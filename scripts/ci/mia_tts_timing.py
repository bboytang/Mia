"""Observe original TTS text preparation, without generating or faking audio."""

import asyncio
import hashlib
import inspect
from pathlib import Path
from queue import Queue
import threading
import time
from types import SimpleNamespace


TIMING_REVISION = 'P23-speech-ready-v2'


class RecordingQueue(Queue):
    def __init__(self, sample, lock):
        super().__init__()
        self.sample, self.lock, self.recording = sample, lock, True
        sample['queued_frames'] = []

    def put(self, item, block=True, timeout=None):
        with self.lock:
            if self.recording:
                elapsed = (time.perf_counter() - self.sample['started']) * 1000
                self.sample['queued_frames'].append({'at_ms': elapsed,
                    'sentence_type': item.sentence_type.name, 'content_type': item.content_type.name,
                    'text': item.content_detail})
                if item.content_type.name == 'TEXT' and item.content_detail and 'first_checked_text_ms' not in self.sample:
                    self.sample.update(first_checked_text_ms=elapsed, first_checked_text=item.content_detail)
        return super().put(item, block=block, timeout=timeout)


def make_probe(conn, sample, lock, config):
    from core.providers.tts.base import TTSProviderBase
    from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
    from core.utils.tts import MarkdownCleaner

    class Probe(TTSProviderBase):
        def __init__(self):
            super().__init__(config, delete_audio_file=True)
            self.conn = conn
            self.raw_queue = self.tts_text_queue = RecordingQueue(sample, lock)
            self.segment_seen, self.ready, self.drained = (threading.Event() for _ in range(3))
            self.closed = False
            sample['segment_checks'], sample['speech_ready_segments'] = [], []
            self.thread = threading.Thread(target=self.tts_text_priority_thread, daemon=True, name='p23-original-tts-text')
            self.thread.start()

        def _get_segment_text(self):
            result = super()._get_segment_text()
            with lock:
                sample['segment_checks'].append({'at_ms': (time.perf_counter() - sample['started']) * 1000,
                    'text': result})
            self.segment_seen.set()
            return result

        def _process_remaining_text_stream(self, opus_handler=None):
            try:
                return super()._process_remaining_text_stream(opus_handler)
            finally:
                self.drained.set()

        def to_tts_stream(self, text, opus_handler=None):
            # Same preprocessing at the original waveform-provider boundary.
            # No waveform provider is called; timings concern text readiness.
            cleaned = MarkdownCleaner.clean_markdown(text)
            if self._correct_words_pattern:
                cleaned = self._correct_words_pattern.sub(lambda match: self.correct_words[match.group(0)], cleaned)
            with lock:
                elapsed = (time.perf_counter() - sample['started']) * 1000
                sample['speech_ready_segments'].append({'at_ms': elapsed, 'segment': text, 'tts_text': cleaned})
                if cleaned.strip() and 'first_sentence_ms' not in sample:
                    sample.update(first_sentence_ms=elapsed, first_sentence=cleaned)
                    self.ready.set()

        async def text_to_speak(self, text, output_file):
            raise AssertionError('P23 text readiness observer must not invoke waveform synthesis')

        async def close(self):
            if self.closed:
                return
            self.closed = True
            self.raw_queue.recording = False
            conn.stop_event.set()
            # Wake the original blocking get with a valid action after recording.
            self.raw_queue.put(TTSMessageDTO(conn.sentence_id, SentenceType.FIRST, ContentType.ACTION))
            await asyncio.to_thread(self.thread.join, 2)
            assert not self.thread.is_alive(), 'Original TTS text observer did not stop'

    return Probe()


async def verify_original_text_stage(logger):
    from core.providers.tts.base import TTSProviderBase
    from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
    from core.utils import textUtils, tts

    sample = {'started': time.perf_counter()}
    conn = SimpleNamespace(sentence_id='p23-mechanical-tts', stop_event=threading.Event(), client_abort=False, logger=logger)
    probe = make_probe(conn, sample, threading.RLock(), {})
    queue = probe.tts_text_queue
    try:
        queue.put(TTSMessageDTO(conn.sentence_id, SentenceType.FIRST, ContentType.ACTION))
        queue.put(TTSMessageDTO(conn.sentence_id, SentenceType.MIDDLE, ContentType.TEXT, '🌿🌿🌿\n'))
        assert await asyncio.to_thread(probe.segment_seen.wait, 2)
        assert not probe.ready.is_set() and 'first_sentence_ms' not in sample
        queue.put(TTSMessageDTO(conn.sentence_id, SentenceType.MIDDLE, ContentType.TEXT, '中文测试，后半句。'))
        assert await asyncio.to_thread(probe.ready.wait, 2)
        assert sample['first_sentence'] == '中文测试'
        queue.put(TTSMessageDTO(conn.sentence_id, SentenceType.LAST, ContentType.ACTION))
        assert await asyncio.to_thread(probe.drained.wait, 2)
    finally:
        await probe.close()
    return {'emoji_frame_did_not_mark_speech_ready': True, 'original_segment_text': sample['first_sentence'],
        'source_sha256': {Path(inspect.getfile(value)).name: hashlib.sha256(Path(inspect.getfile(value)).read_bytes()).hexdigest()
            for value in (TTSProviderBase, textUtils, tts)},
        'probe': {key: value for key, value in sample.items() if key != 'started'},
        'scope': 'Controlled original TTS text processing only; no Provider or waveform call'}
