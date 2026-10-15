"""Scope-first exact vectors in the existing fact DB; full hybrid RAG is P13."""

import asyncio
import heapq
import time

from .authorization import AuthenticatedScope, PrivateAuthorizationRequired
from .embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from .memory import MemoryError


class SemanticMemoryIndex:
    def __init__(self, store, encoder):
        if (encoder.model_id, encoder.revision, encoder.dimension) != (MODEL_KEY, REVISION, DIMENSION):
            raise EmbeddingUnavailable('embedding_model_mismatch')
        self.store, self.encoder = store, encoder
        self._slots = asyncio.Semaphore(2)

    async def _require(self, scope, authorization, permission):
        if not isinstance(scope, AuthenticatedScope) or scope.persona_id != 'mia':
            raise PrivateAuthorizationRequired()
        await authorization.require(scope, permission)

    def _state(self, scope):
        row = self.store.db.execute('SELECT o.revision,s.content_epoch FROM owners o '
                                    'JOIN mia_scope_versions s ON s.owner=o.owner WHERE o.owner=?', (scope.owner,)).fetchone()
        return tuple(row) if row else (0, 0)

    def _snapshot(self, scope):
        with self.store.lock:
            return self._state(scope)

    def _check(self, scope, expected):
        if self._state(scope) != expected:
            raise EmbeddingUnavailable('memory_changed')

    async def _encode(self, text, query=False):
        try:
            await asyncio.wait_for(self._slots.acquire(), timeout=0.4)
        except asyncio.TimeoutError:
            raise EmbeddingUnavailable('embedding_busy') from None
        # Cancelling the caller must not release a still-running native inference
        # slot or allow that result to reach the subsequent commit.
        future = asyncio.get_running_loop().run_in_executor(None, self.encoder.encode, text, query)
        def completed(result):
            self._slots.release()
            if not result.cancelled():
                result.exception()  # Retrieve errors even if the caller timed out.
        future.add_done_callback(completed)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=3)
        except asyncio.TimeoutError:
            raise EmbeddingUnavailable('embedding_timeout') from None

    def _record(self, scope, memory_id):
        with self.store.lock:
            row = self.store.db.execute('SELECT m.content,x.content_version FROM memories m '
                'JOIN mia_memory_meta x ON x.memory_id=m.id WHERE m.owner=? AND m.id=? '
                "AND x.persona_id=? AND m.confirmed=1 AND x.state='active'",
                (scope.owner, memory_id, scope.persona_id)).fetchone()
            if not row:
                raise MemoryError('not_found', 'Active memory not found')
            return row['content'], row['content_version'], self._state(scope)

    def _vector(self, vector):
        import numpy as np
        vector = np.asarray(vector, dtype='<f4')
        if vector.shape != (DIMENSION,) or not np.isfinite(vector).all() or abs(float(np.linalg.norm(vector)) - 1) > 1e-4:
            raise EmbeddingUnavailable('embedding_vector_invalid')
        return vector

    def _commit(self, scope, memory_id, content, version, state, vector):
        vector = self._vector(vector)
        with self.store.lock, self.store.db:
            self.store.db.execute('BEGIN IMMEDIATE')
            self._check(scope, state)
            current = self._record(scope, memory_id)
            if current[:2] != (content, version):
                raise EmbeddingUnavailable('memory_changed')
            self.store.db.execute('INSERT INTO mia_vectors(memory_id,model_id,model_revision,dimension,content_version,'
                'normalized_vector,indexed_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(memory_id) DO UPDATE SET '
                'model_id=excluded.model_id,model_revision=excluded.model_revision,dimension=excluded.dimension,'
                'content_version=excluded.content_version,normalized_vector=excluded.normalized_vector,indexed_at=excluded.indexed_at',
                (memory_id, MODEL_KEY, REVISION, DIMENSION, version, vector.tobytes(), int(time.time())))

    async def index_memory(self, scope, authorization, memory_id):
        await self._require(scope, authorization, 'memory:write')
        content, version, state = await asyncio.to_thread(self._record, scope, memory_id)
        vector = await self._encode(content)
        await self._require(scope, authorization, 'memory:write')
        await asyncio.to_thread(self._commit, scope, memory_id, content, version, state, vector)
        try:
            await self._require(scope, authorization, 'memory:write')
        except PrivateAuthorizationRequired:
            # Derived cache only: compensate if revocation is observed immediately
            # after the local commit. Original facts are never rewritten here.
            await asyncio.to_thread(self._remove, scope, memory_id, version)
            raise
        return {'id': memory_id, 'content_version': version, 'indexed': True}

    def _remove(self, scope, memory_id, version):
        with self.store.lock, self.store.db:
            self.store.db.execute('DELETE FROM mia_vectors WHERE memory_id=? AND content_version=? AND '
                'model_id=? AND model_revision=? AND memory_id IN (SELECT id FROM memories WHERE owner=?)',
                (memory_id, version, MODEL_KEY, REVISION, scope.owner))

    def _scan(self, scope, expected, query, limit, minimum):
        import numpy as np
        query = self._vector(query)
        with self.store.lock, self.store.db:
            self.store.db.execute('BEGIN')
            self._check(scope, expected)
            base = (' FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                    'LEFT JOIN mia_vectors v ON v.memory_id=m.id AND v.model_id=? AND v.model_revision=? '
                    'AND v.dimension=? AND v.content_version=x.content_version '
                    "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active'")
            params = (MODEL_KEY, REVISION, DIMENSION, scope.owner, scope.persona_id)
            counts = self.store.db.execute('SELECT COUNT(*),COUNT(v.memory_id)' + base, params).fetchone()
            if counts[0] != counts[1]:
                raise EmbeddingUnavailable('embedding_index_not_ready')
            cursor = self.store.db.execute('SELECT m.id,m.content,m.category,x.content_version,x.evidence_version,'
                'x.entities,x.keywords,x.trigger_terms,x.emotional_weight,v.normalized_vector' + base, params)
            heap = []
            while True:
                rows = cursor.fetchmany(256)
                if not rows:
                    break
                try:
                    matrix = np.stack([np.frombuffer(row['normalized_vector'], dtype='<f4') for row in rows])
                except (ValueError, TypeError):
                    raise EmbeddingUnavailable('embedding_index_invalid') from None
                if matrix.shape != (len(rows), DIMENSION) or not np.isfinite(matrix).all() or not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-4):
                    raise EmbeddingUnavailable('embedding_index_invalid')
                # Avoid changing the voice process's global BLAS thread settings.
                scores = np.clip(np.einsum('ij,j->i', matrix, query, optimize=False), -1, 1)
                for row, score in zip(rows, scores):
                    score = float(score)
                    if minimum is not None and score < minimum:
                        continue
                    if len(heap) == limit and (score, row['id']) <= heap[0][:2]:
                        continue
                    record = {key: row[key] for key in row.keys() if key != 'normalized_vector'}
                    record['cosine'] = score
                    entry = (score, row['id'], record)
                    if len(heap) < limit:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
            return [item[2] for item in sorted(heap, reverse=True)]

    async def candidates(self, scope, authorization, query, limit=12, minimum=None):
        if type(limit) is not int or not 1 <= limit <= 24 or (minimum is not None and not -1 <= minimum <= 1):
            raise ValueError('Invalid vector candidate limits')
        if not isinstance(query, str) or not query.strip() or len(query) > 4096:
            raise ValueError('Invalid vector query')
        await self._require(scope, authorization, 'memory:read')
        state = await asyncio.to_thread(self._snapshot, scope)
        vector = await self._encode(query, query=True)
        rows = await asyncio.to_thread(self._scan, scope, state, vector, limit, minimum)
        await self._require(scope, authorization, 'memory:read')
        await asyncio.to_thread(self._snapshot_check, scope, state)
        return {'snapshot': {'revision': state[0], 'content_epoch': state[1]}, 'candidates': rows}

    def _snapshot_check(self, scope, expected):
        with self.store.lock:
            self._check(scope, expected)

    def _missing(self, scope, limit):
        with self.store.lock:
            return [row[0] for row in self.store.db.execute('SELECT m.id FROM memories m '
                'JOIN mia_memory_meta x ON x.memory_id=m.id LEFT JOIN mia_vectors v ON v.memory_id=m.id '
                'AND v.model_id=? AND v.model_revision=? AND v.dimension=? AND v.content_version=x.content_version '
                "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active' AND v.memory_id IS NULL "
                'ORDER BY m.id LIMIT ?', (MODEL_KEY, REVISION, DIMENSION, scope.owner, scope.persona_id, limit))]

    async def rebuild_batch(self, scope, authorization, limit=32):
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError('Invalid index rebuild batch')
        await self._require(scope, authorization, 'memory:write')
        ids = await asyncio.to_thread(self._missing, scope, limit)
        for memory_id in ids:
            await self.index_memory(scope, authorization, memory_id)
        await self._require(scope, authorization, 'memory:write')
        remaining = await asyncio.to_thread(self._missing, scope, 1)
        return {'indexed': len(ids), 'has_more': bool(remaining)}
