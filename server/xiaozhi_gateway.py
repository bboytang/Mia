"""Xiaozhi WebSocket v1 gateway backed by cloud ASR, chat, and speech."""

import argparse
import asyncio
import hmac
import json
import os
import uuid

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from server.openai_provider import OpenAIProvider
from server.opus_pcm import OpusDecoder, OpusEncoder

MAX_INPUT_BYTES = 16_000 * 2 * 30
OUTPUT_FRAME_BYTES = 24_000 * 2 * 60 // 1_000


class MiaGateway:
    def __init__(self, token: str, provider_factory=OpenAIProvider):
        if not token:
            raise ValueError("必须设置 MIA_GATEWAY_TOKEN")
        self.token = token
        self.provider_factory = provider_factory

    async def handle_client(self, socket):
        authorization = socket.request.headers.get("Authorization", "")
        if not hmac.compare_digest(authorization, f"Bearer {self.token}"):
            await socket.close(code=1008, reason="未授权")
            return

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
                            self._answer(socket, provider, recording))
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

    async def _answer(self, socket, provider, recording: bytes):
        if not recording:
            await socket.send(json.dumps({"type": "error", "message": "没有收到录音"}))
            return
        encoder = OpusEncoder(24_000)
        started = False
        try:
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
        except Exception:
            try:
                await socket.send(json.dumps({
                    "type": "error", "message": "云语音服务暂时不可用",
                }))
            except ConnectionClosed:
                pass
        finally:
            encoder.close()


async def main(host: str, port: int):
    token = os.environ.get("MIA_GATEWAY_TOKEN", "")
    gateway = MiaGateway(token)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("必须设置 OPENAI_API_KEY")
    async with serve(gateway.handle_client, host, port, max_size=65_536):
        print(f"Mia 语音网关已启动: ws://{host}:{port}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
