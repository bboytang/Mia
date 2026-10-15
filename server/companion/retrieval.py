"""Bounded, traceable S/L/A/E signals; memory metadata is data, never instructions."""

import json
import math
import re


WEIGHTS = {'semantic': 0.58, 'lexical': 0.28, 'association': 0.08, 'emotion': 0.06}
THRESHOLD = 0.20
SEMANTIC_FLOOR = 0.35
CANDIDATES = 12
RESULTS = 4


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


def signals(query, row, cosine, query_terms=None):
    entities, keywords, triggers = [terms(row[name]) for name in ('entities', 'keywords', 'trigger_terms')]
    hits = [term for term in dict.fromkeys(entities + keywords + triggers) if len(term) >= 2 and term in query]
    associations = [term for term in triggers if len(term) >= 2 and term in query]
    left = bigrams(query) if query_terms is None else query_terms
    right = bigrams(row['content'] + ''.join(entities + keywords))
    overlap = len(left & right) / max(1, len(left | right))
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
