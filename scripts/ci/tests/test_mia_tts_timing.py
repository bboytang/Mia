import importlib.util
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location('mia_tts_timing',
    Path(__file__).resolve().parents[1] / 'mia_tts_timing.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class CheckedTextTimestampTests(unittest.TestCase):
    def test_emoji_text_queue_frame_does_not_claim_speech_ready(self):
        sample = {'started': time.perf_counter()}
        queue = timing.RecordingQueue(sample, threading.RLock())
        for text in ('🌿🌿🌿\n', '中文测试。'):
            queue.put(SimpleNamespace(sentence_type=SimpleNamespace(name='MIDDLE'),
                content_type=SimpleNamespace(name='TEXT'), content_detail=text))
        self.assertEqual(sample['first_checked_text'], '🌿🌿🌿\n')
        self.assertEqual([value['text'] for value in sample['queued_frames']], ['🌿🌿🌿\n', '中文测试。'])
        self.assertNotIn('first_sentence_ms', sample)
        self.assertLessEqual(sample['queued_frames'][0]['at_ms'], sample['queued_frames'][1]['at_ms'])
        queue.recording = False
        sample.pop('started')
        queue.put(SimpleNamespace(sentence_type=SimpleNamespace(name='FIRST'),
            content_type=SimpleNamespace(name='ACTION'), content_detail=None))
        self.assertEqual(len(sample['queued_frames']), 2)


if __name__ == '__main__':
    unittest.main()
