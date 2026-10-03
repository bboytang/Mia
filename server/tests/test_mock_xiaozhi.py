import json
import os
import unittest
from unittest.mock import patch

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from server.mock_xiaozhi import ANSWER, handle_client


class MockXiaozhiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = await serve(handle_client, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_hello_listen_and_opus_reply(self):
        async with connect(self.url) as socket:
            await socket.send(json.dumps({"type": "hello", "version": 1,
                                          "transport": "websocket"}))
            hello = json.loads(await socket.recv())
            self.assertEqual(hello["session_id"], "mia-local-test")
            self.assertEqual(hello["audio_params"]["sample_rate"], 24_000)

            await socket.send(json.dumps({"type": "listen", "state": "start",
                                          "mode": "manual", "session_id": "mia-local-test"}))
            await socket.send(b"\x01\x02")
            await socket.send(json.dumps({"type": "listen", "state": "stop",
                                          "session_id": "mia-local-test"}))
            self.assertEqual(json.loads(await socket.recv())["state"], "start")
            sentence = json.loads(await socket.recv())
            self.assertEqual(sentence["text"], ANSWER)
            packets = [await socket.recv() for _ in range(20)]
            self.assertTrue(all(isinstance(packet, bytes) and packet for packet in packets))
            self.assertEqual(json.loads(await socket.recv())["state"], "stop")

    async def test_rejects_invalid_hello(self):
        async with connect(self.url) as socket:
            await socket.send(json.dumps({"type": "hello", "transport": "mqtt"}))
            with self.assertRaises(ConnectionClosed) as error:
                await socket.recv()
            self.assertEqual(error.exception.rcvd.code, 1008)

    async def test_requires_configured_token(self):
        with patch.dict(os.environ, {"MIA_MOCK_TOKEN": "test-secret"}):
            async with connect(self.url) as socket:
                with self.assertRaises(ConnectionClosed) as error:
                    await socket.recv()
                self.assertEqual(error.exception.rcvd.code, 1008)


if __name__ == "__main__":
    unittest.main()
