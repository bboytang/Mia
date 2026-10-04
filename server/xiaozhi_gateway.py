"""Xiaozhi WebSocket v1 gateway backed by cloud ASR, chat, and speech."""

import argparse
import asyncio
import hmac
import json
import os
import uuid

from aiohttp import web
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from server.bailian_provider import BailianProvider
from server.account_http import create_app
from server.account_store import AccountError, AccountStore
from server.opus_pcm import OpusDecoder, OpusEncoder
from server.volcengine_provider import VolcengineProvider

MAX_INPUT_BYTES = 16_000 * 2 * 30
OUTPUT_FRAME_BYTES = 24_000 * 2 * 60 // 1_000


def selected_provider():
    provider = os.environ.get("MIA_PROVIDER", "volcengine")
    if provider == "volcengine":
        if not os.environ.get("VOLC_ARK_API_KEY") or not os.environ.get("VOLC_VOICE_API_KEY"):
            raise ValueError("必须设置 VOLC_ARK_API_KEY 和 VOLC_VOICE_API_KEY")
        return VolcengineProvider
    if provider == "bailian":
        if not os.environ.get("DASHSCOPE_API_KEY"):
            raise ValueError("必须设置 DASHSCOPE_API_KEY")
        if os.environ.get("MIA_BAILIAN_REGION") not in {"cn-beijing", "ap-southeast-1"}:
            raise ValueError("必须设置 MIA_BAILIAN_REGION 为 cn-beijing 或 ap-southeast-1")
        return BailianProvider
    raise ValueError("MIA_PROVIDER 必须是 volcengine 或 bailian")


