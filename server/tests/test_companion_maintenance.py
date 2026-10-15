"""P18 reconciliation and maintenance races, with synthetic vectors and policy."""

import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from server.tests import test_companion_extraction as fixture
from server.companion.context import ContextBuilder, ContextError, ContextLimits
from server.companion.extraction import context_for, validate_output
from server.companion.jobs import MemoryWorker
from server.companion.memory import MemoryError
from server.companion.semantic import SemanticMemoryIndex


class MaintenanceTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixture.ExtractionPipelineTests.setUp
    tearDown = fixture.ExtractionPipelineTests.tearDown
    admit = fixture.ExtractionPipelineTests.admit

    async def seed(self):
        await self.admit('old')
        await self.worker.run_once()
        return self.store.list_memories(self.scope.owner)[0]['id']

    def reconcile(self, target, mode='correction'):
        old = self.store.db.execute('SELECT content FROM memories WHERE id=?', (target,)).fetchone()[0]
        new = '现在：我喜欢绿色' if mode == 'time_change' else '我喜欢绿色'
        prefix = {'correction': '更正：', 'time_change': '以前：', 'conflict': '不确定：'}[mode]
        self.source = prefix + old + '；' + new
        self.output = {'memories': [fixture.proposal(new, reconciliation={
            'target_id': target, 'kind': mode, 'old_quote': old, 'evidence': self.source})]}

    async def bundle(self, store=None):
        builder = ContextBuilder(SemanticMemoryIndex(store or self.store, self.encoder))
        return builder, await builder.build(self.scope, self.policy, 'cached-turn', '我喜欢什么颜色',
            limits=ContextLimits('unit', 16384, 768, 'unit fixture'))

    async def test_correction_replaces_one_fact_and_invalidates_other_connection(self):
        target = await self.seed()
        other = type(self.store)(Path(self.temp.name) / 'facts.sqlite3')
        try:
            builder, cached = await self.bundle(other)
            stale = await self.admit('queued-old')
            self.reconcile(target)
            accepted = await self.admit('correct')
            # Explicit priority selects correction before the older queued task.
            with self.store.db:
                self.store.db.execute('UPDATE mia_jobs SET created_at=created_at-10 WHERE id=?', (accepted['id'],))
            await self.worker.run_once()
            self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
            self.assertEqual(self.jobs.current(stale)['state'], 'cancelled')
            self.assertEqual(self.store.list_memories(self.scope.owner)[0]['id'], target)
            self.assertEqual(self.store.list_memories(self.scope.owner)[0]['content'], '我喜欢绿色')
            self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 1)
            with self.assertRaises(ContextError):
                await builder.validate(cached, self.policy)
            _, fresh = await self.bundle(other)
            self.assertNotIn('我喜欢蓝色', fresh.request_json)
        finally:
            other.close()

    async def test_time_change_keeps_old_source_but_only_new_fact_is_current(self):
        target = await self.seed()
        self.reconcile(target, 'time_change')
        await self.admit('time')
        await self.worker.run_once()
        self.assertEqual(len(self.store.list_memories(self.scope.owner)), 2)
        old = self.store.db.execute('SELECT m.confirmed,x.state FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id WHERE m.id=?', (target,)).fetchone()
        self.assertEqual(tuple(old), (0, 'superseded'))
        self.assertEqual(self.store.db.execute('SELECT excerpt FROM sources WHERE memory_id=?', (target,)).fetchone()[0], '我喜欢蓝色')
        _, bundle = await self.bundle()
        self.assertNotIn('我喜欢蓝色', bundle.request_json)
        self.assertIn('现在：我喜欢绿色', bundle.request_json)

    async def test_uncertain_conflict_preserves_both_for_confirmation_without_vectors(self):
        target = await self.seed()
        self.reconcile(target, 'conflict')
        accepted = await self.admit('conflict')
        await self.worker.run_once()
        self.assertEqual(len(self.store.list_memories(self.scope.owner)), 2)
        self.assertTrue(all(not row['confirmed'] for row in self.store.list_memories(self.scope.owner)))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.assertEqual(json.loads(self.jobs.current(accepted)['validated_result']), {'confirmation_required': True})
        _, bundle = await self.bundle()
        self.assertNotIn('我喜欢蓝色', bundle.request_json)
        self.assertNotIn('我喜欢绿色', bundle.request_json)

    async def test_similarity_and_missing_classification_cannot_replace(self):
        target = await self.seed()
        self.source = '我喜欢绿色'
        self.output = {'memories': [fixture.proposal(self.source, replaces_id=target)]}
        with self.assertRaises(MemoryError):
            validate_output(self.output, [self.source], context_for(self.store, self.scope.owner))
        self.reconcile(target)
        del self.output['memories'][0]['reconciliation']
        with self.assertRaises(MemoryError):
            validate_output(self.output, [self.source], context_for(self.store, self.scope.owner))

    async def test_forged_foreign_quoted_or_wrong_old_evidence_is_rejected(self):
        target = await self.seed()
        context = context_for(self.store, self.scope.owner)
        for mutate in ('foreign', 'old_quote', 'evidence', 'quoted', 'kind'):
            self.reconcile(target)
            proof = self.output['memories'][0]['reconciliation']
            if mutate == 'foreign':
                proof['target_id'] = 'foreign-id'
            elif mutate in {'old_quote', 'evidence', 'kind'}:
                proof[mutate] = 'fabricated'
            else:
                self.source = '小说引用：“' + self.source + '”'
                self.assertEqual(validate_output(self.output, [self.source], context)['memories'], [])
                continue
            with self.subTest(mutate=mutate), self.assertRaises(MemoryError):
                validate_output(self.output, [self.source], context)

    async def test_target_version_changed_after_validation_cancels_before_write(self):
        target = await self.seed()
        self.reconcile(target)
        accepted = await self.admit('race')
        original = self.jobs.commit
        def changed(job, result, vectors):
            with self.store.db:
                self.store.db.execute('UPDATE mia_memory_meta SET evidence_version=evidence_version+1 WHERE memory_id=?', (target,))
            return original(job, result, vectors)
        with patch.object(self.jobs, 'commit', side_effect=changed):
            await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'cancelled')
        self.assertEqual(self.store.list_memories(self.scope.owner)[0]['content'], '我喜欢蓝色')

    async def test_database_retry_and_worker_restart_do_not_repeat_correction_model(self):
        target = await self.seed()
        self.reconcile(target)
        accepted = await self.admit('retry')
        with patch.object(self.store, '_index', side_effect=sqlite3.OperationalError('rollback')):
            await self.worker.run_once()
        self.assertEqual(self.store.list_memories(self.scope.owner)[0]['content'], '我喜欢蓝色')
        self.assertEqual(self.store.snapshot(self.scope.owner)['revision'], 0)
        with self.store.db:
            self.store.db.execute('UPDATE mia_jobs SET next_attempt_at=0')
        self.worker = MemoryWorker(self.jobs, self.policy, self.worker.resolve, encoder=self.encoder)
        await self.worker.run_once()
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
        self.assertEqual(self.calls, 2)  # One seed, one correction; DB retry reused validation.
        self.assertEqual(self.store.snapshot(self.scope.owner)['revision'], 1)

    async def test_delete_clear_pause_or_revoke_during_encoding_cannot_commit(self):
        for action in ('delete', 'clear', 'pause', 'revoke'):
            self.policy.active = True
            self.store.set_paused(self.scope.owner, False)
            self.source = '我喜欢蓝色'
            self.output = {'memories': [fixture.proposal(self.source)]}
            await self.admit('seed-' + action)
            await self.worker.run_once()
            target = next(row['id'] for row in self.store.list_memories(self.scope.owner) if row['confirmed'])
            self.reconcile(target)
            accepted = await self.admit('encode-' + action)
            encode = self.encoder.encode
            def mutate(text, query=False):
                if action == 'delete':
                    self.store.delete_memory(self.scope.owner, target)
                elif action == 'clear':
                    self.store.clear(self.scope.owner)
                elif action == 'pause':
                    self.store.set_paused(self.scope.owner, True)
                else:
                    self.policy.active = False
                return encode(text, query)
            with patch.object(self.encoder, 'encode', side_effect=mutate):
                await self.worker.run_once()
            self.assertEqual(self.jobs.current(accepted)['state'], 'cancelled')
            self.assertFalse(any(row['content'] == '我喜欢绿色' for row in self.store.list_memories(self.scope.owner)))
            if action == 'pause':
                self.assertTrue(any(row['content'] == '我喜欢蓝色' for row in self.store.list_memories(self.scope.owner)))

    async def test_correction_invalidates_traits_events_observations_and_associations(self):
        target = await self.seed()
        with self.store.db:
            self.store.db.execute('INSERT INTO traits VALUES (?,?,?,?,?)',
                (self.scope.owner, 'fixture', 'fixture', json.dumps([target]), 0))
            self.store.db.execute("INSERT INTO mia_events(id,owner,event_type,idempotency_key,state,session_id,turn_id,created_at,updated_at) "
                "VALUES ('event',?,'fixture','one','active','s','old',0,0)", (self.scope.owner,))
            self.store.db.execute('INSERT INTO mia_event_evidence VALUES (?,?,1,2)', ('event', target))
            self.store.db.execute("INSERT INTO mia_observations(id,owner,subject,source_kind,session_id,turn_id,message_id,observed_at,created_at,consent_version,tendency,confidence,source_excerpt,state) "
                "VALUES ('observation',?,'user','self_report','s','old','old',0,0,1,'fixture',1,'我喜欢蓝色','active')", (self.scope.owner,))
            self.store.db.execute('INSERT INTO mia_associations VALUES (?,?,?,?,?,?)',
                (target, target, 'shared_term', '{}', 1, 1))
        self.reconcile(target)
        await self.admit('correct-evidence')
        await self.worker.run_once()
        self.assertEqual(self.store.personality(self.scope.owner)['traits'], [])
        self.assertEqual(self.store.db.execute('SELECT state FROM mia_events').fetchone()[0], 'invalidated')
        self.assertEqual(tuple(self.store.db.execute('SELECT state,source_excerpt FROM mia_observations').fetchone()), ('invalidated', ''))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_associations').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM sources WHERE memory_id=?', (target,)).fetchone()[0], 1)

    async def test_same_batch_cannot_overwrite_twice_or_reuse_changed_evidence(self):
        target = await self.seed()
        self.reconcile(target)
        self.output['memories'] *= 2
        with self.assertRaises(MemoryError):
            validate_output(self.output, [self.source], context_for(self.store, self.scope.owner))

    async def test_pause_retains_existing_data_clear_removes_event_and_observation_rows(self):
        target = await self.seed()
        self.store.set_paused(self.scope.owner, True)
        self.assertEqual(len(self.store.list_memories(self.scope.owner)), 1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 1)
        self.store.set_paused(self.scope.owner, False)
        self.store.clear(self.scope.owner)
        self.assertEqual(self.store.list_memories(self.scope.owner), [])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_events').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_observations').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
