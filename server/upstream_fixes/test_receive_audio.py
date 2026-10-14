"""Exercise the actual chat entry point without audio hardware or model calls."""
import ast
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock


class ReceiveAudioTest(unittest.TestCase):
    def setUp(self):
        source = Path(os.environ['MIA_AUDIO_SOURCE']).read_text()
        function = next(node for node in ast.parse(source).body
                        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'startToChat')
        # Load the complete production function; substitute only its external collaborators.
        self.intent = AsyncMock(return_value=False)
        self.stt = AsyncMock()
        namespace = {'json': json, 'TAG': 'test', 'handle_user_intent': self.intent,
                     'send_stt_message': self.stt, 'handleAbortMessage': AsyncMock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<chat-entry>', 'exec'), namespace)
        self.start = namespace['startToChat']
        self.conn = SimpleNamespace(need_bind=False, max_output_size=0,
                                    client_is_speaking=False, client_listen_mode='auto',
                                    introduced_speakers=set(), logger=Mock(),
                                    executor=Mock(), chat=Mock())

    def assert_chat(self, source, expected):
        asyncio.run(self.start(self.conn, source))
        self.intent.assert_awaited_with(self.conn, expected)
        self.stt.assert_awaited_with(self.conn, expected)
        self.conn.executor.submit.assert_called_with(self.conn.chat, expected)

    def test_funasr_metadata_does_not_enter_chat_history(self):
        self.assert_chat(json.dumps({'content': '今天好吗？', 'language': 'zh', 'emotion': 'happy'}), '今天好吗？')

    def test_speaker_is_introduced_once_and_then_plain_content(self):
        text = json.dumps({'speaker': '测试主人', 'content': '你好'})
        self.assert_chat(text, text)
        self.assert_chat(text, '你好')
        self.assertEqual(self.conn.current_speaker, '测试主人')

    def test_plain_and_invalid_json_remain_usable(self):
        for text in ('你好', '{broken json}', '{"message":"hello"}'):
            with self.subTest(text=text):
                self.assert_chat(text, text)


if __name__ == '__main__':
    unittest.main()
