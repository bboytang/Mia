"""Batch math against the independent original-set oracle; synthetic vectors."""

import json
import random
import unittest

from server.companion.embedding import EmbeddingUnavailable
from server.companion.retrieval import WEIGHTS, batch_signals, bigrams, pair_codes, prepare_signals
from server.tests.test_companion_retrieval_features import reference


class BatchSignalTests(unittest.TestCase):
    def test_literal_words_without_nul_and_empty_middle_groups(self):
        rows = []
        for terms in (['散步', '蓝色水壶'], [], ['İ🙂', '\ud800薄荷'], [], ['散步']):
            rows.append(dict(content='散步蓝色水壶', entities=json.dumps(terms), keywords=None,
                trigger_terms=json.dumps(list(reversed(terms))), emotional_weight=None,
                original_cosine=0.4, expanded_cosine=0.5))
        query = '散步İ🙂\ud800薄荷'
        prepared = [prepare_signals(row) for row in rows]
        values, matched, starts = batch_signals(query, rows, prepared, pair_codes(bigrams(query)))
        for i, row in enumerate(rows):
            expected, hits, associations = reference(query, row, 0.5)
            self.assertEqual(dict(zip(WEIGHTS, values[i])), expected)
            self.assertEqual([term for j, term in enumerate(prepared[i][0]) if matched[starts[i] + j]], hits)
            self.assertEqual([term for j, term in enumerate(prepared[i][1])
                if matched[starts[i] + prepared[i][4][j]]], associations)

    def test_batches_match_original_scores_and_order_including_empty_groups(self):
        rng = random.Random(2306)
        alphabet = '薄荷Aİé🙂𠮷\ud800\x00\t\n 一二.!'
        for query in ('', '一', '散步蓝色水壶', 'Aİ🙂𠮷', '尾\x00', '\ud800薄荷'):
            rows = []
            for i in range(256):
                text = ''.join(rng.choices(alphabet, k=i % 90))
                words = [text[:5], query[:4], text[-3:]]
                words = [word for word in words if word]
                rows.append(dict(content=text, entities=json.dumps(words), keywords='[]',
                    trigger_terms=json.dumps(list(reversed(words))), emotional_weight=(None, 0, 0.7, 1)[i % 4],
                    original_cosine=(-0.5, 0, 0.5, 1.5)[i % 4], expanded_cosine=0.4))
            prepared = [prepare_signals(row) for row in rows]
            values, matched, starts = batch_signals(query, rows, prepared, pair_codes(bigrams(query)))
            for i, row in enumerate(rows):
                features = prepared[i]
                hits = [term for j, term in enumerate(features[0]) if matched[starts[i] + j]]
                associations = [term for j, term in enumerate(features[1]) if matched[starts[i] + features[4][j]]]
                actual = (dict(zip(WEIGHTS, values[i])), hits, associations)
                self.assertEqual(actual, reference(query, row, max(row['original_cosine'], row['expanded_cosine'])))
        self.assertEqual(batch_signals('', [], [], set())[0].shape, (0, 4))

    def test_invalid_emotion_in_any_row_is_rejected(self):
        for value in (float('nan'), float('inf'), -0.1, 1.1, '0.5'):
            row = dict(content='', entities=None, keywords=None, trigger_terms=None,
                emotional_weight=value, original_cosine=0, expanded_cosine=0)
            with self.assertRaisesRegex(EmbeddingUnavailable, 'metadata_invalid'):
                batch_signals('', [row], [prepare_signals(row)], set())
