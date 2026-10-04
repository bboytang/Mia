import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from server.opus_pcm import OpusEncoder
from server.account_store import AccountStore
from server.tests.test_accounts import PASSWORD
from server.bailian_provider import BailianProvider
from server.volcengine_provider import VolcengineProvider
from server.xiaozhi_gateway import MiaGateway, selected_provider


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
    def test_provider_selection_and_rollback(self):
        with patch.dict("os.environ", {"VOLC_ARK_API_KEY": "placeholder-ark",
                                    "VOLC_VOICE_API_KEY": "placeholder-voice"}):
            self.assertIs(selected_provider(), VolcengineProvider)
        with patch.dict("os.environ", {"MIA_PROVIDER": "bailian",
                                    "DASHSCOPE_API_KEY": "placeholder-old",
                                    "MIA_BAILIAN_REGION": "cn-beijing"}):
            self.assertIs(selected_provider(), BailianProvider)
        with patch.dict("os.environ", {"MIA_PROVIDER": "invalid"}):
            with self.assertRaises(ValueError):
                selected_provider()

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


class AccountGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = [1_800_000_000]
        self.accounts = AccountStore(Path(self.temp.name) / "accounts.sqlite3",
                                     daily_rounds=2, clock=lambda: self.now[0])
        self.credential = await self.accounts.register("voice_friend", PASSWORD)
        self.user = self.accounts.authenticate(self.credential["token"])
        self.provider = FakeProvider()
        try:
            self.gateway = MiaGateway("maintenance-token", lambda: self.provider,
                                      accounts=self.accounts, max_concurrent_rounds=1)
            self.server = await serve(self.gateway.handle_client, "127.0.0.1", 0)
        except BaseException:
            await self.accounts.close()
            self.temp.cleanup()
            raise
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()
        await self.accounts.close()
        self.temp.cleanup()

    def socket(self, token=None):
        return connect(self.url, additional_headers={
            "Authorization": "Bearer " + (token or self.credential["token"])})

    async def greet(self, socket):
        await socket.send(json.dumps({"type": "hello", "version": 1, "transport": "websocket"}))
        self.assertEqual(json.loads(await socket.recv())["type"], "hello")

    async def recording(self, socket, empty=False):
        await socket.send(json.dumps({"type": "listen", "state": "start"}))
        if not empty:
            encoder = OpusEncoder(16_000)
            try:
                await socket.send(encoder.encode(bytes(1_920)))
            finally:
                encoder.close()
        await socket.send(json.dumps({"type": "listen", "state": "stop"}))

    async def answer(self, socket):
        events, audio = [], []
        while True:
            message = await asyncio.wait_for(socket.recv(), 2)
            if isinstance(message, bytes):
                audio.append(message)
            else:
                event = json.loads(message)
                events.append(event)
                if event.get("state") == "stop" or event.get("type") == "error":
                    return events, audio

    def rounds(self):
        row = self.accounts.db.execute("SELECT sum(rounds) FROM usage WHERE user_id=?",
                                       (self.user,)).fetchone()
        return row[0] or 0

    async def test_account_voice_round_keeps_mia_only_subtitles_and_opus(self):
        async with self.socket() as socket:
            await self.greet(socket)
            await self.recording(socket)
            events, frames = await self.answer(socket)
            self.assertEqual([e["state"] for e in events], ["start", "sentence_start", "stop"])
            self.assertEqual(events[1]["text"], "你好，我是 Mia。")
            self.assertTrue(frames and all(isinstance(frame, bytes) and frame for frame in frames))
            self.assertFalse(any(e.get("type") == "stt" for e in events))
        self.assertEqual(self.rounds(), 1)

    async def test_revoked_and_expired_accounts_are_rejected_at_handshake(self):
        self.accounts.revoke(self.credential["token"])
        async with self.socket() as socket:
            with self.assertRaises(ConnectionClosed) as error:
                await socket.recv()
            self.assertEqual(error.exception.rcvd.code, 1008)
            self.assertEqual(error.exception.rcvd.reason, "未授权")
        latest = await self.accounts.login("voice_friend", PASSWORD)
        self.now[0] = latest["expires_at"]
        async with self.socket(latest["token"]) as socket:
            with self.assertRaises(ConnectionClosed) as error:
                await socket.recv()
            self.assertEqual(error.exception.rcvd.code, 1008)

    async def test_logout_rejects_new_round_on_already_connected_socket(self):
        async with self.socket() as socket:
            await self.greet(socket)
            self.accounts.revoke(self.credential["token"])
            await self.recording(socket)
            with self.assertRaises(ConnectionClosed) as error:
                await socket.recv()
            self.assertEqual(error.exception.rcvd.code, 1008)
        self.assertEqual(self.rounds(), 0)
        self.assertIsNone(self.provider.recording)

    async def test_expiry_is_checked_before_new_round_and_empty_costs_nothing(self):
        async with self.socket() as socket:
            await self.greet(socket)
            await self.recording(socket, empty=True)
            error = json.loads(await socket.recv())
            self.assertEqual(error["message"], "没有收到录音")
            self.assertEqual(self.rounds(), 0)
            self.now[0] = self.credential["expires_at"]
            await self.recording(socket)
            with self.assertRaises(ConnectionClosed) as closed:
                await socket.recv()
            self.assertEqual(closed.exception.rcvd.code, 1008)
        self.assertEqual(self.rounds(), 0)

    async def test_daily_limit_survives_another_connection(self):
        for _ in range(2):
            async with self.socket() as socket:
                await self.greet(socket)
                await self.recording(socket)
                events, _ = await self.answer(socket)
                self.assertEqual(events[-1]["state"], "stop")
        async with self.socket() as socket:
            await self.greet(socket)
            await self.recording(socket)
            error = json.loads(await socket.recv())
            self.assertEqual(error["type"], "error")
            self.assertIn("额度", error["message"])
        self.assertEqual(self.rounds(), 2)

    async def test_busy_round_never_debits_and_abort_releases_slot(self):
        first_provider, second_provider = SlowProvider(), SlowProvider()
        providers = iter([first_provider, second_provider])
        self.gateway.provider_factory = lambda: next(providers)
        async with self.socket("maintenance-token") as first, self.socket() as second:
            await self.greet(first)
            await self.greet(second)
            await self.recording(first)
            await asyncio.wait_for(first_provider.started.wait(), 2)
            await self.recording(second)
            error = json.loads(await second.recv())
            self.assertEqual(error["type"], "error")
            self.assertEqual(self.rounds(), 0)
            await first.send(json.dumps({"type": "abort"}))
            await asyncio.wait_for(first_provider.cancelled.wait(), 2)
            await self.recording(second)
            await asyncio.wait_for(second_provider.started.wait(), 2)
            self.assertEqual(self.rounds(), 1)
            await second.send(json.dumps({"type": "abort"}))
            await asyncio.wait_for(second_provider.cancelled.wait(), 2)
        self.assertEqual(self.gateway.active_rounds, 0)

    async def test_provider_error_counts_round_and_releases_slot(self):
        class FailingProvider(FakeProvider):
            async def transcribe(self, recording):
                raise RuntimeError("fake upstream unavailable")

        self.gateway.provider_factory = FailingProvider
        async with self.socket() as socket:
            await self.greet(socket)
            for expected_rounds in [1, 2]:
                await self.recording(socket)
                events, _ = await self.answer(socket)
                self.assertEqual(events[-1]["message"], "云语音服务暂时不可用")
                self.assertEqual(self.rounds(), expected_rounds)
        self.assertEqual(self.gateway.active_rounds, 0)


if __name__ == "__main__":
    unittest.main()