class MiaGateway:
    def __init__(self, token: str, provider_factory=VolcengineProvider,
                 accounts=None, max_concurrent_rounds=2):
        if not token:
            raise ValueError("必须设置 MIA_GATEWAY_TOKEN")
        self.token = token
        self.provider_factory = provider_factory
        if max_concurrent_rounds < 1:
            raise ValueError("同时语音轮数必须大于零")
        self.accounts = accounts
        self.max_concurrent_rounds = max_concurrent_rounds
        self.active_rounds = 0

    def _principal(self, token):
        if hmac.compare_digest(token.encode("utf-8"), self.token.encode("utf-8")):
            return 0  # Explicit legacy maintenance access; still shares the global limit.
        return self.accounts.authenticate(token) if self.accounts else None

    async def handle_client(self, socket):
        authorization = socket.request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer ") or self._principal(authorization[7:]) is None:
            await socket.close(code=1008, reason="未授权")
            return
        access_token = authorization[7:]

        provider = self.provider_factory()
        decoder = OpusDecoder(16_000)
        pcm = bytearray()
        session_id = uuid.uuid4().hex
        greeted = False
        listening = False
        answer_task = None
        try:
            async for message in socket:
                if isinstance(message, bytes):
                    if not listening:
                        await socket.close(code=1008, reason="未开始聆听")
                        break
                    try:
                        pcm.extend(decoder.decode(message))
                    except (ValueError, RuntimeError):
                        await socket.close(code=1003, reason="无效 Opus")
                        break
                    if len(pcm) > MAX_INPUT_BYTES:
                        await socket.close(code=1009, reason="录音超过 30 秒")
                        break
                    continue

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    await socket.close(code=1003, reason="无效 JSON")
                    break
                if not isinstance(data, dict):
                    await socket.close(code=1003, reason="无效消息")
                    break

                if not greeted:
                    if (data.get("type") != "hello" or data.get("version") != 1
                            or data.get("transport") != "websocket"):
                        await socket.close(code=1008, reason="握手无效")
                        break
                    greeted = True
                    await socket.send(json.dumps({
                        "type": "hello", "transport": "websocket",
                        "session_id": session_id,
                        "audio_params": {"format": "opus", "sample_rate": 24_000,
                                         "channels": 1, "frame_duration": 60},
                    }))
                elif data.get("type") == "abort":
                    if answer_task:
                        answer_task.cancel()
                        try:
                            await answer_task
                        except asyncio.CancelledError:
                            pass
                        answer_task = None
                    listening = False
                    pcm.clear()
                elif data.get("type") == "listen" and data.get("state") == "start":
                    if answer_task:
                        answer_task.cancel()
                        try:
                            await answer_task
                        except asyncio.CancelledError:
                            pass
                        answer_task = None
                    pcm.clear()
                    listening = True
                elif data.get("type") == "listen" and data.get("state") == "stop":
                    if listening:
                        listening = False
                        recording = bytes(pcm)
                        pcm.clear()
                        answer_task = asyncio.create_task(
                            self._answer(socket, provider, recording, access_token))
        except ConnectionClosed:
            pass
        finally:
            if answer_task:
                answer_task.cancel()
                try:
                    await answer_task
                except asyncio.CancelledError:
                    pass
            decoder.close()
            await provider.close()

    async def _answer(self, socket, provider, recording: bytes, access_token: str):
        if not recording:
            await socket.send(json.dumps({"type": "error", "message": "没有收到录音"}))
            return
        principal = self._principal(access_token)
        if principal is None:
            await socket.close(code=1008, reason="未授权")
            return
        if self.active_rounds >= self.max_concurrent_rounds:
            await socket.send(json.dumps({"type": "error", "message": "Mia 正忙，请稍后再试"}))
            return
        self.active_rounds += 1
        encoder = None
        started = False
        try:
            if principal != 0:
                self.accounts.consume_round(principal)
            encoder = OpusEncoder(24_000)
            user_text = await provider.transcribe(recording)
            if not user_text:
                await socket.send(json.dumps({"type": "error", "message": "没有听清，请再说一次"}))
                return
            mia_text = (await provider.reply(user_text))[:400]
            if not mia_text:
                await socket.send(json.dumps({"type": "error", "message": "Mia 暂时没有回答"}))
                return
            await socket.send(json.dumps({"type": "tts", "state": "start"}))
            started = True
            await socket.send(json.dumps({
                "type": "tts", "state": "sentence_start", "text": mia_text,
            }, ensure_ascii=False))
            pending = bytearray()
            async for chunk in provider.speech(mia_text):
                pending.extend(chunk)
                while len(pending) >= OUTPUT_FRAME_BYTES:
                    frame = bytes(pending[:OUTPUT_FRAME_BYTES])
                    del pending[:OUTPUT_FRAME_BYTES]
                    await socket.send(encoder.encode(frame))
            if pending:
                frame = bytes(pending).ljust(OUTPUT_FRAME_BYTES, b"\0")
                await socket.send(encoder.encode(frame))
            await socket.send(json.dumps({"type": "tts", "state": "stop"}))
        except asyncio.CancelledError:
            if started:
                try:
                    await socket.send(json.dumps({"type": "tts", "state": "stop"}))
                except ConnectionClosed:
                    pass
            raise
        except AccountError as error:
            try:
                await socket.send(json.dumps({"type": "error", "message": str(error)},
                                             ensure_ascii=False))
            except ConnectionClosed:
                pass
        except Exception:
            try:
                await socket.send(json.dumps({
                    "type": "error", "message": "云语音服务暂时不可用",
                }))
            except ConnectionClosed:
                pass
        finally:
            if encoder:
                encoder.close()
            self.active_rounds -= 1


async def main(host: str, port: int):
    token = os.environ.get("MIA_GATEWAY_TOKEN", "")
    provider = selected_provider()
    enabled = os.environ.get("MIA_ACCOUNTS_ENABLED", "0")
    if enabled not in {"0", "1"}:
        raise ValueError("MIA_ACCOUNTS_ENABLED 必须是 0 或 1")
    accounts = None
    runner = None
    try:
        if enabled == "1":
            accounts = AccountStore(os.environ.get("MIA_ACCOUNT_DB", "/var/lib/mia/accounts.sqlite3"),
                                    max_users=int(os.environ.get("MIA_MAX_ACCOUNTS", "100")),
                                    daily_rounds=int(os.environ.get("MIA_DAILY_ROUNDS", "30")))
        gateway = MiaGateway(token, provider, accounts=accounts,
                             max_concurrent_rounds=int(os.environ.get("MIA_MAX_CONCURRENT_ROUNDS", "2")))
        if accounts:
            runner = web.AppRunner(create_app(accounts), access_log=None, handler_cancellation=True)
            await runner.setup()
            await web.TCPSite(runner, "127.0.0.1", 8766).start()
        async with serve(gateway.handle_client, host, port, max_size=65_536):
            print(f"Mia 语音网关已启动: ws://{host}:{port}", flush=True)
            await asyncio.Future()
    finally:
        if runner:
            await runner.cleanup()
        if accounts:
            await accounts.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
