"""Error taxonomy preserves rejection, source authority and safe retry feedback."""

import json
import gzip
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest

from server.companion.extraction import LLMMemoryExtractor, validate_output
from server.companion.memory import MemoryError
from server.companion.model_requests import ModelQueueError, ModelRequestGate
from server.companion.proposal import ExtractionError, ProviderError, read_stream, validation_feedback


class ExtractionErrorTests(unittest.TestCase):
    def test_all_original_rejected_outputs_preserve_offline_verdicts_and_hashes(self):
        root = Path(__file__).resolve().parents[2] / 'docs/verification/mia-persona-memory'
        child = json.loads(gzip.decompress((root / 'performance-worker-fairness-complete-child.json.gz').read_bytes()))
        baseline = json.loads((root / 'performance-trailing-fence-offline.json').read_text())
        expected = {(x['job_id'], x['attempt']): x for x in baseline['cases']}
        for failure in child['validation_failures']:
            with self.subTest(job=failure['job_id'], attempt=failure['attempt']):
                original = failure['original_output']
                before = json.dumps(original, ensure_ascii=False).encode()
                self.assertEqual(hashlib.sha256(before).hexdigest(), failure['original_output_sha256'])
                try:
                    validate_output(original, failure['sources'], [])
                    accepted = True
                except ExtractionError as error:
                    accepted = False
                    self.assertIn(error.category, {'parse', 'field_schema', 'source_semantic'})
                self.assertEqual(accepted, expected[(failure['job_id'], failure['attempt'])].get(
                    'source_validation_empty_context_passed', False))
                self.assertEqual(json.dumps(original, ensure_ascii=False).encode(), before)

    def proposal(self, **changes):
        record = {'category': 'fact', 'content': '我常用青瓷杯喝茶', 'source_quote': '我常用青瓷杯喝茶',
            'source_index': 0, 'kind': 'explicit', 'subject': 'user', 'value': 'durable', 'sensitive': False}
        return {'memories': [dict(record, **changes)]}

    def test_parse_schema_and_source_errors_are_distinct_and_never_repaired(self):
        cases = [('not JSON', 'parse'), (self.proposal(keywords='["喝茶"]'), 'field_schema'),
            (self.proposal(keywords=['喝茶'] * 9), 'field_schema'),
            (self.proposal(source_quote='我喜欢另一件物品'), 'source_semantic'),
            (self.proposal(keywords=['不存在的词']), 'source_semantic'),
            (self.proposal(category='unknown'), 'field_schema')]
        for value, category in cases:
            with self.subTest(category=category, value=value):
                before = json.dumps(value, ensure_ascii=False)
                with self.assertRaises(ExtractionError) as caught:
                    validate_output(value, ['我常用青瓷杯喝茶'], [])
                self.assertEqual(caught.exception.category, category)
                self.assertEqual(caught.exception.code, 'invalid_input')
                self.assertEqual(validation_feedback(caught.exception)['category'], category)
                self.assertEqual(json.dumps(value, ensure_ascii=False), before)
        self.assertEqual(validate_output('{"memories":[]}', ['我常用青瓷杯喝茶'], [])['memories'], [])

    def test_tool_contract_and_provider_errors_do_not_share_feedback_or_raw_bodies(self):
        call = SimpleNamespace(index=0, id='one', function=SimpleNamespace(name='other_tool', arguments='{}'))
        with self.assertRaises(ExtractionError) as caught:
            read_stream(iter([(None, [call])]))
        self.assertEqual(caught.exception.category, 'tool_contract')
        self.assertIn('mia_memory_proposal', validation_feedback(caught.exception)['message'])
        class Provider:
            def response_no_stream(self, *args):
                raise RuntimeError('sk-synthetic-credential private response body')
        with self.assertRaises(ProviderError) as failed:
            LLMMemoryExtractor(Provider)(['我常用青瓷杯喝茶'], [])
        self.assertNotIn('sk-', str(failed.exception))
        self.assertIsNone(validation_feedback(failed.exception))
        self.assertIsNone(validation_feedback(MemoryError('invalid_input', 'Unclassified foreign error')))

    def test_provider_initialization_and_cleanup_keep_safe_primary_diagnosis(self):
        def broken_factory():
            raise RuntimeError('private response body')
        with self.assertRaises(ProviderError):
            LLMMemoryExtractor(broken_factory)(['我常用青瓷杯喝茶'], [])

        class Client:
            def close(self):
                raise RuntimeError('private cleanup body')
        class Provider:
            client = Client()
            def response_no_stream(self, *args):
                raise ExtractionError('tool_contract', 'Invalid extraction proposal')
        with self.assertRaises(ExtractionError) as caught:
            LLMMemoryExtractor(Provider)(['我常用青瓷杯喝茶'], [])
        self.assertEqual(caught.exception.category, 'tool_contract')
        Provider.response_no_stream = lambda *args: '{"memories":[]}'
        with self.assertRaises(ProviderError):
            LLMMemoryExtractor(Provider)(['我常用青瓷杯喝茶'], [])

    def test_feedback_does_not_echo_credentials_or_alias_original_rejected_values(self):
        error = ExtractionError('source_semantic', 'sk-synthetic-credential')
        error.rejected_clues = {'entities': ['sk-synthetic-credential'], 'keywords': ['喝茶喝茶']}
        feedback = validation_feedback(error)
        self.assertNotIn('sk-', json.dumps(feedback))
        self.assertNotIn('entities', feedback['rejected_clues'])
        feedback['rejected_clues']['keywords'].clear()
        self.assertEqual(error.rejected_clues['keywords'], ['喝茶喝茶'])
        private = ExtractionError('source_semantic', 'Invalid user source', code='credentials_forbidden')
        self.assertIsNone(validation_feedback(private))

    def test_queue_timeout_and_cancel_are_distinct_without_releasing_native_slots(self):
        gate = ModelRequestGate()
        leases = [gate.acquire(foreground=True), gate.acquire(foreground=True)]
        try:
            with self.assertRaises(ModelQueueError) as caught:
                gate.acquire(foreground=False, timeout=.001)
            self.assertEqual(caught.exception.category, 'model_queue_timeout')
            self.assertEqual(gate.snapshot()['active'], 2)
            with self.assertRaises(ModelQueueError) as cancelled:
                gate.acquire(foreground=False, cancelled=lambda: True)
            self.assertEqual(cancelled.exception.category, 'cancelled')
            self.assertIsNone(validation_feedback(cancelled.exception))
        finally:
            for lease in leases:
                lease.release()
        self.assertEqual(gate.snapshot(), {'active': 0, 'waiting_foreground': 0, 'waiting_background': 0})
