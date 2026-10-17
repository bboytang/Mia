"""Bounded, traceable S/L/A/E signals; memory metadata is data, never instructions."""

from array import array
from bisect import bisect_left
from collections import OrderedDict
import json
import math
import re
import sys
import threading


WEIGHTS = {'semantic': 0.58, 'lexical': 0.28, 'association': 0.08, 'emotion': 0.06}
THRESHOLD = 0.20
SEMANTIC_FLOOR = 0.35
CANDIDATES = 12
RESULTS = 4
FEATURE_CACHE_BYTES = 128 * 1024 * 1024
FEATURE_CACHE_ENTRIES = 32768


def terms(value):
    if value is None:
        return []
    try:
        values = json.loads(value)
        if (not isinstance(values, list) or len(values) > 16
                or any(not isinstance(term, str) or not 1 <= len(term) <= 64 for term in values)):
            raise ValueError()
        return list(dict.fromkeys(values))
    except (ValueError, TypeError):
        from .embedding import EmbeddingUnavailable
        raise EmbeddingUnavailable('retrieval_metadata_invalid') from None


def bigrams(text):
    compact = re.sub(r'\s+', '', text.lower())
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def pair_codes(pairs):
    # Two Unicode code points fit in 42 bits; this is exact, not a hash.
    return {(ord(pair[0]) << 21) | ord(pair[1]) for pair in pairs}


def prepare_signals(row):
    entities, keywords, triggers = [terms(row[name]) for name in ('entities', 'keywords', 'trigger_terms')]
    right = array('Q', sorted(pair_codes(bigrams(row['content'] + ''.join(entities + keywords)))))
    all_terms = tuple(term for term in dict.fromkeys(entities + keywords + triggers) if len(term) >= 2)
    triggers = tuple(term for term in triggers if len(term) >= 2)
    positions = {term: i for i, term in enumerate(all_terms)}
    return (all_terms, triggers, right, tuple(dict.fromkeys(entities + keywords)),
            tuple(positions[term] for term in triggers))


class FeatureCache:
    """Store-owned, bounded static features; epochs forbid stale reuse."""
    def __init__(self):
        self.entries = OrderedDict()
        self.bytes = 0
        self.lock = threading.RLock()

    def begin(self, scope, state):
        # Called after checking the snapshot, including when another connection has
        # changed/deleted facts. No query, score, vector or reply is cached.
        with self.lock:
            for key in list(self.entries):
                if key[:2] == (scope.owner, scope.persona_id) and key[2] != state:
                    self.bytes -= self.entries.pop(key)[1]

    def peek(self, scope, state, memory_id):
        with self.lock:
            item = self.entries.get((scope.owner, scope.persona_id, state, memory_id))
            return item[0] if item is not None else None

    def prepare(self, scope, state, row):
        with self.lock:
            key = (scope.owner, scope.persona_id, state, row['id'])
            item = self.entries.pop(key, None)
            if item is not None:
                self.entries[key] = item
                return item[0]
            return self._prepare(key, row)

    def _prepare(self, key, row):
        prepared = prepare_signals(row)
        # Conservatively include key/node overhead and repeated references to
        # strings, as well as the packed array's allocated buffer.
        size = (512 + sum(sys.getsizeof(part) for part in key) + sys.getsizeof(prepared)
                + sum(sys.getsizeof(part) for part in prepared)
                + sum(sys.getsizeof(term) for i in (0, 1, 3) for term in prepared[i]))
        if size > FEATURE_CACHE_BYTES:
            return prepared
        while self.entries and (self.bytes + size > FEATURE_CACHE_BYTES
                                or len(self.entries) >= FEATURE_CACHE_ENTRIES):
            self.bytes -= self.entries.popitem(last=False)[1][1]
        self.entries[key] = (prepared, size)
        self.bytes += size
        return prepared


