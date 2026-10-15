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

    async def test_timed_out_native_encodes_keep_slots_and_cannot_commit_late(self):
        own = self.fact('喜欢蓝色')
        release = threading.Event()
        self.encoder.hook = lambda *args: release.wait(10)
        tasks = [asyncio.create_task(self.index.index_memory(self.scope, self.auth, own)) for _ in range(2)]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self.assertEqual(len(self.encoder.calls), 2)
            for error in results:
                self.assertIsInstance(error, EmbeddingUnavailable)
                self.assertEqual(str(error), 'embedding_timeout')
            with self.assertRaisesRegex(EmbeddingUnavailable, 'embedding_busy'):
                await self.index.index_memory(self.scope, self.auth, own)
            self.assertEqual(len(self.encoder.calls), 2)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.encoder.hook = None
        # Retry only after the native work has completed, without replacing the
        # index/semaphore. Timed-out results must never appear in SQLite.
        for _ in range(100):
            if not self.index._slots.locked():
                break
            await asyncio.sleep(0.01)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM mia_vectors').fetchone()[0], 0)
        await self.index.index_memory(self.scope, self.auth, own)
        self.assertEqual((await self.index.candidates(self.scope, self.auth, '蓝色'))['candidates'][0]['id'], own)

    async def test_query_changes_during_encode_and_after_scan_do_not_return_stale_facts(self):
        for phase in ('encode', 'after_scan'):
            for action in ('edit', 'delete', 'clear', 'pause'):
                with self.subTest(phase=phase, action=action):
                    self.store.set_paused(self.scope.owner, False)
                    own = self.fact('喜欢蓝色')
                    await self.index.rebuild_batch(self.scope, self.auth)
                    def change():
                        if action == 'edit':
                            self.store.edit_memory(self.scope.owner, own, '现在喜欢红色')
                        elif action == 'delete':
                            self.store.delete_memory(self.scope.owner, own)
                        elif action == 'clear':
                            self.store.clear(self.scope.owner)
                        else:
                            self.store.set_paused(self.scope.owner, True)
                    scanned = threading.Event()
                    original_scan = self.index._scan
                    def scan(*args):
                        result = original_scan(*args)
                        scanned.set()
                        return result
                    if phase == 'encode':
                        self.encoder.hook = lambda *args: change()
                    else:
                        self.index._scan = scan
                        self.auth.hook = lambda: change() if scanned.is_set() else None
                    try:
                        with self.assertRaisesRegex(EmbeddingUnavailable, 'memory_changed'):
                            await self.index.candidates(self.scope, self.auth, '蓝色')
                    finally:
                        self.encoder.hook = self.auth.hook = None
                        self.index._scan = original_scan

    async def test_query_revocation_after_scan_and_encoder_failure_are_not_empty_success(self):
        own = self.fact('喜欢蓝色')
        await self.index.index_memory(self.scope, self.auth, own)
        scanned = threading.Event()
        original_scan = self.index._scan
        def scan(*args):
            result = original_scan(*args)
            scanned.set()
            return result
        self.index._scan = scan
        self.auth.hook = lambda: setattr(self.auth, 'active', False) if scanned.is_set() else None
        with self.assertRaises(PrivateAuthorizationRequired):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        self.auth.hook = None
        self.auth.active = True
        def fail(*args):
            raise EmbeddingUnavailable('embedding_inference_failed')
        self.encoder.hook = fail
        with self.assertRaisesRegex(EmbeddingUnavailable, 'embedding_inference_failed'):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        self.encoder.hook = None
        self.assertEqual((await self.index.candidates(self.scope, self.auth, '蓝色'))['candidates'][0]['id'], own)

    async def test_reopen_and_rebuild_preserve_facts_and_exclude_nonactive_states(self):
        own = self.fact('喜欢蓝色')
        excluded = [self.fact('蓝色经历' + str(i)) for i in range(3)]
        with self.store.db:
            for memory_id, state in zip(excluded, ('pending', 'superseded', 'invalidated')):
                self.store.db.execute('UPDATE mia_memory_meta SET state=? WHERE memory_id=?', (state, memory_id))
        await self.index.rebuild_batch(self.scope, self.auth)
        facts = [tuple(row) for row in self.store.db.execute('SELECT * FROM memories ORDER BY id')]
        self.store.close()
        self.store = MemoryStore(Path(self.temp.name) / 'memory.sqlite3')
        self.index = SemanticMemoryIndex(self.store, self.encoder)
        self.assertEqual([r['id'] for r in (await self.index.candidates(self.scope, self.auth, '蓝色'))['candidates']], [own])
        with self.store.db:
            self.store.db.execute('DELETE FROM mia_vectors')
        with self.assertRaisesRegex(EmbeddingUnavailable, 'embedding_index_not_ready'):
            await self.index.candidates(self.scope, self.auth, '蓝色')
        self.assertEqual(await self.index.rebuild_batch(self.scope, self.auth), {'indexed': 1, 'has_more': False})
        self.assertEqual([tuple(row) for row in self.store.db.execute('SELECT * FROM memories ORDER BY id')], facts)
        self.assertEqual([r['id'] for r in (await self.index.candidates(self.scope, self.auth, '蓝色'))['candidates']], [own])

    def test_invalid_assets_fail_before_optional_native_runtime_import(self):
        with self.assertRaisesRegex(EmbeddingUnavailable, 'assets_invalid'):
            SemanticEncoder(Path(self.temp.name) / 'missing-assets')


if __name__ == '__main__':
    unittest.main()
