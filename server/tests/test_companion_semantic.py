"""SQLite/authorization mechanisms with named synthetic unit vectors, not embeddings."""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import threading
import unittest

import numpy as np

from server.companion.authorization import AuthenticatedScope, PrivateAuthorizationRequired
from server.companion.embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable, SemanticEncoder
from server.companion.memory import MemoryStore, MemoryError
from server.companion.semantic import SemanticMemoryIndex


class SyntheticEncoder:
    model_id, revision, dimension = MODEL_KEY, REVISION, DIMENSION

    def __init__(self):
        self.calls = []
        self.hook = None

    def encode(self, text, query=False):
        self.calls.append((text, query))
        if self.hook:
            self.hook(text, query)
        vector = np.zeros(DIMENSION, dtype=np.float32)
        vector[1 if '红' in text else 0] = 1
        return vector


class Authorization:
    def __init__(self):
        self.active = True
        self.hook = None

    async def require(self, scope, permission):
        if self.hook:
            self.hook()
        if not self.active or permission not in scope.permissions:
            raise PrivateAuthorizationRequired()


class SemanticIndexTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / 'memory.sqlite3')
        self.encoder = SyntheticEncoder()
        self.index = SemanticMemoryIndex(self.store, self.encoder)
        self.auth = Authorization()
        self.scope = AuthenticatedScope('user:1:agent:a', 1, 1, 'a', 'mia', 'device', 'client', 0, 1,
            datetime.now(timezone.utc) + timedelta(days=1), frozenset({'memory:read','memory:write','memory:manage'}))
        self.count = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def fact(self, text, owner=None, sensitive=False):
        self.count += 1
        owner = owner or self.scope.owner
        return self.store.apply_extraction(owner, 'session', self.store.snapshot(owner)['revision'], [text],
            {'memories': [{'category': 'fact', 'content': text, 'source_index': 0, 'sensitive': sensitive}]},
            str(self.count))['memories'][0]

    async def test_scope_limits_index_and_candidates_before_ranking_without_fts(self):
        own = self.fact('喜欢蓝色')
        peer = self.fact('喜欢蓝色', owner='user:2:agent:b')
        self.fact('个人私密经历', sensitive=True)
        with self.assertRaises(MemoryError):
            await self.index.index_memory(self.scope, self.auth, peer)
        self.assertEqual(self.encoder.calls, [])
        self.assertEqual((await self.index.rebuild_batch(self.scope, self.auth))['indexed'], 1)
        self.store.retrieve = lambda *args, **kwargs: self.fail('FTS/recent fallback was called')
        result = await self.index.candidates(self.scope, self.auth, '蓝色', limit=4, minimum=0.35)
        self.assertEqual([r['id'] for r in result['candidates']], [own])
        self.assertEqual((await self.index.candidates(self.scope, self.auth, '红色', minimum=0.35))['candidates'], [])
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.candidates(replace(self.scope, persona_id='other'), self.auth, '蓝色')

    async def test_missing_or_wrong_model_is_unavailable_never_silent_empty(self):
        own = self.fact('喜欢蓝色')
        with self.assertRaisesRegex(EmbeddingUnavailable, 'index_not_ready'):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        await self.index.index_memory(self.scope, self.auth, own)
        with self.store.db:
            self.store.db.execute("UPDATE mia_vectors SET model_revision='different' WHERE memory_id=?", (own,))
        with self.assertRaisesRegex(EmbeddingUnavailable, 'index_not_ready'):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        self.assertEqual((await self.index.rebuild_batch(self.scope, self.auth))['indexed'], 1)

    async def test_edits_and_deletion_remove_vectors_and_rebuild_uses_same_fact_id(self):
        own = self.fact('喜欢蓝色')
        await self.index.index_memory(self.scope, self.auth, own)
        self.store.edit_memory(self.scope.owner, own, '现在喜欢红色')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        with self.assertRaisesRegex(EmbeddingUnavailable, 'index_not_ready'):
            await self.index.candidates(self.scope, self.auth, '红色')
        await self.index.index_memory(self.scope, self.auth, own)
        result = await self.index.candidates(self.scope, self.auth, '红色', minimum=0.35)
        self.assertEqual(result['candidates'][0]['id'], own)
        self.assertEqual(result['candidates'][0]['content_version'], 2)
        self.store.delete_memory(self.scope.owner, own)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.assertEqual((await self.index.candidates(self.scope, self.auth, '红色'))['candidates'], [])

    async def test_change_or_revocation_during_encode_prevents_index_commit(self):
        own = self.fact('喜欢蓝色')
        self.encoder.hook = lambda *args: self.store.edit_memory(self.scope.owner, own, '现在喜欢红色')
        with self.assertRaisesRegex(EmbeddingUnavailable, 'memory_changed'):
            await self.index.index_memory(self.scope, self.auth, own)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.encoder.hook = lambda *args: setattr(self.auth, 'active', False)
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.index_memory(self.scope, self.auth, own)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)

    async def test_revocation_observed_after_commit_compensates_derived_vector_only(self):
        own = self.fact('喜欢蓝色')
        def revoke_after_commit():
            with self.store.lock:
                if self.store.db.execute('SELECT 1 FROM mia_vectors').fetchone():
                    self.auth.active = False
        self.auth.hook = revoke_after_commit
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.index_memory(self.scope, self.auth, own)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        self.assertEqual(self.store.list_memories(self.scope.owner)[0]['id'], own)

    async def test_corrupt_vector_or_query_is_rejected_not_empty_recall(self):
        own = self.fact('喜欢蓝色')
        await self.index.index_memory(self.scope, self.auth, own)
        with self.store.db:
            self.store.db.execute('UPDATE mia_vectors SET normalized_vector=? WHERE memory_id=?', (bytes(DIMENSION * 4), own))
        with self.assertRaisesRegex(EmbeddingUnavailable, 'index_invalid'):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        self.encoder.encode = lambda *args: np.full(DIMENSION, np.nan, dtype=np.float32)
        with self.assertRaisesRegex(EmbeddingUnavailable, 'vector_invalid'):
            await self.index.candidates(self.scope, self.auth, '蓝色')

    async def test_cancelled_encodes_keep_slots_until_threads_finish_and_never_commit(self):
        own = self.fact('喜欢蓝色')
        release = threading.Event()
        self.encoder.hook = lambda *args: release.wait(5)
        tasks = [asyncio.create_task(self.index.index_memory(self.scope, self.auth, own)) for _ in range(2)]
        try:
            for _ in range(100):
                if len(self.encoder.calls) == 2:
                    break
                await asyncio.sleep(0.01)
            self.assertEqual(len(self.encoder.calls), 2)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            with self.assertRaisesRegex(EmbeddingUnavailable, 'embedding_busy'):
                await self.index.index_memory(self.scope, self.auth, own)
            self.assertEqual(len(self.encoder.calls), 2)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.05)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)

    def test_invalid_assets_fail_before_optional_native_runtime_import(self):
        with self.assertRaisesRegex(EmbeddingUnavailable, 'assets_invalid'):
            SemanticEncoder(Path(self.temp.name) / 'missing-assets')


if __name__ == '__main__':
    unittest.main()