def signals(query, row, cosine, query_terms=None, *, prepared=None, query_codes=None):
    if prepared is None:
        # Oversized working sets keep the original no-cache set path rather
        # than continuously allocating and evicting packed features.
        entities, keywords, triggers = [terms(row[name]) for name in ('entities', 'keywords', 'trigger_terms')]
        all_terms = dict.fromkeys(entities + keywords + triggers)
        left = bigrams(query) if query_terms is None else query_terms
        right = bigrams(row['content'] + ''.join(entities + keywords))
        overlap = len(left & right) / max(1, len(left | right))
    else:
        all_terms, triggers, right = prepared[:3]
        left = pair_codes(bigrams(query) if query_terms is None else query_terms) if query_codes is None else query_codes
        shared = 0
        for value in left:
            position = bisect_left(right, value)
            shared += position < len(right) and right[position] == value
        overlap = shared / max(1, len(left) + len(right) - shared)
    hits = [term for term in all_terms if len(term) >= 2 and term in query]
    associations = [term for term in triggers if len(term) >= 2 and term in query]
    emotion = row['emotional_weight']
    if emotion is not None and (not isinstance(emotion, (float, int)) or not math.isfinite(emotion) or not 0 <= emotion <= 1):
        from .embedding import EmbeddingUnavailable
        raise EmbeddingUnavailable('retrieval_metadata_invalid')
    return {'semantic': max(0.0, min(1.0, cosine)),
            'lexical': min(1.0, overlap * 2.2 + min(0.7, len(hits) * 0.14)),
            'association': min(1.0, len(associations) * 0.35),
            'emotion': 0.0 if emotion is None else emotion}, hits, associations


def batch_signals(query, rows, prepared, query_codes):
    """Exact dynamic signals for at most one scan batch; no query-result cache."""
    import numpy as np

    def totals(matches, lengths):
        lengths = np.asarray(lengths, dtype=np.intp)
        offsets = np.cumsum(lengths) - lengths
        result = np.zeros(len(lengths), dtype=np.intp)
        nonempty = lengths > 0
        if len(matches):
            result[nonempty] = np.add.reduceat(matches, offsets[nonempty], dtype=np.intp)
        return result, offsets

    lengths = np.asarray([len(item[2]) for item in prepared], dtype=np.intp)
    flat = np.frombuffer(b''.join(item[2].tobytes() for item in prepared), dtype=np.uint64)
    codes = np.asarray(sorted(query_codes), dtype=np.uint64)
    if len(codes) and len(flat):
        positions = np.searchsorted(codes, flat)
        np.minimum(positions, len(codes) - 1, out=positions)
        shared, _ = totals(codes[positions] == flat, lengths)
    else:
        shared = np.zeros(len(rows), dtype=np.intp)
    overlap = shared / np.maximum(1, len(codes) + lengths - shared)

    words = [term for item in prepared for term in item[0]]
    # Python containment preserves all Unicode/NUL input directly and avoids
    # allocating fixed-width copies of the query and every candidate term.
    matched = np.fromiter((term in query for term in words), dtype=bool, count=len(words))
    hit_counts, offsets = totals(matched, [len(item[0]) for item in prepared])
    trigger_positions = [int(offsets[i]) + position for i, item in enumerate(prepared) for position in item[4]]
    trigger_matched = matched[np.asarray(trigger_positions, dtype=np.intp)]
    association_counts, _ = totals(trigger_matched, [len(item[1]) for item in prepared])
    emotions = []
    for row in rows:
        value = row['emotional_weight']
        if value is not None and (not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 1):
            from .embedding import EmbeddingUnavailable
            raise EmbeddingUnavailable('retrieval_metadata_invalid')
        emotions.append(0.0 if value is None else value)
    values = np.column_stack((
        np.clip([max(row['original_cosine'], row['expanded_cosine']) for row in rows], 0, 1),
        np.minimum(1, overlap * 2.2 + np.minimum(0.7, hit_counts * 0.14)),
        np.minimum(1, association_counts * 0.35), emotions))
    return values, matched, offsets


def rank(rows):
    accepted = []
    for row in rows:
        row['score'] = sum(WEIGHTS[key] * value for key, value in row['signals'].items())
        row['accepted'] = row['original_cosine'] >= SEMANTIC_FLOOR and row['score'] >= THRESHOLD
        if row['accepted']:
            accepted.append(row)
    return sorted(accepted, key=lambda row: (row['score'], row['id']), reverse=True)[:RESULTS]
