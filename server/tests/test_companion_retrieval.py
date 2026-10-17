"""Controlled S/L/A/E, candidate omissions and lifecycle; vectors are synthetic."""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np

from server.companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from server.companion.memory import MemoryStore
from server.companion.retrieval import FeatureCache, WEIGHTS, rank, signals
from server.companion.semantic import SemanticMemoryIndex


class ControlledEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION

    def __init__(self):
        self.hook = None

    def encode(self, text, query=False):
        if self.hook:
            self.hook(text, query)
        cosine = 0.9 if text.startswith('干扰') else 0.4
        vector = np.zeros(DIMENSION, dtype=np.float32)
        vector[:2] = (cosine, (1 - cosine ** 2) ** 0.5)
        if query:
            vector[:2] = (0, 1) if '关联线索' in text else (1, 0)
        return vector


class Policy:
    active = True

    async def require(self, scope, permission):
        if not self.active or permission not in scope.permissions:
            raise PrivateAuthorizationRequired()


class HybridRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / 'memory.sqlite3')
        self.encoder, self.auth = ControlledEncoder(), Policy()
        self.index = SemanticMemoryIndex(self.store, self.encoder)
        self.scope = AuthenticatedScope('user:1:agent:a', 1, 1, 'a', 'mia', 'device', 'client', 0, 1,
            datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read', 'memory:write', 'memory:manage'}))
        self.count = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def fact(self, text, owner=None, triggers=None, keywords=None, emotion=None, state='active'):
        self.count += 1
        owner = owner or self.scope.owner
        memory_id = self.store.apply_extraction(owner, 'fixture', self.store.snapshot(owner)['revision'], [text],
            {'memories': [{'category': 'fact', 'content': text, 'source_index': 0, 'sensitive': state == 'pending'}]},
            str(self.count))['memories'][0]
        with self.store.db:
            self.store.db.execute('UPDATE mia_memory_meta SET entities=?,keywords=?,trigger_terms=?,emotional_weight=?,state=? '
                'WHERE memory_id=?', (json.dumps([]), json.dumps(keywords or []), json.dumps(triggers or []), emotion, state, memory_id))
        return memory_id

    async def test_expansion_recovers_outside_original_top12_and_all_sources_are_traced(self):
        target = self.fact('海鲜过敏需要避开扇贝', triggers=['点菜'], keywords=['扇贝', '过敏'], emotion=0.4)
        for i in range(13):
            self.fact('干扰记录' + str(i))
        await self.index.rebuild_batch(self.scope, self.auth)
        original = (await self.index.candidates(self.scope, self.auth, '点菜'))['candidates']
        self.assertNotIn(target, [row['id'] for row in original])
        result = await self.index.retrieve(self.scope, self.auth, '点菜')
        self.assertEqual(result['results'][0]['id'], target)
        candidate = next(row for row in result['candidates'] if row['id'] == target)
        self.assertNotIn('original', candidate['candidate_sources'])
        self.assertIn('expanded', candidate['candidate_sources'])
        self.assertIn('association', candidate['candidate_sources'])
        self.assertEqual(set(candidate['signals']), set(WEIGHTS))
        self.assertTrue(all(value > 0 for value in candidate['signals'].values()))
        self.assertEqual({clue['memory_id'] for clue in result['expansion']}, {target})
        self.assertTrue(all(clue['content_version'] == 1 and clue['evidence_version'] >= 1 for clue in result['expansion']))
        self.assertLessEqual(len(result['candidates']), 48)
        self.assertLessEqual(len(result['results']), 4)

    async def test_lexical_association_supplement_retains_missing_candidate_even_without_expanded_gain(self):
        target = self.fact('点菜要避开扇贝', triggers=['点菜'], keywords=['扇贝'])
        for i in range(13):
            self.fact('干扰记录' + str(i))
        await self.index.rebuild_batch(self.scope, self.auth)
        original_encode = self.encoder.encode
        self.encoder.encode = lambda text, query=False: original_encode('点菜' if query else text, query)
        result = await self.index.retrieve(self.scope, self.auth, '点菜')
        candidate = next(row for row in result['candidates'] if row['id'] == target)
        self.assertNotIn('original', candidate['candidate_sources'])
        self.assertNotIn('expanded', candidate['candidate_sources'])
        self.assertEqual(set(candidate['candidate_sources']), {'lexical', 'association'})

    async def test_foreign_and_inactive_metadata_never_expand_or_rank_and_revocation_is_checked(self):
        own = self.fact('养薄荷前检查土壤', triggers=['浇水'], keywords=['薄荷'])
        for owner in ('user:2:agent:a', 'user:1:agent:b'):
            self.fact('私人证据', owner=owner, triggers=['浇水'], keywords=['绝不能扩展'])
        for state in ('pending', 'superseded', 'invalidated'):
            self.fact('无效线索' + state, triggers=['浇水'], keywords=['无效扩展'], state=state)
        await self.index.rebuild_batch(self.scope, self.auth)
        result = await self.index.retrieve(self.scope, self.auth, '浇水')
        self.assertEqual({r['id'] for r in result['candidates']}, {own})
        self.assertEqual([r['term'] for r in result['expansion']], ['薄荷'])
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.retrieve(replace(self.scope, persona_id='other'), self.auth, '浇水')
        self.encoder.hook = lambda *args: setattr(self.auth, 'active', False)
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.retrieve(self.scope, self.auth, '浇水')

    async def test_metadata_change_during_encode_rejects_old_clues_and_removed_source_clears_them(self):
        own = self.fact('海鲜过敏需要避开扇贝', triggers=['点菜'], keywords=['扇贝'], emotion=1)
        await self.index.rebuild_batch(self.scope, self.auth)
        def change(*args):
            with self.store.db:
                self.store.db.execute('UPDATE mia_memory_meta SET trigger_terms=NULL WHERE memory_id=?', (own,))
        self.encoder.hook = change
        with self.assertRaisesRegex(EmbeddingUnavailable, 'memory_changed'):
            await self.index.retrieve(self.scope, self.auth, '点菜')
        self.encoder.hook = None
        with self.store.db:
            self.store.db.execute('DELETE FROM sources WHERE memory_id=?', (own,))
        meta = self.store.db.execute('SELECT entities,keywords,trigger_terms,emotional_weight FROM mia_memory_meta WHERE memory_id=?', (own,)).fetchone()
        self.assertEqual(tuple(meta), (None, None, None, None))
        self.assertEqual((await self.index.retrieve(self.scope, self.auth, '点菜'))['expansion'], [])

    async def test_missing_index_invalid_metadata_and_deleted_clues_are_not_silent_success(self):
        own = self.fact('点菜避开扇贝', triggers=['点菜'], keywords=['扇贝'])
        with self.assertRaisesRegex(EmbeddingUnavailable, 'index_not_ready'):
            await self.index.retrieve(self.scope, self.auth, '点菜')
        await self.index.rebuild_batch(self.scope, self.auth)
        with self.store.db:
            self.store.db.execute("UPDATE mia_memory_meta SET trigger_terms='not-json' WHERE memory_id=?", (own,))
        with self.assertRaisesRegex(EmbeddingUnavailable, 'metadata_invalid'):
            await self.index.retrieve(self.scope, self.auth, '点菜')
        self.store.delete_memory(self.scope.owner, own)
        result = await self.index.retrieve(self.scope, self.auth, '点菜')
        self.assertEqual(result['expansion'], [])
        self.assertEqual(result['results'], [])

    async def test_shared_features_match_uncached_candidates_and_cross_connection_changes(self):
        own = self.fact('散步带蓝色水壶', triggers=['散步'], keywords=['蓝色水壶'])
        self.fact('练琴带节拍器', triggers=['练琴'], keywords=['节拍器'])
        await self.index.rebuild_batch(self.scope, self.auth)
        cached = await self.index.retrieve(self.scope, self.auth, '散步')
        other = SemanticMemoryIndex(self.store, self.encoder)
        self.assertIs(other._features, self.index._features)
        other._features = FeatureCache()
        with patch('server.companion.retrieval.FEATURE_CACHE_BYTES', 0):
            uncached = await other.retrieve(self.scope, self.auth, '散步')
        self.assertEqual(cached, uncached)
        # Independent SQLite connection: warm cache must not keep old clues.
        second = MemoryStore(Path(self.temp.name) / 'memory.sqlite3')
        try:
            with second.lock, second.db:
                second.db.execute('UPDATE mia_memory_meta SET keywords=? WHERE memory_id=?',
                                  ('["新水壶"]', own))
            changed = await self.index.retrieve(self.scope, self.auth, '散步')
            self.assertEqual([row['term'] for row in changed['expansion']], ['新水壶'])
            second.delete_memory(self.scope.owner, own)
            deleted = await self.index.retrieve(self.scope, self.auth, '散步')
            self.assertNotIn(own, [row['id'] for row in deleted['candidates']])
            self.assertEqual(deleted['expansion'], [])
        finally:
            second.close()

    async def test_read_snapshot_does_not_block_deletion_and_old_result_is_rejected(self):
        own = self.fact('散步带水壶', triggers=['散步'], keywords=['水壶'])
        await self.index.rebuild_batch(self.scope, self.auth)
        scanning, release = threading.Event(), threading.Event()
        prepare = self.index._features.prepare

        def held(*args):
            scanning.set()
            if not release.wait(3):
                raise AssertionError('Concurrent deletion did not release held scan')
            return prepare(*args)

        self.index._features.prepare = held
        task = asyncio.create_task(self.index.retrieve(self.scope, self.auth, '散步'))
        try:
            self.assertTrue(await asyncio.to_thread(scanning.wait, 3))
            # The scan is still open. Deletion through the original write
            # connection must finish before the reader is allowed to continue.
            await asyncio.wait_for(asyncio.to_thread(self.store.delete_memory, self.scope.owner, own), 1)
        finally:
            release.set()
            self.index._features.prepare = prepare
        with self.assertRaisesRegex(EmbeddingUnavailable, 'memory_changed'):
            await task
        self.assertEqual((await self.index.retrieve(self.scope, self.auth, '散步'))['results'], [])

    async def test_large_scope_fallback_matches_cached_results(self):
        self.fact('散步带水壶', triggers=['散步'], keywords=['水壶'])
        self.fact('练琴带节拍器', triggers=['练琴'], keywords=['节拍器'])
        await self.index.rebuild_batch(self.scope, self.auth)
        expected = await self.index.retrieve(self.scope, self.auth, '散步')
        self.index._features = FeatureCache()
        with patch('server.companion.retrieval.FEATURE_CACHE_ENTRIES', 1):
            actual = await self.index.retrieve(self.scope, self.auth, '散步')
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.index._features.entries), 0)

    async def test_background_waits_for_shared_foreground_and_resumes_after_cancel(self):
        self.fact('散步带水壶')
        await self.index.rebuild_batch(self.scope, self.auth)
        foreign = replace(self.scope, owner='user:2:agent:a')
        own = self.fact('后台记录', owner=foreign.owner)
        other = SemanticMemoryIndex(self.store, self.encoder)
        entered, release, background = threading.Event(), threading.Event(), threading.Event()

        def held(text, query):
            if query:
                entered.set()
                if not release.wait(3):
                    raise AssertionError('Foreground query was not released')
            else:
                background.set()

        self.encoder.hook = held
        foreground = asyncio.create_task(self.index.retrieve(self.scope, self.auth, '散步'))
        pending = None
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            self.assertIs(other._activity, self.index._activity)
            with self.assertRaises(asyncio.TimeoutError):
                await other._background_ready(0.01)
            pending = asyncio.create_task(other.index_memory(foreign, self.auth, own))
            self.assertFalse(await asyncio.to_thread(background.wait, 0.05))
            foreground.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await foreground
            self.assertEqual(self.index._activity['foreground'], 0)
            await asyncio.wait_for(pending, 2)
            self.assertTrue(background.is_set())
            # Cancelling the caller does not free its still-running native slot.
            self.assertEqual(self.index._slots._value, 1)
        finally:
            release.set()
            await asyncio.gather(foreground, *([pending] if pending else []), return_exceptions=True)
            self.encoder.hook = None
        for _ in range(100):
            if self.index._slots._value == 2:
                break
            await asyncio.sleep(0.01)
        self.assertEqual(self.index._slots._value, 2)

    async def test_eight_clue_limit_keeps_order_and_does_not_hide_invalid_tail(self):
        for i in range(10):
            self.fact('记录' + str(i), triggers=['散步'], keywords=['线索' + str(i)])
        await self.index.rebuild_batch(self.scope, self.auth)
        with self.store.lock:
            ids = [row['id'] for row in self.store.db.execute('SELECT id FROM memories ORDER BY id')]
            expected = [self.store.db.execute('SELECT keywords FROM mia_memory_meta WHERE memory_id=?',
                (memory_id,)).fetchone()[0] for memory_id in ids[:8]]
        result = await self.index.retrieve(self.scope, self.auth, '散步')
        self.assertEqual([item['term'] for item in result['expansion']], [json.loads(value)[0] for value in expected])
        with self.store.db:
            self.store.db.execute("UPDATE mia_memory_meta SET keywords='invalid' WHERE memory_id=?", (ids[-1],))
        with self.assertRaisesRegex(EmbeddingUnavailable, 'metadata_invalid'):
            await self.index.retrieve(self.scope, self.auth, '散步')

    def test_each_signal_can_change_ranking_and_emotion_cannot_override_original_floor(self):
        for dimension in WEIGHTS:
            with self.subTest(dimension=dimension):
                base = {name: 0.5 for name in WEIGHTS}
                a = {'id': 'a', 'original_cosine': 0.5, 'signals': dict(base)}
                b = {'id': 'b', 'original_cosine': 0.5, 'signals': dict(base)}
                self.assertEqual(rank([a, b])[0]['id'], 'b')
                a['signals'][dimension] = 0.6
                self.assertEqual(rank([a, b])[0]['id'], 'a')
                self.assertAlmostEqual(a['score'] - b['score'], 0.1 * WEIGHTS[dimension])
        irrelevant = {'id': 'unrelated', 'original_cosine': 0.34, 'signals': {name: 1.0 for name in WEIGHTS}}
        self.assertEqual(rank([irrelevant]), [])
        self.assertFalse(irrelevant['accepted'])
        row = {'content': '普通长期偏好', 'entities': None, 'keywords': None, 'trigger_terms': None, 'emotional_weight': None}
        score, _, _ = signals('普通长期偏好', row, 0.5)
        self.assertEqual(score['emotion'], 0)
        self.assertEqual(row['emotional_weight'], None)


if __name__ == '__main__':
    unittest.main()
