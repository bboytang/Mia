import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location('mia_extraction_diagnostics',
    Path(__file__).resolve().parents[1] / 'mia_extraction_diagnostics.py')
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


def chunk(name, arguments):
    call = SimpleNamespace(index=0, id='actual-id', type='function',
        function=SimpleNamespace(name=name, arguments=arguments))
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=None,
        delta=SimpleNamespace(content=None, tool_calls=[call]))])


class OriginalSDKCaptureTests(unittest.TestCase):
    def test_fragments_and_repeated_names_are_preserved_without_reconstruction(self):
        original = {'model': 'test', 'messages': [{'role': 'user', 'content': '原文'}], 'stream': True}
        capture = diagnostics.StreamCapture(1, original)
        first, second = chunk('mia_memory_proposal', '{"memories":'), chunk('mia_memory_proposal', '[]}')
        capture.append(first)
        capture.append(second)
        capture.finish()
        parts = capture.entry['parts']
        self.assertEqual([x['tool_calls'][0]['function']['name'] for x in parts],
            ['mia_memory_proposal', 'mia_memory_proposal'])
        self.assertEqual([x['tool_calls'][0]['function']['arguments'] for x in parts], ['{"memories":', '[]}'])
        expected = b''.join(json.dumps(x, ensure_ascii=False, sort_keys=True).encode() + b'\n' for x in parts)
        self.assertEqual(capture.entry['consumed_parts_sha256'], hashlib.sha256(expected).hexdigest())
        self.assertEqual(capture.entry['request'], original)
        self.assertEqual(first.choices[0].delta.tool_calls[0].function.arguments, '{"memories":')

    def test_overflow_stays_bounded_records_truncation_and_hashes_all_consumed_parts(self):
        capture = diagnostics.StreamCapture(1, {'messages': [{'content': 'x' * diagnostics.MAX_CAPTURE_BYTES}]})
        self.assertTrue(capture.entry['request_truncated'])
        self.assertIsNone(capture.entry['request'])
        capture.append(chunk('mia_memory_proposal', 'x' * diagnostics.MAX_CAPTURE_BYTES))
        capture.append(chunk(None, 'last'))
        capture.finish()
        self.assertTrue(capture.entry['capture_truncated'])
        self.assertEqual(capture.entry['parts'], [])
        self.assertEqual(capture.entry['parts_seen'], 2)
        self.assertLessEqual(capture.entry['captured_bytes'], diagnostics.MAX_CAPTURE_BYTES)
        self.assertEqual(len(capture.entry['consumed_parts_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
