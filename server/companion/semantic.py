"""Scope-first exact vectors and hybrid retrieval in the existing fact DB."""

import asyncio
from contextlib import closing
from functools import wraps
import heapq
from pathlib import Path
import sqlite3
import time

from .authorization import AuthenticatedScope, PrivateAuthorizationRequired
from .embedding import DIMENSION, MODEL_KEY, REVISION, EmbeddingUnavailable
from .memory import MemoryError


def _foreground_read(function):
    @wraps(function)
    async def read(self, *args, **kwargs):
        activity = self._activity
        activity['foreground'] += 1
        activity['idle'].clear()
        try:
            return await function(self, *args, **kwargs)
        finally:
            activity['foreground'] -= 1
            if activity['foreground'] == 0:
                activity['idle'].set()
    return read


class SemanticMemoryIndex:
    def __init__(self, store, encoder):
        if (encoder.model_id, encoder.revision, encoder.dimension) != (MODEL_KEY, REVISION, DIMENSION):
            raise EmbeddingUnavailable('embedding_model_mismatch')
        self.store, self.encoder = store, encoder
        self._slots = asyncio.Semaphore(2)
        from .retrieval import FeatureCache
        with store.lock:
            self._database_uri = Path(store.db.execute('PRAGMA database_list').fetchone()['file']).as_uri() + '?mode=ro'
            if not hasattr(store, '_youmi_retrieval_features'):
                store._youmi_retrieval_features = FeatureCache()
            self._features = store._youmi_retrieval_features
            if not hasattr(store, '_youmi_retrieval_activity'):
                store._youmi_retrieval_activity = {'foreground': 0, 'idle': asyncio.Event()}
                store._youmi_retrieval_activity['idle'].set()
            self._activity = store._youmi_retrieval_activity

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

    def _recall_snapshot(self, scope):
        with self.store.lock:
            row = self.store.db.execute('SELECT o.revision,s.content_epoch,COALESCE(f.memory_recall,1) '
                'FROM owners o JOIN mia_scope_versions s ON s.owner=o.owner '
                'LEFT JOIN mia_feature_settings f ON f.owner=o.owner WHERE o.owner=?', (scope.owner,)).fetchone()
            return (tuple(row[:2]), bool(row[2])) if row else ((0, 0), True)

    def _check(self, scope, expected, db=None):
        if self._state(scope, db) != expected:
            raise EmbeddingUnavailable('memory_changed')

    async def _encode(self, text, query=False):
        deadline = asyncio.get_running_loop().time() + 120
        while True:
            if not query:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise EmbeddingUnavailable('embedding_busy')
                try:
                    await self._background_ready(remaining)
                except asyncio.TimeoutError:
                    raise EmbeddingUnavailable('embedding_busy') from None
            try:
                await asyncio.wait_for(self._slots.acquire(), timeout=0.4)
            except asyncio.TimeoutError:
                raise EmbeddingUnavailable('embedding_busy') from None
            if query or self._activity['foreground'] == 0:
                break
            self._slots.release()
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

    async def _background_ready(self, timeout=120):
        deadline = asyncio.get_running_loop().time() + timeout
        while self._activity['foreground']:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            await asyncio.wait_for(self._activity['idle'].wait(), remaining)

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
        from .retrieval import FEATURE_CACHE_ENTRIES, WEIGHTS, batch_signals, bigrams, pair_codes, signals
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
            cached = {}
            if query_text is not None:
                self._features.begin(scope, expected)
                count = db.execute('SELECT COUNT(*) FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                    "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active'",
                    (scope.owner, scope.persona_id)).fetchone()[0]
                use_cache = count <= FEATURE_CACHE_ENTRIES
                if use_cache:
                    cached = self._features.snapshot(scope, expected)
                    if len(cached) != count:
                        cached = {}
            base = (' FROM memories m JOIN mia_memory_meta x ON x.memory_id=m.id '
                    'LEFT JOIN mia_vectors v ON v.memory_id=m.id AND v.model_id=? AND v.model_revision=? '
                    'AND v.dimension=? AND v.content_version=x.content_version '
                    "WHERE m.owner=? AND x.persona_id=? AND m.confirmed=1 AND x.state='active'")
            params = (MODEL_KEY, REVISION, DIMENSION, scope.owner, scope.persona_id)
            columns = ('m.id,x.content_version,x.evidence_version,v.normalized_vector' if cached else
                'm.id,m.content,m.category,x.content_version,x.evidence_version,'
                'x.entities,x.keywords,x.trigger_terms,x.emotional_weight,v.normalized_vector')
            cursor = db.execute('SELECT ' + columns + base, params)
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
                    if cached:
                        item = cached.get(row['id'])
                        if item is None:
                            raise EmbeddingUnavailable('memory_changed')
                        record = dict(item[1])
                        record['content_version'], record['evidence_version'] = row['content_version'], row['evidence_version']
                    else:
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
        def batches():
            # ID order only breaks score ties. Larger IDs first reduce heap
            # churn without changing any source's exact top-k.
            records.sort(key=lambda row: row['id'], reverse=True)
            for offset in range(0, len(records), 256):
                batch = records[offset:offset + 256]
                if not use_cache:
                    for row in batch:
                        yield row, None
                    continue
                prepared = ([cached[row['id']][0] for row in batch] if cached else
                            [self._features.prepare(scope, expected, row) for row in batch])
                values, matched, starts = batch_signals(query_text, batch, prepared, query_codes)
                # A source's global top-k must be in its batch top-k. Rows are
                # already ID-descending, so stable score ordering preserves ties.
                sources = (np.fromiter((row['original_cosine'] for row in batch), float, count=len(batch)),
                           np.fromiter((row['expanded_cosine'] for row in batch), float, count=len(batch)),
                           values[:, 1], values[:, 2])
                positions = set()
                for scores in sources:
                    positions.update(np.argsort(-scores, kind='stable')[:limit].tolist())
                for i in sorted(positions):
                    yield batch[i], (values[i], matched, int(starts[i]), prepared[i])

        for record, dynamic in batches():
            score, expanded_score = record['original_cosine'], record['expanded_cosine']
            if use_cache:
                calculated, matched, start, prepared = dynamic
                lexical, association = float(calculated[1]), float(calculated[2])
            else:
                calculated, hits, associations = signals(query_text, record, max(score, expanded_score), query_terms)
                lexical, association = calculated['lexical'], calculated['association']
            values = {'original': score, 'expanded': expanded_score,
                      'lexical': lexical, 'association': association}
            admitted = []
            for name, value in values.items():
                if name in ('lexical', 'association') and value <= 0:
                    continue
                heap = heaps[name]
                if len(heap) < limit or (value, record['id']) > heap[0][:2]:
                    admitted.append((heap, value))
            if not admitted:
                continue
            if use_cache:
                record['signals'] = {name: float(calculated[i]) for i, name in enumerate(WEIGHTS)}
                record['lexical_hits'] = [term for i, term in enumerate(prepared[0]) if matched[start + i]]
                record['association_hits'] = [term for i, term in enumerate(prepared[1]) if matched[start + prepared[4][i]]]
            else:
                record['signals'], record['lexical_hits'], record['association_hits'] = calculated, hits, associations
            for heap, value in admitted:
                entry = (value, record['id'], record)
                if len(heap) < limit:
                    heapq.heappush(heap, entry)
                else:
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
                if len(clues) == 8:
                    break
        return list(clues.values())

    @_foreground_read
    async def retrieve(self, scope, authorization, query):
        from .retrieval import CANDIDATES, WEIGHTS, THRESHOLD, SEMANTIC_FLOOR, rank
        if not isinstance(query, str) or not query.strip() or len(query) > 4096:
            raise ValueError('Invalid hybrid query')
        await self._require(scope, authorization, 'memory:read')
        state, recall = await asyncio.to_thread(self._recall_snapshot, scope)
        if not recall:
            await self._require(scope, authorization, 'memory:read')
            await asyncio.to_thread(self._snapshot_check, scope, state)
            return {'snapshot': {'revision': state[0], 'content_epoch': state[1]}, 'query': query,
                    'expansion': [], 'weights': dict(WEIGHTS), 'threshold': THRESHOLD,
                    'semantic_floor': SEMANTIC_FLOOR, 'candidates': [], 'results': []}
        available = await asyncio.to_thread(self._clues, scope, state, query)
        clues, expanded_text = [], query
        for clue in available:
            candidate = expanded_text + ('、' if clues else '。关联线索：') + clue['term']
            if len(candidate) <= 4096:
                clues.append(clue)
                expanded_text = candidate
        # Give other active foreground requests a chance to use the second slot;
        # an isolated request can still overlap its independent query encodes.
        if clues and self._activity['foreground'] == 1:
            vectors = await asyncio.gather(self._encode(query, query=True),
                self._encode(expanded_text, query=True), return_exceptions=True)
            # Both calls finish before propagating a failure; cancellation still
            # retains each running native slot through _encode's completion fence.
            for value in vectors:
                if isinstance(value, BaseException):
                    raise value
            original, expanded = vectors
        else:
            original = await self._encode(query, query=True)
            expanded = await self._encode(expanded_text, query=True) if clues else original
        rows = await asyncio.to_thread(self._scan, scope, state, original, CANDIDATES, None, query, expanded)
        results = rank(rows)
        await self._require(scope, authorization, 'memory:read')
        await asyncio.to_thread(self._snapshot_check, scope, state)
        return {'snapshot': {'revision': state[0], 'content_epoch': state[1]}, 'query': query,
                'expansion': clues, 'weights': dict(WEIGHTS), 'threshold': THRESHOLD, 'semantic_floor': SEMANTIC_FLOOR,
                'candidates': rows, 'results': results}

    @_foreground_read
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
