from enum import Enum
import importlib.util
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
import unittest

from server.companion.persona import GuardedTTSQueue, PersonaAgent, SAFE_REPLY

spec = importlib.util.spec_from_file_location('youmi_tts_boundaries', Path(__file__).resolve().parents[1] / 'youmi_tts_boundaries.py')
boundaries = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundaries)


class Sentence(Enum):
    FIRST = 'FIRST'
    MIDDLE = 'MIDDLE'
    LAST = 'LAST'


class Content(Enum):
    TEXT = 'TEXT'
    ACTION = 'ACTION'


def item(text=None, stage=Sentence.MIDDLE, sentence='one'):
    return SimpleNamespace(sentence_id=sentence, sentence_type=stage,
        content_type=Content.TEXT if text is not None else Content.ACTION, content_detail=text)


class BoundaryContractTests(unittest.TestCase):
    def test_all_lengths_punctuation_and_increment_shapes_keep_complete_checks(self):
        for case in boundaries.boundary_cases():
            with self.subTest(case=case['name']):
                conn, sink = SimpleNamespace(sentence_id='one'), Queue()
                persona = PersonaAgent()
                queue = GuardedTTSQueue(sink, conn, persona)
                checks = []
                original = persona.guardrail.inspect_output
                def check(text):
                    checks.append(text)
                    return original(text)
                persona.guardrail.inspect_output = check
                for index, chunk in enumerate(case['chunks']):
                    queue.put(item(chunk))
                    if case['boundary'] in ('comma', 'unsafe') and index < len(case['chunks']) - 1:
                        self.assertEqual(checks, [])
                if case['boundary'] == 'last':
                    self.assertEqual(checks, [])
                queue.put(item(stage=Sentence.LAST))
                values = []
                while not sink.empty():
                    message = sink.get_nowait()
                    if message.content_type is Content.TEXT:
                        values.append(message.content_detail)
                expected = [original(text)[0] for text in checks]
                self.assertEqual(values, expected)
                self.assertTrue(checks)

    def test_early_comma_release_is_not_equivalent_to_original_rejection_scope(self):
        guard = PersonaAgent().guardrail
        prefix, tail = '可以慢慢走，', '我是ChatGPT。'
        self.assertEqual(guard.inspect_output(prefix + tail), (SAFE_REPLY, True))
        self.assertEqual(guard.inspect_output(prefix), (prefix, False))
        self.assertEqual(guard.inspect_output(tail), (SAFE_REPLY, True))
        self.assertNotEqual(prefix + SAFE_REPLY, SAFE_REPLY)

    def test_superseded_sentence_cannot_flush_old_pending_text(self):
        conn, sink = SimpleNamespace(sentence_id='one'), Queue()
        queue = GuardedTTSQueue(sink, conn, PersonaAgent())
        queue.put(item('旧待发送'))
        conn.sentence_id = 'new'
        queue.put(item(stage=Sentence.LAST))
        queue.put(item('新轮次。', sentence='new'))
        self.assertEqual(sink.qsize(), 1)
        self.assertEqual(sink.get_nowait().content_detail, '新轮次。')
