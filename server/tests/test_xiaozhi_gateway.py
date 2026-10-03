import asyncio
import json
import unittest

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from server.opus_pcm import OpusEncoder
from server.xiaozhi_gateway import MiaGateway


class FakeProvider:
    def __init__(self):
        self.recording = None
        self.question = None
        self.answer = None
        self.closed = False
        self.closed_event = asyncio.Event()

    async def transcribe(self, recording):
        self.recording = recording
        return "你好"

    async def reply(self, question):
        self.question = question
        return "你好，我是 Mia。"

    async def speech(self, answer):
        self.answer = answer
        pcm = bytes(2_880 * 2)
        yield pcm[:17]
        yield pcm[17:]

    async def close(self):
        self.closed = True
        self.closed_event.set()


class SlowProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def transcribe(self, recording):
        self.started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


class MiaGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.provider = FakeProvider()
        self.gateway = MiaGateway("test-token", lambda: self.provider)
        self.server = await serve(self.gateway.handle_client, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_recording_to_mia_only_subtitles_and_raw_opus(self):
        async with connect(self.url, additional_headers={
            "Authorization": "Bearer test-token"
        }) as socket:
            await socket.send(json.dumps({"type": "hello", "version": 1,
                                          "transport": "websocket"}))
            hello = json.loads(await socket.recv())
            self.assertEqual(hello["audio_params"]["sample_rate"], 24_000)
            await socket.send(json.dumps({"type": "listen", "state": "start"}))
            encoder = OpusEncoder(16_000)
            try:
                await socket.send(encoder.encode(bytes(1_920)))
            finally:
                encoder.close()
            await socket.send(json.dumps({"type": "listen", "state": "stop"}))
            self.assertEqual(json.loads(await socket.recv())["state"], "start")
            sentence = json.loads(await socket.recv())
            self.assertEqual(sentence["text"], "你好，我是 Mia。")
            frames = [await socket.recv(), await socket.recv()]
            self.assertTrue(all(isinstance(frame, bytes) and frame for frame in frames))
            self.assertEqual(json.loads(await socket.recv())["state"], "stop")
        self.assertEqual(len(self.provider.recording), 1_920)
        self.assertEqual(self.provider.question, "你好")
        self.assertEqual(self.provider.answer, "你好，我是 Mia。")
        await asyncio.wait_for(self.provider.closed_event.wait(), timeout=1)
        self.assertTrue(self.provider.closed)

    async def test_rejects_wrong_token(self):
        async with connect(self.url) as socket:
            with self.assertRaises(ConnectionClosed) as error:
                await socket.recv()
            self.assertEqual(error.exception.rcvd.code, 1008)

    async def test_empty_recording_returns_error_without_provider_call(self):
        async with connect(self.url, additional_headers={
            "Authorization": "Bearer test-token"
        }) as socket:
            await socket.send(json.dumps({"type": "hello", "version": 1,
                                          "transport": "websocket"}))
            await socket.recv()
            await socket.send(json.dumps({"type": "listen", "state": "start"}))
            await socket.send(json.dumps({"type": "listen", "state": "stop"}))
            error = json.loads(await socket.recv())
            self.assertEqual(error["type"], "error")
            self.assertIsNone(self.provider.recording)

    async def test_abort_cancels_pending_cloud_request(self):
        self.provider = SlowProvider()
        self.gateway.provider_factory = lambda: self.provider
        async with connect(self.url, additional_headers={
            "Authorization": "Bearer test-token"
        }) as socket:
            await socket.send(json.dumps({"type": "hello", "version": 1,
                                          "transport": "websocket"}))
            await socket.recv()
            await socket.send(json.dumps({"type": "listen", "state": "start"}))
            encoder = OpusEncoder(16_000)
            try:
                await socket.send(encoder.encode(bytes(1_920)))
            finally:
                encoder.close()
            await socket.send(json.dumps({"type": "listen", "state": "stop"}))
            await asyncio.wait_for(self.provider.started.wait(), timeout=1)
            await socket.send(json.dumps({"type": "abort"}))
            await asyncio.wait_for(self.provider.cancelled.wait(), timeout=1)


if __name__ == "__main__":
    unittest.main()
