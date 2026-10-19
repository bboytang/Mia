import importlib.util
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location('youmi_tts_timing',
    Path(__file__).resolve().parents[1] / 'youmi_tts_timing.py')
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class CheckedTextTimestampTests(unittest.TestCase):
    def test_nonzero_sdk_offset_uses_one_case_origin_and_legacy_is_explicit(self):
        sample = {'started': 100.0, 'timing_revision': timing.TIMING_REVISION}
        sample['sdk_start_ms'] = timing.case_elapsed_ms(sample, 100.25)
        sample['sdk_first_content_ms'] = timing.case_elapsed_ms(sample, 100.9)
        sample['first_sentence_ms'] = timing.case_elapsed_ms(sample, 101.1)
        stages = timing.stage_durations(sample)
        for key, value in zip(stages, (250, 650, 200)):
            self.assertAlmostEqual(stages[key], value)
        self.assertAlmostEqual(sum(stages.values()), sample['first_sentence_ms'])
        legacy = dict(sample, timing_revision='P23-speech-ready-v2', sdk_first_content_ms=650)
        for key, value in timing.stage_durations(legacy).items():
            self.assertAlmostEqual(value, stages[key])
        with self.assertRaises(ValueError):
            timing.stage_durations(dict(sample, timing_revision='unknown'))
        with self.assertRaises(ValueError):
            timing.stage_durations(dict(sample, sdk_first_content_ms=200))

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
