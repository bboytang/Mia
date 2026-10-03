import httpx
import unittest

from server.openai_provider import OpenAIProvider


class OpenAIProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_asr_chat_and_raw_pcm_contract(self):
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.path.endswith("/audio/transcriptions"):
                self.assertIn(b"RIFF", request.content)
                return httpx.Response(200, json={"text": "你好 Mia"})
            if request.url.path.endswith("/chat/completions"):
                self.assertIn(b"gpt-4o-mini", request.content)
                return httpx.Response(200, json={"choices": [
                    {"message": {"content": "你好，我在。"}}
                ]})
            if request.url.path.endswith("/audio/speech"):
                self.assertIn(b'"response_format":"pcm"', request.content)
                return httpx.Response(200, content=b"\x01\x00\x02\x00")
            return httpx.Response(404)

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        provider = OpenAIProvider(api_key="test-key", client=client)
        try:
            self.assertEqual(await provider.transcribe(bytes(1_920)), "你好 Mia")
            self.assertEqual(await provider.reply("你好 Mia"), "你好，我在。")
            self.assertEqual(b"".join([chunk async for chunk in provider.speech("你好，我在。")]),
                             b"\x01\x00\x02\x00")
            self.assertEqual(len(requests), 3)
            self.assertTrue(all(r.headers["Authorization"] == "Bearer test-key"
                                for r in requests))
        finally:
            await client.aclose()
