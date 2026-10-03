import base64
import io
import json
import unittest
import wave

import httpx

from server.bailian_provider import BailianProvider


class BailianProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_asr_chat_and_streamed_pcm_contract(self):
        requests = []

        def respond(request):
            requests.append(request)
            body = json.loads(request.content)
            if body["model"] == "qwen3-asr-flash":
                self.assertEqual(request.url.host, "dashscope.aliyuncs.com")
                audio = body["messages"][0]["content"][0]["input_audio"]["data"]
                self.assertTrue(audio.startswith("data:audio/wav;base64,"))
                with wave.open(io.BytesIO(base64.b64decode(audio.split(",", 1)[1]))) as wav:
                    self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getsampwidth()),
                                     (16_000, 1, 2))
                return httpx.Response(200, json={"choices": [{"message": {"content": "你好 Mia"}}]})
            if body["model"] == "qwen-plus":
                self.assertEqual(body["messages"][1]["content"], "你好 Mia")
                return httpx.Response(200, json={"choices": [{"message": {"content": "你好，我在。"}}]})
            if body["model"] == "qwen3-tts-flash":
                self.assertEqual(request.url.path,
                                 "/api/v1/services/aigc/multimodal-generation/generation")
                self.assertEqual(body["input"]["voice"], "Cherry")
                self.assertEqual(request.headers["X-DashScope-SSE"], "enable")
                audio = base64.b64encode(b"\x01\x00\x02\x00").decode()
                return httpx.Response(200, text=(
                    f'data: {json.dumps({"output": {"audio": {"data": audio}}})}\n\n'
                    'data: {"output":{"audio":{"data":""},"finish_reason":"stop"}}\n\n'))
            return httpx.Response(404)

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        provider = BailianProvider(api_key="test-key", region="cn-beijing", client=client)
        try:
            self.assertEqual(await provider.transcribe(bytes(1_920)), "你好 Mia")
            self.assertEqual(await provider.reply("你好 Mia"), "你好，我在。")
            self.assertEqual(b"".join([chunk async for chunk in provider.speech("你好，我在。")]),
                             b"\x01\x00\x02\x00")
            self.assertEqual(len(requests), 3)
            self.assertTrue(all(r.headers["Authorization"] == "Bearer test-key" for r in requests))
        finally:
            await client.aclose()

    async def test_region_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "MIA_BAILIAN_REGION"):
            BailianProvider(api_key="test-key", region="us-east-1")
