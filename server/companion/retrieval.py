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
    return (tuple(dict.fromkeys(entities + keywords + triggers)), tuple(triggers), right,
            tuple(dict.fromkeys(entities + keywords)))


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
        all_terms, triggers, right, _ = prepared
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


def rank(rows):
    accepted = []
    for row in rows:
        row['score'] = sum(WEIGHTS[key] * value for key, value in row['signals'].items())
        row['accepted'] = row['original_cosine'] >= SEMANTIC_FLOOR and row['score'] >= THRESHOLD
        if row['accepted']:
            accepted.append(row)
    return sorted(accepted, key=lambda row: (row['score'], row['id']), reverse=True)[:RESULTS]
