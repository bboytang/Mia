"""Exact feature equivalence and cache bounds; no embedding/performance claim."""

from dataclasses import dataclass, replace
import json
import random
import unittest
from unittest.mock import patch

from server.companion.embedding import EmbeddingUnavailable
from server.companion.retrieval import FeatureCache, bigrams, prepare_signals, signals, terms


@dataclass(frozen=True)
class Scope:
    owner: str = 'user:1:agent:a'
    persona_id: str = 'mia'


def reference(query, row, cosine):
    # Original uncompressed set algebra, independent of the packed cache path.
    entities, keywords, triggers = [terms(row[name]) for name in ('entities', 'keywords', 'trigger_terms')]
    hits = [term for term in dict.fromkeys(entities + keywords + triggers) if len(term) >= 2 and term in query]
    associations = [term for term in triggers if len(term) >= 2 and term in query]
    left, right = bigrams(query), bigrams(row['content'] + ''.join(entities + keywords))
    overlap = len(left & right) / max(1, len(left | right))
    return {'semantic': max(0.0, min(1.0, cosine)),
            'lexical': min(1.0, overlap * 2.2 + min(0.7, len(hits) * 0.14)),
            'association': min(1.0, len(associations) * 0.35),
            'emotion': row['emotional_weight'] or 0.0}, hits, associations


class RetrievalFeatureTests(unittest.TestCase):
    def row(self, marker='one'):
        return {'id': marker, 'content': '散步时带蓝色水壶。', 'entities': '["蓝色水壶"]',
                'category': 'fact', 'content_version': 1, 'evidence_version': 1,
                'keywords': '["散步","蓝色水壶"]', 'trigger_terms': '["散步"]', 'emotional_weight': 0.7}

    def test_packed_scores_match_original_sets_for_unicode_whitespace_and_order(self):
        rng = random.Random(23)
        alphabet = '薄荷Aİé🙂𠮷\ud800\u0000\t\n 一二.!'
        cases = [('', ''), ('一', '一'), ('🙂𠮷薄荷', '𠮷薄荷'), ('a A\nB', 'A B')]
        cases += [(''.join(rng.choices(alphabet, k=90)), ''.join(rng.choices(alphabet, k=20))) for _ in range(120)]
        for content, query in cases:
            row = self.row()
            row.update(content=content, entities=json.dumps([content[:5], query[:4], content[:5]]) if content and query else None,
                       keywords=json.dumps([query[-3:]]) if query else '[]',
                       trigger_terms=json.dumps([query[:2], query[-2:]]) if query else None)
            for cosine in (-0.5, 0.0, 0.5, 1.5):
                expected = reference(query, row, cosine)
                self.assertEqual(signals(query, row, cosine), expected)
                self.assertEqual(signals(query, row, cosine, prepared=prepare_signals(row)), expected)

    def test_scope_epoch_isolation_eviction_and_oversize_entries(self):
        cache, current = FeatureCache(), Scope()
        old = cache.prepare(current, (0, 1), self.row())
        foreign = replace(current, owner='user:2:agent:a')
        cache.prepare(foreign, (0, 1), self.row())
        self.assertIsNone(cache.peek(replace(current, persona_id='other'), (0, 1), 'one'))
        cache.begin(current, (0, 2))
        self.assertIsNone(cache.peek(current, (0, 1), 'one'))
        self.assertEqual(cache.snapshot(current, (0, 1)), {})
        self.assertEqual(cache.snapshot(foreign, (0, 1))['one'][1], self.row())
        self.assertIsNotNone(cache.peek(foreign, (0, 1), 'one'))
        changed = dict(self.row(), keywords='["新线索"]')
        self.assertNotEqual(cache.prepare(current, (0, 2), changed), old)
        with patch('server.companion.retrieval.FEATURE_CACHE_ENTRIES', 2):
            for marker in ('two', 'three', 'four'):
                cache.prepare(current, (0, 2), self.row(marker))
                self.assertLessEqual(len(cache.entries), 2)
        with patch('server.companion.retrieval.FEATURE_CACHE_BYTES', 1):
            before = cache.bytes
            cache.prepare(current, (0, 2), self.row('oversize'))
            self.assertIsNone(cache.peek(current, (0, 2), 'oversize'))
            self.assertEqual(cache.bytes, before)
        # Byte-budget eviction is independent of the entry-count limit.
        budget = cache.bytes
        with patch('server.companion.retrieval.FEATURE_CACHE_BYTES', budget):
            for i in range(20):
                cache.prepare(current, (0, 2), self.row(str(i)))
                self.assertLessEqual(cache.bytes, budget)

    def test_invalid_metadata_is_never_cached_or_silently_reused(self):
        cache, current = FeatureCache(), Scope()
        cache.prepare(current, (0, 1), self.row())
        cache.begin(current, (0, 2))
        with self.assertRaises(EmbeddingUnavailable):
            cache.prepare(current, (0, 2), dict(self.row(), keywords='not-json'))
        self.assertIsNone(cache.peek(current, (0, 2), 'one'))
