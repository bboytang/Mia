"""Scope-first exact vectors and hybrid retrieval in the existing fact DB."""

import asyncio
from contextlib import closing
import heapq
from pathlib import Path
import sqlite3
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
        from .retrieval import FeatureCache
        with store.lock:
            self._database_uri = Path(store.db.execute('PRAGMA database_list').fetchone()['file']).as_uri() + '?mode=ro'
            if not hasattr(store, '_mia_retrieval_features'):
                store._mia_retrieval_features = FeatureCache()
            self._features = store._mia_retrieval_features

    async def _require(self, scope, authorization, permission):
        if not isinstance(scope, AuthenticatedScope) or scope.persona_id != 'mia':
            raise PrivateAuthorizationRequired()
        await authorization.require(scope, permission)

    def _state(self, scope, db=None):
        row = (db if db is not None else self.store.db).execute('SELECT o.revision,s.content_epoch FROM owners o '
                                    'JOIN mia_scope_versions s ON s.owner=o.owner WHERE o.owner=?', (scope.owner,)).fetchone()
        return tuple(row) if row else (0, 0)

    def _snapshot(self, scope):
        with self.store.lock:
            return self._state(scope)

    def _check(self, scope, expected, db=None):
        if self._state(scope, db) != expected:
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

    def _scan(self, scope, expected, query, limit, minimum, query_text=None, expanded=None):
        import numpy as np
        from .retrieval import FEATURE_CACHE_ENTRIES, bigrams, pair_codes, signals
        query = self._vector(query)
        expanded = query if expanded is None else self._vector(expanded)
        query_terms = bigrams(query_text) if query_text is not None else None
        query_codes = pair_codes(query_terms) if query_terms is not None else None
        records = []
        # A private read-only WAL snapshot cannot hold the application's write
        # connection lock while scoring. retrieve/candidates still recheck the
        # current epoch and authorization before releasing these results.
        with closing(sqlite3.connect(self._database_uri, uri=True)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            self._check(scope, expected, db)
            use_cache = False
            if query_text is not None:
                self._features.begin(scope, expected)
                count = db.execute('SELECT COUNT(*) FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                    "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active'",
                    (scope.owner, scope.persona_id)).fetchone()[0]
                use_cache = count <= FEATURE_CACHE_ENTRIES
            base = (' FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                    'LEFT JOIN mia_vectors v ON v.memory_id=m.id AND v.model_id=? AND v.model_revision=? '
                    'AND v.dimension=? AND v.content_version=x.content_version '
                    "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active'")
            params = (MODEL_KEY, REVISION, DIMENSION, scope.owner, scope.persona_id)
            cursor = db.execute('SELECT m.id,m.content,m.category,x.content_version,x.evidence_version,'
                'x.entities,x.keywords,x.trigger_terms,x.emotional_weight,v.normalized_vector' + base, params)
            heaps = {name: [] for name in (('original',) if query_text is None else ('original', 'expanded', 'lexical', 'association'))}
            while True:
                rows = cursor.fetchmany(256)
                if not rows:
                    break
                if any(row['normalized_vector'] is None for row in rows):
                    raise EmbeddingUnavailable('embedding_index_not_ready')
                try:
                    matrix = np.stack([np.frombuffer(row['normalized_vector'], dtype='<f4') for row in rows])
                except (ValueError, TypeError):
                    raise EmbeddingUnavailable('embedding_index_invalid') from None
                if matrix.shape != (len(rows), DIMENSION) or not np.isfinite(matrix).all() or not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-4):
                    raise EmbeddingUnavailable('embedding_index_invalid')
                # Avoid changing the voice process's global BLAS thread settings.
                scores = np.clip(np.einsum('ij,j->i', matrix, query, optimize=False), -1, 1)
                expanded_scores = scores if expanded is query else np.clip(np.einsum('ij,j->i', matrix, expanded, optimize=False), -1, 1)
                for row, score, expanded_score in zip(rows, scores, expanded_scores):
                    score = float(score)
                    if minimum is not None and score < minimum:
                        continue
                    if query_text is None and len(heaps['original']) == limit and (score, row['id']) <= heaps['original'][0][:2]:
                        continue
                    record = {key: row[key] for key in row.keys() if key != 'normalized_vector'}
                    record['cosine'] = score
                    if query_text is not None:
                        record['original_cosine'], record['expanded_cosine'] = score, float(expanded_score)
                        records.append(record)
                        continue
                    heap = heaps['original']
                    entry = (score, row['id'], record)
                    if len(heap) < limit:
                        heapq.heappush(heap, entry)
                    elif entry[:2] > heap[0][:2]:
                        heapq.heapreplace(heap, entry)
        if query_text is None:
            return [item[2] for item in sorted(heaps['original'], reverse=True)]
        # Close the read transaction before CPU scoring: forgetting must be able
        # to finish its WAL purge while scoring is in progress. Retain metadata
        # and scalar cosines only, never the Scope's full vector matrix.
        for record in records:
            score, expanded_score = record['original_cosine'], record['expanded_cosine']
            record['signals'], record['lexical_hits'], record['association_hits'] = signals(
                query_text, record, max(score, expanded_score), query_terms,
                prepared=self._features.prepare(scope, expected, record) if use_cache else None,
                query_codes=query_codes)
            values = {'original': score, 'expanded': expanded_score,
                      'lexical': record['signals']['lexical'], 'association': record['signals']['association']}
            for name, value in values.items():
                if name in ('lexical', 'association') and value <= 0:
                    continue
                heap = heaps[name]
                entry = (value, record['id'], record)
                if len(heap) < limit:
                    heapq.heappush(heap, entry)
                elif entry[:2] > heap[0][:2]:
                    heapq.heapreplace(heap, entry)
        selected = {}
        for name, heap in heaps.items():
            for _, memory_id, row in heap:
                if memory_id not in selected:
                    selected[memory_id] = dict(row, candidate_sources=[])
                selected[memory_id]['candidate_sources'].append(name)
        return sorted(selected.values(), key=lambda row: (row['original_cosine'], row['id']), reverse=True)

    def _clues(self, scope, expected, query):
        from .retrieval import terms
        clues = {}
        with self.store.lock:
            self._check(scope, expected)
            self._features.begin(scope, expected)
            cursor = self.store.db.execute('SELECT m.id,x.content_version,x.evidence_version,x.entities,x.keywords,x.trigger_terms '
                'FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active' ORDER BY m.id",
                (scope.owner, scope.persona_id))
            for row in cursor:
                prepared = self._features.peek(scope, expected, row['id'])
                triggers = terms(row['trigger_terms']) if prepared is None else prepared[1]
                hits = [term for term in triggers if len(term) >= 2 and term in query]
                if not hits:
                    continue
                expansion = terms(row['entities']) + terms(row['keywords']) if prepared is None else prepared[3]
                for term in expansion:
                    if term not in clues and len(clues) < 8:
                        clues[term] = {'term': term, 'memory_id': row['id'], 'content_version': row['content_version'],
                                       'evidence_version': row['evidence_version'], 'trigger_hits': hits}
        return list(clues.values())

    async def retrieve(self, scope, authorization, query):
        from .retrieval import CANDIDATES, WEIGHTS, THRESHOLD, SEMANTIC_FLOOR, rank
        if not isinstance(query, str) or not query.strip() or len(query) > 4096:
            raise ValueError('Invalid hybrid query')
        await self._require(scope, authorization, 'memory:read')
        state = await asyncio.to_thread(self._snapshot, scope)
        available = await asyncio.to_thread(self._clues, scope, state, query)
        clues, expanded_text = [], query
        for clue in available:
            candidate = expanded_text + ('、' if clues else '。关联线索：') + clue['term']
            if len(candidate) <= 4096:
                clues.append(clue)
                expanded_text = candidate
        original = await self._encode(query, query=True)
        expanded = await self._encode(expanded_text, query=True) if clues else original
        rows = await asyncio.to_thread(self._scan, scope, state, original, CANDIDATES, None, query, expanded)
        results = rank(rows)
        await self._require(scope, authorization, 'memory:read')
        await asyncio.to_thread(self._snapshot_check, scope, state)
        return {'snapshot': {'revision': state[0], 'content_epoch': state[1]}, 'query': query,
                'expansion': clues, 'weights': dict(WEIGHTS), 'threshold': THRESHOLD, 'semantic_floor': SEMANTIC_FLOOR,
                'candidates': rows, 'results': results}

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
