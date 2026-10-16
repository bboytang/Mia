"""Evidence-grounded proposals and atomic derived indexes; no real LLM calls."""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from server.companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from server.companion.extraction import EvidenceContext, LLMMemoryExtractor, context_for, explicit_change, normalize, validate_output
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
        with self.assertRaises(MemoryError):
            self.validate(source, proposal(source, category='habit'))

    def test_quote_hypothesis_joke_report_question_and_deletion_are_not_facts(self):
        for source, quote in [
            ('小说台词：“我住在月球”。', '我住在月球'),
            ('假设我喜欢蓝色', '假设我喜欢蓝色'), ('我开玩笑说我喜欢蓝色', '我开玩笑说我喜欢蓝色'),
            ('你刚才说我喜欢蓝色', '你刚才说我喜欢蓝色'), ('我喜欢蓝色？', '我喜欢蓝色'),
            ('忘掉我喜欢蓝色', '忘掉我喜欢蓝色'), ('小张说我喜欢蓝色', '小张说我喜欢蓝色')]:
            with self.subTest(source=source):
                self.assertEqual(self.validate(source, proposal(quote))['memories'], [])

    def test_tool_requests_do_not_become_durable_facts(self):
        for source in [
            '请同时查红盒和蓝盒，分别告诉我各有几颗棋子。',
            '请先读取route，再按其中的next_record继续查。',
            '查一下temperature里的温度，用我平时习惯的单位告诉我。',
            '旧话题先放一边，现在请查红盒的棋子数量。',
            '麻烦帮我计算这张订单的总价。',
            '帮我打开客厅的灯。',
            '不要把它记成我的真实经历。', '请不要保存这段台词。',
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.validate(source, proposal(source))['memories'], [])
        source = '请查询订单。我每周五会核对账单。'
        result = self.validate(source, proposal('我每周五会核对账单。'))
        self.assertEqual(result['memories'][0]['content'], '我每周五会核对账单。')
        for source in ['我每周都会查询天气预报。', '请记住我每天练习计算。']:
            quote = source.removeprefix('请记住')
            self.assertEqual(self.validate(source, proposal(quote))['memories'][0]['content'], quote)

    def test_extractor_skips_ineligible_requests_before_provider_but_keeps_real_sources(self):
        factory = Mock()
        extractor = LLMMemoryExtractor(factory)
        old = [{'id': 'owned', 'content': '我看温度时更习惯用摄氏度。'}]
        for source in ['查一下temperature里的温度，用我平时习惯的单位告诉我。',
                       '请同时查红盒和蓝盒，分别告诉我各有几颗棋子。',
                       '“我喜欢蓝色”只是引用。', '“我喜欢蓝色”', '谢谢你', '我今天很累',
                       '这只是小说台词：“我住在月球”；不要把它记成我的真实经历']:
            with self.subTest(source=source):
                self.assertEqual(extractor([source], old), {'memories': [], 'trait': None})
        factory.assert_not_called()
        for source in ['我每周都会查询天气预报。', '请记住我每天练习计算。',
                       '请查询订单。我每周五会核对账单。']:
            extractor([source], old)
        self.assertEqual(factory.call_count, 3)
        enabled = EvidenceContext()
        enabled.tracking = {'enabled': 1}
        extractor(['我今天很累'], enabled)
        self.assertEqual(factory.call_count, 4, 'Authorized transient observation must still reach the extractor')

    def test_full_owned_quotation_reconciliation_uses_user_data_without_model_guessing(self):
        target = {'id': 'owned', 'content': '我喜欢蓝色', 'category': 'preference',
                  'content_version': 2, 'evidence_version': 3, 'keywords': '["蓝色","喜欢"]'}
        factory = Mock()
        extractor = LLMMemoryExtractor(factory)
        for prefix, mode, new in [('更正：', 'correction', '我喜欢绿色'),
                                  ('以前：', 'time_change', '现在：我喜欢绿色'),
                                  ('不确定：', 'conflict', '我喜欢绿色')]:
            source = prefix + target['content'] + '；' + new
            result = validate_output(extractor([source], [target]), [source], [target])['memories'][0]
            self.assertEqual(result['reconciliation']['kind'], mode)
            self.assertEqual(result['reconciliation']['target_version'], 2)
            self.assertEqual(result['category'], 'preference')
            self.assertEqual(result['source_index'], 0)
            self.assertEqual(result['kind'], 'explicit')
            self.assertEqual(result['keywords'], ['喜欢'])
        factory.assert_not_called()
        source = '更正：我喜欢蓝色；我喜欢绿色'
        self.assertIsNone(explicit_change(source, []))
        self.assertIsNone(explicit_change(source, [target, dict(target, id='ambiguous')]))
        for unsupported in ['引用“' + source + '”', '更正：我喜欢蓝；我喜欢绿色',
                            source + '；我喜欢紫色', '更正：我喜欢蓝色；我被确诊为糖尿病',
                            '以前：我喜欢蓝色；我喜欢绿色']:
            with self.subTest(source=unsupported):
                self.assertIsNone(explicit_change(unsupported, [target]))

    def test_retrieved_old_fact_is_not_a_source_for_a_new_lookup(self):
        old = '我看温度时更习惯用摄氏度。'
        context = [{'id': 'owned', 'content': old, 'content_version': 1, 'evidence_version': 1}]
        source = '查一下temperature里的温度，用我平时习惯的单位告诉我。'
        for index in [0, 1, 2]:
            with self.subTest(index=index), self.assertRaises(MemoryError):
                self.validate(source, proposal(old, source_index=index), context)

    def test_natural_correction_requires_owned_unique_literal_target_and_keeps_raw_result(self):
        target = {'id': 'owned', 'content': '我平常用木梳梳头', 'category': 'fact',
                  'content_version': 2, 'evidence_version': 3}
        for source in ('我梳头用角梳，之前说木梳是口误', '我梳头用角梳，不是木梳'):
            proof = {'form': 'natural', 'kind': 'correction', 'target_id': 'owned',
                     'old_quote': target['content'], 'evidence': source,
                     'old_value': '木梳', 'new_value': '角梳', 'anchor': '梳头'}
            item = proposal(source, reconciliation=proof)
            before = json.dumps(item, ensure_ascii=False, sort_keys=True)
            record = self.validate(source, item, [target])['memories'][0]
            self.assertEqual(record['replaces_id'], 'owned')
            self.assertEqual(record['content'], normalize(source))
            self.assertEqual(record['reconciliation']['target_evidence_version'], 3)
            self.assertEqual(json.dumps(item, ensure_ascii=False, sort_keys=True), before)
            with self.assertRaises(MemoryError):
                self.validate(source, proposal(source), [target])
            for changes in ({'target_id': 'foreign'}, {'old_value': '塑料梳'},
                            {'new_value': '铁梳'}, {'anchor': '洗头'},
                            {'evidence': 'fabricated'}, {'kind': 'time_change'},
                            {'new_value': '木梳'}):
                with self.subTest(changes=changes), self.assertRaises(MemoryError):
                    self.validate(source, proposal(source, reconciliation=dict(proof, **changes)), [target])
            ambiguous = dict(target, id='another', content='旅行时我用木梳梳头')
            with self.assertRaises(MemoryError):
                self.validate(source, item, [target, ambiguous])
        for source in ('我梳头用角梳，木梳放在桌上', '我不确定梳头用角梳还是木梳',
                       '我可能梳头用角梳，不是木梳', '我以前梳头用木梳，现在用角梳，不是木梳'):
            proof = dict(proof, evidence=source)
            with self.assertRaises(MemoryError):
                self.validate(source, proposal(source, reconciliation=proof), [target])

    def test_first_person_correction_intro_is_not_other_speaker_evidence(self):
        provider = Mock()
        extractor = LLMMemoryExtractor(lambda: provider)
        source = '之前说的梳子记错了，我用角梳，不是木梳'
        extractor([source], [])
        self.assertEqual(provider.response_no_stream.call_count, 1)
        self.assertEqual(json.loads(provider.response_no_stream.call_args.args[1])['user_excerpts'], [source])
        for foreign in ('之前小张说我用木梳是口误', '小张说我用角梳，不是木梳'):
            result = extractor([foreign], [])
            self.assertEqual(result, {'memories': [], 'trait': None})
        self.assertEqual(provider.response_no_stream.call_count, 1)

    def test_natural_extractor_uses_one_provider_call_and_keeps_source_and_result(self):
        target = {'id': 'owned', 'content': '我平常用木梳梳头', 'category': 'fact',
                  'content_version': 2, 'evidence_version': 3}
        quote = '我梳头用角梳，不是木梳'
        raw = {'memories': [proposal(quote, reconciliation={
            'form': 'natural', 'kind': 'correction', 'target_id': 'owned',
            'old_quote': target['content'], 'evidence': quote,
            'old_value': '木梳', 'new_value': '角梳', 'anchor': '梳头'})], 'trait': None}
        provider = Mock()
        provider.response_no_stream.return_value = raw
        sources = ['请记住' + quote]
        result = LLMMemoryExtractor(lambda: provider)(sources, [target])
        self.assertIs(result, raw)
        self.assertEqual(provider.response_no_stream.call_count, 1)
        payload = json.loads(provider.response_no_stream.call_args.args[1])
        self.assertEqual(payload['user_excerpts'], [quote])
        self.assertEqual(payload['existing_memories'], [{key: target[key] for key in ('id', 'category', 'content')}])
        self.assertEqual(target['content_version'], 2)
        self.assertEqual(target['evidence_version'], 3)
        self.assertEqual(sources, ['请记住' + quote])
        self.assertEqual(validate_output(result, sources, [target])['memories'][0]['replaces_id'], 'owned')

    def test_mixed_quote_and_real_statement_only_keep_actual_statement(self):
        source = '“我喜欢蓝色”只是引用。我喜欢绿色。'
        result = self.validate(source, proposal('我喜欢绿色'))
        self.assertEqual([item['content'] for item in result['memories']], ['我喜欢绿色'])

    def test_growth_review_uses_actual_prior_evidence_without_changing_model_result(self):
        context = EvidenceContext([{'id': str(i), 'category': 'fact', 'content': f'我在第{i}次观云时画草图',
            'content_version': 1, 'evidence_version': 1,
            'evidence': [{'session_id': f's{i}', 'fingerprint': f'fp{i}'}]} for i in range(3)])
        before = json.dumps(context)
        raw = {'memories': [proposal('我喜欢观云')], 'trait': None}
        provider = Mock()
        provider.response_no_stream.return_value = raw
        extractor = LLMMemoryExtractor(lambda: provider)
        self.assertIs(extractor(['我喜欢观云'], context), raw)
        self.assertIn('可以审阅，不代表语义支持已成立', provider.response_no_stream.call_args.args[0])
        self.assertEqual(json.loads(provider.response_no_stream.call_args.args[1])['existing_memories'],
            [{key: fact[key] for key in ('id', 'category', 'content', 'evidence')} for fact in context])
        self.assertEqual(json.dumps(context), before)
        self.assertEqual(provider.response_no_stream.call_count, 1)
        for fact in context:
            fact['evidence'][0]['fingerprint'] = 'one-source'
        self.assertIs(extractor(['我喜欢观云'], context), raw)
        self.assertNotIn('可以审阅，不代表语义支持已成立', provider.response_no_stream.call_args.args[0])

    def test_focused_importance_keeps_source_and_original_positive_or_negative_value(self):
        for source, weight, evidence in [('修复老书柜对我格外重要', 0.73, '格外重要'),
                                        ('我认为收藏玩偶并不重要', None, None)]:
            with self.subTest(source=source):
                raw = {'memories': [proposal(source, category='fact', importance_weight=weight,
                    importance_evidence=evidence)], 'trait': None}
                before = json.dumps(raw)
                provider = Mock()
                provider.response_no_stream.return_value = raw
                result = LLMMemoryExtractor(lambda: provider)([source], [])
                self.assertIs(result, raw)
                self.assertEqual(provider.response_no_stream.call_count, 1)
                self.assertIn('首要任务是区分用户本人明确肯定', provider.response_no_stream.call_args.args[0])
                self.assertEqual(json.loads(provider.response_no_stream.call_args.args[1])['user_excerpts'], [source])
                self.assertEqual(validate_output(result, [source], [])['memories'][0]['emotional_weight'], weight)
                self.assertEqual(json.dumps(raw), before)

    def test_cannot_drop_negation_or_change_subject_with_a_substring(self):
        for quote in ['喜欢蓝色', '我朋友喜欢蓝色']:
            source = '我不喜欢蓝色，但我朋友喜欢蓝色'
            self.assertEqual(self.validate(source, proposal(quote))['memories'], [])
        with self.assertRaises(MemoryError):
            self.validate('我不喜欢蓝色', proposal('我喜欢蓝色', source_quote='我不喜欢蓝色'))

    def test_extractor_request_omits_only_command_prefix_and_preserves_original_provenance(self):
        provider = Mock()
        received = []

        def response(instruction, payload):
            text = json.loads(payload)['user_excerpts'][0]
            received.append(text)
            return {'memories': [proposal(text)], 'trait': None}

        provider.response_no_stream.side_effect = response
        sources = ['米娅，请记住我不喜欢蓝色']
        raw = LLMMemoryExtractor(lambda: provider)(sources, [])
        result = validate_output(raw, sources, [])
        self.assertEqual(received, ['我不喜欢蓝色'])
        self.assertEqual(sources, ['米娅，请记住我不喜欢蓝色'])
        self.assertEqual(result['memories'][0]['content'], '我不喜欢蓝色')
        self.assertEqual(result['memories'][0]['source_quote'], '我不喜欢蓝色')
        literal = '我喜欢蓝色，尤其是浅蓝色。'
        LLMMemoryExtractor(lambda: provider)([literal], [])
        self.assertEqual(received[-1], literal, 'An ordinary source must not be rewritten for the model')

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

    def test_importance_producer_fields_preserve_canonical_storage_and_legacy_results(self):
        source = '维护旧书对我很有意义'
        for prefix in ('importance', 'emotional'):
            with self.subTest(prefix=prefix):
                item = proposal(source, **{prefix + '_weight': 0.65, prefix + '_evidence': '很有意义'})
                original = dict(item)
                record = self.validate(source, item)['memories'][0]
                self.assertEqual(record['emotional_weight'], 0.65)
                self.assertEqual(record['emotional_evidence'], '很有意义')
                self.assertNotIn('importance_weight', record)
                self.assertEqual(item, original)
        source = '我觉得整理积木并不重要'
        record = self.validate(source, proposal(source, importance_weight=None,
            importance_evidence=None))['memories'][0]
        self.assertIsNone(record['emotional_weight'])
        self.assertIsNone(record['emotional_evidence'])

    def test_importance_producer_cannot_bypass_source_bounds_or_choose_between_two_scores(self):
        source = '维护旧书对我很有意义'
        for extra in [
            {'importance_weight': value, 'importance_evidence': '很有意义'}
            for value in (True, -0.1, 1.1, '0.5', float('nan'))
        ] + [
            {'importance_weight': 0.7, 'importance_evidence': '格外重要'},
            {'importance_weight': 0.7},
            {'importance_weight': 0.7, 'importance_evidence': '很有意义', 'emotional_weight': None},
            {'importance_weight': 0.7, 'importance_evidence': '很有意义', 'emotional_evidence': '很有意义'},
        ]:
            with self.subTest(extra=extra), self.assertRaises(MemoryError):
                self.validate(source, proposal(source, **extra))
        with self.assertRaises(MemoryError):
            self.validate('我喜欢陶杯', proposal('我喜欢陶杯', importance_weight=0.7,
                importance_evidence='陶杯'))

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

    async def test_natural_correction_commits_same_fact_and_replaces_old_source_and_vector(self):
        await self.admit()
        await self.worker.run_once()
        target = self.store.list_memories(self.scope.owner)[0]['id']
        self.source = '我喜欢绿色，不是蓝色，之前说错了'
        self.output = {'memories': [proposal(self.source, reconciliation={
            'form': 'natural', 'kind': 'correction', 'target_id': target,
            'old_quote': '我喜欢蓝色', 'evidence': self.source,
            'old_value': '蓝色', 'new_value': '绿色', 'anchor': '喜欢'})]}
        accepted = await self.admit('natural-correction')
        await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
        records = self.store.list_memories(self.scope.owner)
        self.assertEqual([(r['id'], r['content']) for r in records], [(target, normalize(self.source))])
        self.assertEqual(records[0]['source'], normalize(self.source))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM sources WHERE excerpt=?',
                                             ('我喜欢蓝色',)).fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 1)
        self.assertEqual(self.store.snapshot(self.scope.owner)['revision'], 1)
        self.assertEqual(self.calls, 2)

    async def test_model_importance_reaches_existing_metadata_and_retrieval_signal(self):
        self.source = '维护旧书对我很有意义'
        self.output = {'memories': [proposal(self.source, importance_weight=0.65,
            importance_evidence='很有意义')]}
        accepted = await self.admit()
        await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
        meta = self.store.db.execute('SELECT emotional_weight FROM mia_memory_meta').fetchone()
        self.assertEqual(meta['emotional_weight'], 0.65)
        found = await SemanticMemoryIndex(self.store, self.encoder).retrieve(
            self.scope, self.policy, '维护旧书')
        self.assertEqual(found['candidates'][0]['signals']['emotion'], 0.65)
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
