import asyncio
import gzip
import json
import struct
import unittest
from unittest.mock import patch

import httpx
from websockets.asyncio.server import serve

from server.volcengine_provider import (
    VolcengineProvider,
    decode_asr_response,
    decode_tts_message,
    encode_asr_audio,
    encode_asr_full,
    encode_tts_event,
)


def asr_response(text, final=False):
    payload = gzip.compress(json.dumps({"result": {"text": text}}).encode())
    flags = 3 if final else 1
    return bytes((0x11, 0x90 | flags, 0x11, 0)) + struct.pack(
        ">iI", -2 if final else 2, len(payload)
    ) + payload


def tts_event(event, payload=b"", message_type=0xB, session_id=""):
    data = bytes((0x11, (message_type << 4) | 4, 0x10, 0))
    data += struct.pack(">i", event)
    if event in (50, 51, 52) or event >= 150:
        session = session_id.encode()
        data += struct.pack(">I", len(session)) + session
    return data + struct.pack(">I", len(payload)) + payload


class VolcengineProtocolTests(unittest.TestCase):
    def test_tts_event_encoding_and_audio_decoding(self):
        packet = encode_tts_event(200, {"req_params": {"text": "你好"}}, "session")
        self.assertEqual(packet[:8], bytes((0x11, 0x14, 0x10, 0, 0, 0, 0, 200)))
        sid_size = struct.unpack_from(">I", packet, 8)[0]
        self.assertEqual(packet[12:12 + sid_size], b"session")
        size = struct.unpack_from(">I", packet, 12 + sid_size)[0]
        self.assertEqual(json.loads(packet[16 + sid_size:16 + sid_size + size]),
                         {"req_params": {"text": "你好"}})
        self.assertEqual(decode_tts_message(tts_event(352, b"\x01\x02", session_id="session")),
                         (352, b"\x01\x02"))
        self.assertEqual(decode_tts_message(tts_event(50, b"{}", 0x9)), (50, {}))

    def test_tts_error_frame_is_explicit(self):
        packet = bytes((0x11, 0xF0, 0x10, 0)) + struct.pack(">iI", 45000001, 4) + b"oops"
        with self.assertRaisesRegex(RuntimeError, "45000001"):
            decode_tts_message(packet)

    def test_asr_full_request_is_gzipped_json_with_positive_sequence(self):
        packet = encode_asr_full(1, {"audio": {"rate": 16000}})
        self.assertEqual(packet[:4], bytes((0x11, 0x11, 0x11, 0)))
        self.assertEqual(struct.unpack(">i", packet[4:8])[0], 1)
        size = struct.unpack(">I", packet[8:12])[0]
        self.assertEqual(json.loads(gzip.decompress(packet[12:12 + size])),
                         {"audio": {"rate": 16000}})

    def test_asr_audio_packets_mark_only_last_sequence_negative(self):
        regular = encode_asr_audio(2, b"\x01\x02", final=False)
        final = encode_asr_audio(3, b"\x03\x04", final=True)
        self.assertEqual(regular[:4], bytes((0x11, 0x21, 0x01, 0)))
        self.assertEqual(final[:4], bytes((0x11, 0x23, 0x01, 0)))
        self.assertEqual(struct.unpack(">i", regular[4:8])[0], 2)
        self.assertEqual(struct.unpack(">i", final[4:8])[0], -3)
        for packet, expected in ((regular, b"\x01\x02"), (final, b"\x03\x04")):
            size = struct.unpack(">I", packet[8:12])[0]
            self.assertEqual(gzip.decompress(packet[12:12 + size]), expected)

    def test_asr_partial_final_and_server_error_decode(self):
        partial = decode_asr_response(asr_response("你好"))
        final = decode_asr_response(asr_response("你好 Mia", final=True))
        self.assertEqual((partial["text"], partial["final"]), ("你好", False))
        self.assertEqual((final["text"], final["final"]), ("你好 Mia", True))
        error_body = gzip.compress(b"{}")
        error = bytes((0x11, 0xF0, 0x11, 0)) + struct.pack(
            ">iI", 45000001, len(error_body)) + error_body
        with self.assertRaisesRegex(RuntimeError, "45000001"):
            decode_asr_response(error)


class VolcengineProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_tts_uses_verified_order_and_yields_pcm_chunks(self):
        events = []

        async def handler(socket):
            self.assertEqual(socket.request.headers["X-Api-Key"], "placeholder-voice")
            self.assertEqual(socket.request.headers["X-Api-Resource-Id"], "seed-tts-2.0")
            self.assertTrue(socket.request.headers["X-Api-Connect-Id"])
            for expected, response in ((1, 50), (100, 150)):
                packet = await socket.recv()
                event = struct.unpack_from(">i", packet, 4)[0]
                self.assertEqual(event, expected)
                events.append(event)
                await socket.send(tts_event(response, b"{}", 0x9))
            for expected in (200, 102):
                packet = await socket.recv()
                event = struct.unpack_from(">i", packet, 4)[0]
                self.assertEqual(event, expected)
                events.append(event)
                if event == 200:
                    self.assertIn(b"\xe4\xbd\xa0\xe5\xa5\xbd", packet)
            await socket.send(tts_event(352, b"\x01\x02"))
            await socket.send(tts_event(352, b"\x03\x04"))
            await socket.send(tts_event(152, b"{}", 0x9))
            packet = await socket.recv()
            events.append(struct.unpack_from(">i", packet, 4)[0])

        server = await serve(handler, "127.0.0.1", 0)
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            with patch("server.volcengine_provider.TTS_URL", url):
                chunks = [chunk async for chunk in provider.speech("你好")]
            self.assertEqual(chunks, [b"\x01\x02", b"\x03\x04"])
            self.assertEqual(events, [1, 100, 200, 102, 2])
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()

    async def test_tts_server_error_and_abnormal_close(self):
        async def handler(socket):
            await socket.recv()
            await socket.send(bytes((0x11, 0xF0, 0x10, 0)) +
                              struct.pack(">iI", 45000001, 0))

        server = await serve(handler, "127.0.0.1", 0)
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            with patch("server.volcengine_provider.TTS_URL", url):
                with self.assertRaisesRegex(RuntimeError, "45000001"):
                    _ = [part async for part in provider.speech("你好")]
        finally:
            server.close()
            await server.wait_closed()

        async def close_handler(socket):
            await socket.recv()
            await socket.close(code=1011)

        server = await serve(close_handler, "127.0.0.1", 0)
        try:
            url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            with patch("server.volcengine_provider.TTS_URL", url):
                with self.assertRaisesRegex(RuntimeError, "连接提前关闭"):
                    _ = [part async for part in provider.speech("你好")]
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()

    async def test_tts_cancel_closes_upstream_socket(self):
        started = asyncio.Event()
        closed = asyncio.Event()

        async def handler(socket):
            try:
                await socket.recv()
                started.set()
                await socket.wait_closed()
            finally:
                closed.set()

        server = await serve(handler, "127.0.0.1", 0)
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            with patch("server.volcengine_provider.TTS_URL", url):
                task = asyncio.create_task(anext(provider.speech("你好")))
                await asyncio.wait_for(started.wait(), 1)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                await asyncio.wait_for(closed.wait(), 1)
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()

    async def test_tts_timeout(self):
        async def handler(socket):
            await socket.recv()
            await asyncio.sleep(0.1)

        server = await serve(handler, "127.0.0.1", 0)
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            with patch("server.volcengine_provider.TTS_URL", url), patch(
                    "server.volcengine_provider.TTS_TIMEOUT", 0.02):
                with self.assertRaises(TimeoutError):
                    _ = [part async for part in provider.speech("你好")]
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()

    async def test_llm_endpoint_headers_model_thinking_and_response(self):
        def respond(request):
            self.assertEqual(str(request.url),
                             "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer placeholder-ark")
            self.assertEqual(request.headers["Content-Type"], "application/json")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "doubao-seed-2-1-lite-260915")
            self.assertEqual(body["thinking"], {"type": "disabled"})
            self.assertEqual(body["messages"][1]["content"], "你好")
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice", client)
        try:
            self.assertEqual(await provider.reply("你好"), "OK")
        finally:
            await provider.close()
            await client.aclose()

    async def test_llm_http_error_is_not_swallowed(self):
        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"error": "rejected"})))
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice", client)
        try:
            with self.assertRaises(httpx.HTTPStatusError):
                await provider.reply("你好")
        finally:
            await provider.close()
            await client.aclose()

    async def test_asr_uses_verified_request_and_only_returns_final_text(self):
        async def handler(socket):
            self.assertEqual(socket.request.headers["X-Api-Key"], "placeholder-voice")
            self.assertEqual(socket.request.headers["X-Api-Resource-Id"],
                             "volc.seedasr.sauc.duration")
            self.assertTrue(socket.request.headers["X-Api-Request-Id"])
            first = await socket.recv()
            self.assertEqual(first[:4], bytes((0x11, 0x11, 0x11, 0)))
            body = json.loads(gzip.decompress(first[12:]))
            self.assertEqual(body["audio"], {"format": "pcm", "codec": "raw",
                                             "rate": 16000, "bits": 16, "channel": 1})
            self.assertEqual(body["request"]["model_name"], "bigmodel")
            self.assertTrue(body["request"]["enable_itn"])
            self.assertTrue(body["request"]["enable_punc"])
            regular = await socket.recv()
            final = await socket.recv()
            self.assertEqual(struct.unpack(">i", regular[4:8])[0], 2)
            self.assertEqual(struct.unpack(">i", final[4:8])[0], -3)
            await socket.send(asr_response("你好"))
            await socket.send(asr_response("你好 Mia", final=True))

        server = await serve(handler, "127.0.0.1", 0)
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            with patch("server.volcengine_provider.ASR_URL", url):
                self.assertEqual(await provider.transcribe(bytes(12_800)), "你好 Mia")
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()

    async def test_asr_abnormal_close_and_timeout_raise(self):
        async def close_handler(socket):
            await socket.recv()
            await socket.recv()
            await socket.close(code=1011)

        server = await serve(close_handler, "127.0.0.1", 0)
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        provider = VolcengineProvider("placeholder-ark", "placeholder-voice")
        try:
            with patch("server.volcengine_provider.ASR_URL", url):
                with self.assertRaisesRegex(RuntimeError, "连接提前关闭"):
                    await provider.transcribe(bytes(6400))
        finally:
            server.close()
            await server.wait_closed()

        async def wait_handler(socket):
            await socket.recv()
            await socket.recv()
            await asyncio.sleep(1)

        server = await serve(wait_handler, "127.0.0.1", 0)
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        try:
            with patch("server.volcengine_provider.ASR_URL", url), patch(
                    "server.volcengine_provider.ASR_TIMEOUT", 0.02):
                with self.assertRaises(TimeoutError):
                    await provider.transcribe(bytes(6400))
        finally:
            await provider.close()
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
