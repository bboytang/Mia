"""P19/P20 lifecycle mechanisms. Clock/policy/vectors here are explicitly synthetic."""

import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from server.tests import test_companion_extraction as fixture
from server.companion import emotions
from server.companion.context import ContextBuilder, ContextError, ContextLimits
from server.companion.extraction import context_for, validate_output
from server.companion.jobs import JobStore, MemoryWorker, TurnCompleted
from server.companion.memory import MemoryError, MemoryStore
from server.companion.semantic import SemanticMemoryIndex


class ContinuityTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixture.ExtractionPipelineTests.setUp
    tearDown = fixture.ExtractionPipelineTests.tearDown
    admit = fixture.ExtractionPipelineTests.admit

    async def seed(self):
        await self.admit('seed')
        await self.worker.run_once()
        self.builder = ContextBuilder(SemanticMemoryIndex(self.store, self.encoder))
        return self.store.list_memories(self.scope.owner)[0]['id']

    async def bundle(self, query='你还记得我喜欢蓝色吗', turn='event', session='new-session'):
        return await self.builder.build(self.scope, self.policy, turn, query, session_id=session,
            limits=ContextLimits('unit', 16384, 768, 'unit fixture'))

    async def test_event_is_pending_before_generation_and_activates_only_after_actual_reply(self):
        await self.seed()
        bundle = await self.bundle()
        self.assertEqual(bundle.diagnostics()['events'][0]['state'], 'pending')
        self.assertEqual(self.store.db.execute('SELECT state FROM mia_events').fetchone()[0], 'pending')
        ids = await self.builder.complete(bundle, self.policy, '😌记得，你喜欢蓝色。')
        self.assertEqual(ids, [bundle.diagnostics()['events'][0]['id']])
        self.assertEqual(self.store.db.execute('SELECT state FROM mia_events').fetchone()[0], 'active')

    async def test_keyword_without_support_has_no_event_and_unknown_reply_cannot_activate(self):
        await self.seed()
        self.assertEqual((await self.bundle('你是谁，你会离开吗')).diagnostics()['events'], [])
        pending = await self.bundle()
        self.assertEqual(await self.builder.complete(pending, self.policy, '😌我不知道你喜欢什么颜色。'), [])
        self.assertEqual(self.store.db.execute('SELECT state FROM mia_events').fetchone()[0], 'pending')

    async def test_restart_and_new_session_restore_one_active_event_without_reenactment(self):
        await self.seed()
        first = await self.bundle()
        await self.builder.complete(first, self.policy, '😌记得，你喜欢蓝色。')
        self.store.close()
        self.store = MemoryStore(Path(self.temp.name) / 'facts.sqlite3')
        self.builder = ContextBuilder(SemanticMemoryIndex(self.store, self.encoder))
        second = await self.bundle(turn='again', session='other-device-session')
        self.assertEqual(second.diagnostics()['events'], [{'id': first.diagnostics()['events'][0]['id'], 'state': 'active'}])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_events').fetchone()[0], 1)
        self.assertEqual(await self.builder.complete(second, self.policy, '😌你喜欢蓝色。'), [])

    async def test_failed_turn_stays_pending_and_retry_needs_new_real_completion(self):
        await self.seed()
        first = await self.bundle()
        second = await self.bundle(turn='retry', session='different')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_events').fetchone()[0], 1)
        with self.assertRaises(ContextError):
            await self.builder.complete(first, self.policy, '😌你喜欢蓝色。')
        self.assertTrue(await self.builder.complete(second, self.policy, '😌你喜欢蓝色。'))

    async def test_edit_delete_and_revoke_prevent_completion_or_later_event_use(self):
        target = await self.seed()
        first = await self.bundle()
        self.store.edit_memory(self.scope.owner, target, '我喜欢绿色')
        with self.assertRaises(ContextError):
            await self.builder.complete(first, self.policy, '😌你喜欢蓝色。')
        self.assertEqual((await self.bundle('你还记得我喜欢蓝色吗', turn='new')).diagnostics()['events'], [])
        self.policy.active = False
        with self.assertRaises(fixture.PrivateAuthorizationRequired):
            await self.bundle(turn='revoked')

    async def test_boundary_and_reflection_need_two_sided_evidence_and_preserve_core(self):
        await self.seed()
        boundary = await self.bundle('请不要叫我宝贝', turn='boundary')
        self.assertIn('Pending events', boundary.request_json)
        self.assertTrue(await self.builder.complete(boundary, self.policy, '😌我会尊重你的称呼偏好，不再这样叫你。'))
        reflection = await self.bundle('你怎么看我喜欢蓝色这件事', turn='reflection')
        self.assertTrue(await self.builder.complete(reflection, self.policy, '😌我会尊重你喜欢蓝色的偏好。'))
        types = {row[0] for row in self.store.db.execute("SELECT event_type FROM mia_events WHERE state='active'")}
        self.assertEqual(types, {'boundary', 'reflection'})
        self.assertIn('cannot be rewritten', reflection.request_json)

    async def test_deleting_evidence_erases_event_excerpts_and_foreign_management_is_denied(self):
        target = await self.seed()
        bundle = await self.bundle()
        ids = await self.builder.complete(bundle, self.policy, '😌你喜欢蓝色。')
        with self.assertRaises(MemoryError):
            self.store.handle('foreign', {'action': 'event_delete', 'id': ids[0]})
        self.store.delete_memory(self.scope.owner, target)
        self.assertEqual(tuple(self.store.db.execute('SELECT user_excerpt,assistant_excerpt FROM mia_event_interactions').fetchone()), ('', None))
        self.assertEqual(self.store.db.execute('SELECT state FROM mia_events').fetchone()[0], 'invalidated')

    def enable(self):
        return self.store.handle(self.scope.owner, {'action': 'emotion_consent', 'enabled': True})

    async def observe(self, marker, *, day=0, session=None, text='我今天很难过', kind='self_report', tendency='negative'):
        if not hasattr(self, 'epoch'):
            self.epoch = 1800000000 // emotions.DAY * emotions.DAY
        self.store.clock = lambda: self.epoch + day * emotions.DAY + 3600
        self.source = text
        self.output = {'memories': [], 'observations': [{'source_index': 0, 'source_quote': text,
            'subject': 'user', 'source_kind': kind, 'tendency': tendency, 'confidence': 0.6 if kind == 'inferred' else 0.9}]}
        accepted = await self.worker.submit(TurnCompleted(self.scope, session or 's-' + marker, marker, marker, text,
            self.store.snapshot(self.scope.owner)['revision']))
        await self.worker.run_once()
        return accepted

    async def test_default_off_cannot_persist_observations_and_no_unreviewed_history_is_aggregated(self):
        admitted = await self.observe('off')
        self.assertEqual(self.jobs.current(admitted)['error_category'], 'invalid_output')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_observations').fetchone()[0], 0)
        self.assertEqual(emotions.trend(self.store, self.scope.owner), {'status': 'disabled'})

    async def test_observation_uses_server_time_identity_and_consent_not_model_fields(self):
        self.enable()
        accepted = await self.observe('real-identity')
        self.assertEqual(self.jobs.current(accepted)['state'], 'committed')
        row = self.store.db.execute('SELECT * FROM mia_observations').fetchone()
        self.assertEqual(row['observed_at'], self.epoch + 3600)
        self.assertEqual((row['message_id'], row['source_kind'], row['consent_version']), ('real-identity', 'self_report', 1))
        self.assertEqual(emotions.trend(self.store, self.scope.owner)['status'], 'insufficient_observations')
        self.assertEqual(self.store.list_memories(self.scope.owner), [])

    async def test_five_observations_three_sessions_seven_calendar_days_and_single_reversal(self):
        self.enable()
        for i, day in enumerate((0, 1, 2, 4, 6)):
            await self.observe(str(i), day=day, session='session-' + str(i % 3))
        result = emotions.trend(self.store, self.scope.owner)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['groups']['self_report']['distribution'], {'negative': 5})
        await self.observe('happy', day=6, text='我今天很开心', tendency='positive')
        result = emotions.trend(self.store, self.scope.owner)
        self.assertEqual(result['groups']['self_report']['distribution'], {'negative': 5, 'positive': 1})
        self.assertEqual(result['groups']['inferred']['status'], 'insufficient_observations')

    async def test_one_day_or_one_session_never_qualifies_and_inference_is_not_pooled(self):
        self.enable()
        for i in range(5):
            await self.observe('same-' + str(i), day=0, session='one')
        result = emotions.trend(self.store, self.scope.owner)
        self.assertEqual(result['status'], 'insufficient_observations')
        await self.observe('infer', day=6, text='我反复检查同一份工作', kind='inferred')
        self.assertEqual(emotions.trend(self.store, self.scope.owner)['status'], 'insufficient_observations')

    async def test_quotes_other_subject_hypothesis_and_negation_cannot_be_mislabelled(self):
        self.enable()
        tracking = emotions.consent(self.store, self.scope.owner)
        for text in ('他说我今天很难过', '假设我今天很难过', '小说台词：“我今天很难过”', '我不难过'):
            with self.subTest(text=text), self.assertRaises(MemoryError):
                emotions.validate_observations([{'source_index': 0, 'source_quote': text, 'subject': 'user',
                    'source_kind': 'self_report', 'tendency': 'negative', 'confidence': 0.9}], [text], tracking)

    async def test_disable_retains_view_but_stops_use_and_cancels_inflight_old_consent(self):
        self.enable()
        await self.observe('before')
        self.store.handle(self.scope.owner, {'action': 'emotion_consent', 'enabled': False})
        self.assertEqual(len(self.store.handle(self.scope.owner, {'action': 'observations'})['observations']), 1)
        self.assertEqual(emotions.trend(self.store, self.scope.owner), {'status': 'disabled'})
        self.enable()
        await self.observe('after', day=1)
        self.assertEqual(self.store.db.execute('SELECT consent_version FROM mia_observations WHERE message_id=\'after\'').fetchone()[0], 3)

    async def test_correction_delete_recompute_and_cross_owner_isolation(self):
        self.enable()
        for i, day in enumerate((0, 1, 2, 4, 6)):
            await self.observe('obs-' + str(i), day=day)
        target = self.store.db.execute('SELECT id FROM mia_observations ORDER BY observed_at LIMIT 1').fetchone()[0]
        with self.assertRaises(MemoryError):
            self.store.handle('foreign', {'action': 'observation_delete', 'id': target})
        self.store.handle(self.scope.owner, {'action': 'observation_update', 'id': target, 'tendency': 'neutral'})
        self.assertEqual(emotions.trend(self.store, self.scope.owner)['groups']['self_report']['distribution'], {'neutral': 1, 'negative': 4})
        self.store.handle(self.scope.owner, {'action': 'observation_delete', 'id': target})
        self.assertEqual(emotions.trend(self.store, self.scope.owner)['status'], 'insufficient_observations')

    async def test_trend_only_enters_related_context_and_disable_invalidates_other_connection(self):
        self.enable()
        for i, day in enumerate((0, 1, 2, 4, 6)):
            await self.observe('ctx-' + str(i), day=day)
        self.builder = ContextBuilder(SemanticMemoryIndex(self.store, self.encoder))
        related = await self.bundle('我最近的心情怎么样', turn='mood')
        unrelated = await self.bundle('今天的天气怎么样', turn='weather')
        self.assertEqual(related.diagnostics()['trends'], 'available')
        self.assertEqual(unrelated.diagnostics()['trends'], 'not_relevant')
        other = MemoryStore(Path(self.temp.name) / 'facts.sqlite3', clock=self.store.clock)
        try:
            other.handle(self.scope.owner, {'action': 'emotion_consent', 'enabled': False})
            with self.assertRaises(ContextError):
                await self.builder.validate(related, self.policy)
        finally:
            other.close()

    async def test_window_and_retention_expire_with_server_calendar_and_clear_prevents_revival(self):
        self.enable()
        for i, day in enumerate((0, 1, 2, 4, 6)):
            await self.observe('expiry-' + str(i), day=day)
        self.store.clock = lambda: self.epoch + 31 * emotions.DAY
        self.assertEqual(emotions.trend(self.store, self.scope.owner)['status'], 'insufficient_observations')
        self.store.clock = lambda: self.epoch + 100 * emotions.DAY
        await self.worker.run_once()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_observations').fetchone()[0], 0)
        self.store.handle(self.scope.owner, {'action': 'emotion_clear'})
        self.worker = MemoryWorker(JobStore(self.store), self.policy, self.worker.resolve, encoder=self.encoder)
        await self.worker.run_once()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_observations').fetchone()[0], 0)

    async def test_database_retry_does_not_repeat_model_or_duplicate_observation(self):
        self.enable()
        original = self.jobs.commit
        with patch.object(self.jobs, 'commit', side_effect=sqlite3.OperationalError('fixture')):
            accepted = await self.observe('retry')
        self.assertEqual(self.jobs.current(accepted)['state'], 'retry_wait')
        with self.store.db:
            self.store.db.execute('UPDATE mia_jobs SET next_attempt_at=0')
        await self.worker.run_once()
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_observations').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
