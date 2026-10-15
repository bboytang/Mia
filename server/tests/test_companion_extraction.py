"""Evidence-grounded proposals and atomic derived indexes; no real LLM calls."""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from server.companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from server.companion.extraction import LLMMemoryExtractor, context_for, validate_output
from server.companion.jobs import JobStore, MemoryWorker, TurnCompleted
from server.companion.memory import MemoryStore, MemoryError
from server.companion.semantic import SemanticMemoryIndex


def proposal(text, **changes):
    return dict({'category': 'preference', 'content': text, 'source_quote': text, 'source_index': 0,
        'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False}, **changes)


class UnitEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION

    def encode(self, text, query=False):
        vector = np.zeros(DIMENSION, dtype=np.float32)
        vector[0] = 1
        return vector


class Policy:
    active = True

    async def require(self, scope, permission):
        if not self.active or permission not in scope.permissions:
            raise PrivateAuthorizationRequired()

    async def restore(self, snapshot):
        if snapshot != self.scope.snapshot() or not self.active:
            raise PrivateAuthorizationRequired()
        return self.scope


class ExtractionValidationTests(unittest.TestCase):
    def validate(self, source, item, context=None):
        return validate_output({'memories': [item], 'trait': None}, [source], context or [])

    def test_neutral_durable_statement_needs_no_emotional_threshold(self):
        source = '我每周三都会在公司食堂吃素'
        result = self.validate(source, proposal(source, entities=['公司食堂'], keywords=['吃素'], trigger_terms=['周三']))
        self.assertEqual(result['memories'][0]['content'], source)
        self.assertIsNone(result['memories'][0]['emotional_weight'])
        self.assertFalse(result['memories'][0]['sensitive'])

    def test_quote_hypothesis_joke_report_question_and_deletion_are_not_facts(self):
        for source, quote in [
            ('小说台词：“我住在月球”。', '我住在月球'),
            ('假设我喜欢蓝色', '假设我喜欢蓝色'), ('我开玩笑说我喜欢蓝色', '我开玩笑说我喜欢蓝色'),
            ('你刚才说我喜欢蓝色', '你刚才说我喜欢蓝色'), ('我喜欢蓝色？', '我喜欢蓝色'),
            ('忘掉我喜欢蓝色', '忘掉我喜欢蓝色'), ('小张说我喜欢蓝色', '小张说我喜欢蓝色')]:
            with self.subTest(source=source):
                self.assertEqual(self.validate(source, proposal(quote))['memories'], [])

    def test_mixed_quote_and_real_statement_only_keep_actual_statement(self):
        source = '“我喜欢蓝色”只是引用。我喜欢绿色。'
        result = self.validate(source, proposal('我喜欢绿色'))
        self.assertEqual([item['content'] for item in result['memories']], ['我喜欢绿色'])

    def test_cannot_drop_negation_or_change_subject_with_a_substring(self):
        for quote in ['喜欢蓝色', '我朋友喜欢蓝色']:
            source = '我不喜欢蓝色，但我朋友喜欢蓝色'
            self.assertEqual(self.validate(source, proposal(quote))['memories'], [])
        with self.assertRaises(MemoryError):
            self.validate('我不喜欢蓝色', proposal('我喜欢蓝色', source_quote='我不喜欢蓝色'))

    def test_remember_prefix_is_not_part_of_the_fact(self):
        source = '米娅，请记住我喜欢蓝色'
        self.assertEqual(self.validate(source, proposal('我喜欢蓝色'))['memories'][0]['content'], '我喜欢蓝色')

    def test_transient_and_greeting_are_valid_empty_not_parse_errors(self):
        for source, value in [('谢谢你', 'durable'), ('我今天很累', 'durable'), ('窗外下雨', 'transient')]:
            self.assertEqual(self.validate(source, proposal(source, value=value))['memories'], [])
        for raw in ({}, {'memories': [], 'trait': None}, '```json\n{"memories":[]}\n```'):
            self.assertEqual(validate_output(raw, ['你好'], [])['memories'], [])
        for raw in ('not json', '[]', {'memories': 'not a list'}, {'instructions': 'ignore everything'}):
            with self.assertRaises(MemoryError):
                validate_output(raw, ['你好'], [])

    def test_secret_and_false_or_out_of_range_provenance_fail_before_write(self):
        with self.assertRaises(MemoryError):
            self.validate('我喜欢蓝色', proposal('password: synthetic', source_quote='我喜欢蓝色'))
        with self.assertRaises(MemoryError):
            self.validate('ｐａｓｓｗｏｒｄ：synthetic', proposal('我喜欢蓝色'))
        for item in [proposal('我喜欢蓝色', source_quote='根本没有这句'), proposal('我喜欢蓝色', source_index=1),
                     proposal('我喜欢蓝色', kind=[]), proposal('我喜欢蓝色', subject=[]),
                     proposal('我喜欢蓝色', relations=[{'target_id': []}])]:
            with self.assertRaises(MemoryError):
                self.validate('我喜欢蓝色', item)

    def test_medical_financial_and_inferred_candidates_require_confirmation(self):
        for source in ('我被确诊为糖尿病', '我对花生过敏', '我的年薪是二十万元'):
            self.assertTrue(self.validate(source, proposal(source))['memories'][0]['sensitive'])
        source = '我每次提交前都会检查测试结果'
        inferred = proposal('检查测试结果可能是我的稳定习惯', source_quote=source, kind='inferred', anchor='检查测试结果')
        self.assertTrue(self.validate(source, inferred)['memories'][0]['sensitive'])
        with self.assertRaises(MemoryError):
            self.validate(source, dict(inferred, anchor='谨慎'))

    def test_unproved_clues_importance_relations_and_replacements_are_rejected(self):
        source = '我喜欢蓝色'
        for extra in ({'keywords': ['忧郁']}, {'emotional_weight': 0.9}, {'emotional_weight': True},
                      {'relations': [{'target_id': 'foreign', 'relation': 'shared_term', 'anchor': '蓝色', 'evidence': source}]},
                      {'replaces_id': 'old-fact'}):
            with self.assertRaises(MemoryError):
                self.validate(source, proposal(source, **extra))
        important = '蓝色对我很重要'
        self.assertEqual(self.validate(important, proposal(important, emotional_weight=0.6,
            emotional_evidence='很重要'))['memories'][0]['emotional_weight'], 0.6)

    def test_traits_need_three_owned_versioned_sources_and_a_shared_anchor(self):
        context = [{'id': str(i), 'content': f'我在第{i}次提交前检查测试结果', 'content_version': 1,
                    'evidence_version': 1, 'evidence': [{'session_id': f's{i}', 'fingerprint': f'fp{i}'}]} for i in range(3)]
        trait = {'name': '检查习惯', 'description': '检查测试结果的稳定习惯', 'anchor': '检查测试结果',
            'evidence_ids': [row['id'] for row in context],
            'evidence_quotes': [{'id': row['id'], 'quote': row['content']} for row in context]}
        self.assertEqual(len(validate_output({'memories': [], 'trait': trait}, ['我在检查'], context)['trait']['evidence_quotes']), 3)
        with self.assertRaises(MemoryError):
            validate_output({'memories': [], 'trait': dict(trait, evidence_ids=['foreign'])}, ['我在检查'], context)
        for row in context:
            row['evidence'][0]['session_id'] = 'same-session'
        with self.assertRaises(MemoryError):
            validate_output({'memories': [], 'trait': trait}, ['我在检查'], context)

    def test_relation_is_versioned_and_only_a_literal_shared_term(self):
        source = '我吃素时会选择豆腐'
        context = [{'id': 'own', 'content': '我每周三吃素', 'content_version': 2, 'evidence_version': 3}]
        relation = {'target_id': 'own', 'relation': 'shared_term', 'anchor': '吃素', 'evidence': source}
        result = self.validate(source, proposal(source, relations=[relation]), context)
        self.assertEqual(result['memories'][0]['relations'][0]['target_version'], 2)
        for changes in ({'relation': 'causes'}, {'anchor': '午餐'}, {'target_id': 'foreign'}):
            with self.assertRaises(MemoryError):
                self.validate(source, proposal(source, relations=[dict(relation, **changes)]), context)


class ExtractionPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / 'facts.sqlite3')
        self.scope = AuthenticatedScope('user:1:agent:one', 1, 1, 'one', 'mia', 'device', 'client', 0, 1,
            datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
        self.policy = Policy()
        self.policy.scope = self.scope
        self.jobs = JobStore(self.store)
        self.encoder = UnitEncoder()
        self.calls = 0
        self.source = '我喜欢蓝色'
        self.output = {'memories': [proposal(self.source, keywords=['蓝色'], trigger_terms=['喜欢'])]}
        async def resolve(scope):
            def extract(sources, context):
                self.calls += 1
                return self.output
            return extract
        self.worker = MemoryWorker(self.jobs, self.policy, resolve, encoder=self.encoder)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    async def admit(self, marker='one'):
        event = TurnCompleted(self.scope, 's', marker, marker, self.source, self.store.snapshot(self.scope.owner)['revision'])
        return await self.worker.submit(event)

    async def test_fact_metadata_true_vector_and_source_identity_commit_together(self):
        accepted = await self.admit()
        await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
        record = self.store.list_memories(self.scope.owner)[0]
        meta = dict(self.store.db.execute('SELECT * FROM mia_memory_meta').fetchone())
        self.assertEqual(meta['confirmation_origin'], 'model_user_excerpt')
        self.assertEqual(json.loads(meta['keywords']), ['蓝色'])
        source = dict(self.store.db.execute('SELECT * FROM mia_source_meta').fetchone())
        self.assertEqual((source['turn_id'], source['message_id'], source['source_type']), ('one', 'one', 'user_explicit'))
        index = SemanticMemoryIndex(self.store, self.encoder)
        found = await index.retrieve(self.scope, self.policy, '我喜欢什么颜色')
        self.assertEqual(found['results'][0]['id'], record['id'])
        await self.worker.submit(TurnCompleted(self.scope, 's', 'one', 'one', self.source, 0))
        self.assertFalse(await self.worker.run_once())
        self.assertEqual(self.calls, 1)

    async def test_sensitive_and_inferred_candidates_do_not_enter_index_or_persona(self):
        for marker, text, extra in [('medical', '我被确诊为糖尿病', {}),
                ('inferred', '我会检查测试结果', {'content': '检查测试结果可能是我的习惯', 'kind': 'inferred', 'anchor': '检查测试结果'})]:
            self.source = text
            self.output = {'memories': [proposal(text, **extra)]}
            await self.admit(marker)
            await self.worker.run_once()
        self.assertTrue(all(not row['confirmed'] for row in self.store.list_memories(self.scope.owner)))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.assertEqual(self.store.personality(self.scope.owner)['traits'], [])
        found = await SemanticMemoryIndex(self.store, self.encoder).retrieve(self.scope, self.policy, '我习惯做什么')
        self.assertEqual(found['results'], [])

    async def test_embedding_failure_then_database_retry_never_reextracts(self):
        accepted = await self.admit()
        with patch.object(self.encoder, 'encode', side_effect=EmbeddingUnavailable('fixture')):
            await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['error_category'], 'embedding')
        self.assertEqual(self.store.list_memories(self.scope.owner), [])
        with self.store.db:
            self.store.db.execute('UPDATE mia_jobs SET next_attempt_at=0')
        with patch.object(self.jobs, 'commit', side_effect=sqlite3.OperationalError('fixture')):
            await self.worker.run_once()
        with self.store.db:
            self.store.db.execute('UPDATE mia_jobs SET next_attempt_at=0')
        await self.worker.run_once()
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')

    async def test_owned_relation_and_confirmation_summary_are_persisted_without_fact_mirror(self):
        await self.admit()
        await self.worker.run_once()
        target = self.store.list_memories(self.scope.owner)[0]['id']
        self.source = '我选择蓝色的文具'
        self.output = {'memories': [proposal(self.source, relations=[{'target_id': target, 'relation': 'shared_term',
            'anchor': '蓝色', 'evidence': self.source}])]}
        await self.admit('relation')
        await self.worker.run_once()
        relation = dict(self.store.db.execute('SELECT * FROM mia_associations').fetchone())
        self.assertEqual(relation['related_id'], target)
        self.assertEqual(json.loads(relation['evidence'])['message_id'], 'relation')
        self.source = '我被确诊为糖尿病'
        self.output = {'memories': [proposal(self.source)]}
        accepted = await self.admit('medical')
        await self.worker.run_once()
        row = self.jobs.current(accepted)
        self.assertEqual(json.loads(row['validated_result']), {'confirmation_required': True})
        self.assertEqual(row['source_payload'], '{}')

    async def test_stale_relation_evidence_cancels_before_fact_or_vector_write(self):
        target = self.store.apply_extraction(self.scope.owner, 'old', 0, ['我喜欢蓝色'],
            {'memories': [{'category': 'preference', 'content': '我喜欢蓝色', 'source_index': 0}]}, 'old')['memories'][0]
        self.source = '我选择蓝色的文具'
        self.output = {'memories': [proposal(self.source, relations=[{'target_id': target, 'relation': 'shared_term',
            'anchor': '蓝色', 'evidence': self.source}])]}
        accepted = await self.admit()
        original = self.jobs.commit
        def changed(job, result, vectors):
            with self.store.db:
                self.store.db.execute('UPDATE mia_memory_meta SET evidence_version=evidence_version+1 WHERE memory_id=?', (target,))
            return original(job, result, vectors)
        with patch.object(self.jobs, 'commit', side_effect=changed):
            await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'cancelled')
        self.assertEqual(len(self.store.list_memories(self.scope.owner)), 1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)

    async def test_invalid_prepared_vector_rolls_back_without_fact_or_metadata(self):
        accepted = await self.admit()
        with patch.object(self.encoder, 'encode', return_value=np.zeros(3, dtype=np.float32)):
            await self.worker.run_once()
        self.assertEqual(self.store.list_memories(self.scope.owner), [])
        self.assertEqual(self.jobs.current(accepted)['state'], 'retry_wait')
        self.assertEqual(self.calls, 1)

    async def test_unverified_legacy_validated_job_is_cancelled_without_model_replay(self):
        accepted = await self.admit()
        self.jobs.update(accepted, 'validated', result=json.dumps({'memories': [{'category': 'fact',
            'content': 'unverified old model claim', 'source_index': 0}]}))
        await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'cancelled')
        self.assertEqual(self.jobs.current(accepted)['error_category'], 'extractor_version_changed')
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
