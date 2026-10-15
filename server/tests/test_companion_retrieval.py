"""Controlled S/L/A/E, candidate omissions and lifecycle; vectors are synthetic."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from server.companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from server.companion.memory import MemoryStore
from server.companion.retrieval import WEIGHTS, rank, signals
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
