"""Local Xiaozhi v1 protocol fixture. It plays a tone, not synthesized speech."""

import argparse
import asyncio
import ctypes
import ctypes.util
import json
import math
import os

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

SAMPLE_RATE = 24_000
FRAME_SAMPLES = 1_440
ANSWER = "你好，我是 Mia。这里是语音联调测试。"


class OpusTone:
    def __init__(self):
        library = ctypes.util.find_library("opus")
        if not library:
            raise RuntimeError("系统未安装 libopus")
        self.lib = ctypes.CDLL(library)
        self.lib.opus_encoder_create.argtypes = [
            ctypes.c_int32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)
        ]
        self.lib.opus_encoder_create.restype = ctypes.c_void_p
        self.lib.opus_encode.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int,
            ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int32,
        ]
        self.lib.opus_encode.restype = ctypes.c_int32
        self.lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
        error = ctypes.c_int()
        self.encoder = self.lib.opus_encoder_create(SAMPLE_RATE, 1, 2048, ctypes.byref(error))
        if not self.encoder or error.value:
            raise RuntimeError(f"Opus 编码器初始化失败: {error.value}")
        self.position = 0

    def frame(self) -> bytes:
        pcm = (ctypes.c_int16 * FRAME_SAMPLES)(
            *(int(math.sin((self.position + index) * 2 * math.pi * 440 / SAMPLE_RATE) * 4_000)
              for index in range(FRAME_SAMPLES))
        )
        self.position += FRAME_SAMPLES
        encoded = (ctypes.c_ubyte * 4_000)()
        length = self.lib.opus_encode(self.encoder, pcm, FRAME_SAMPLES, encoded, len(encoded))
        if length <= 0:
            raise RuntimeError(f"Opus 编码失败: {length}")
        return bytes(encoded[:length])

    def close(self):
        if self.encoder:
            self.lib.opus_encoder_destroy(self.encoder)
            self.encoder = None


async def send_response(socket):
    encoder = OpusTone()
    try:
        await socket.send(json.dumps({"type": "tts", "state": "start"}))
        await socket.send(json.dumps({"type": "tts", "state": "sentence_start", "text": ANSWER}))
        for _ in range(20):
            await socket.send(encoder.frame())
            await asyncio.sleep(0.06)
        await socket.send(json.dumps({"type": "tts", "state": "stop"}))
    finally:
        encoder.close()


async def handle_client(socket):
    token = os.environ.get("MIA_MOCK_TOKEN")
    if token and socket.request.headers.get("Authorization") != f"Bearer {token}":
        await socket.close(code=1008, reason="未授权")
        return

    greeted = False
    listening = False
    try:
        async for message in socket:
            if isinstance(message, bytes):
                if not listening:
                    await socket.close(code=1008, reason="未开始聆听")
                    return
                continue
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await socket.close(code=1003, reason="无效 JSON")
                return
            if not isinstance(data, dict):
                await socket.close(code=1003, reason="无效消息")
                return
            if not greeted:
                if (data.get("type") != "hello" or data.get("version") != 1
                        or data.get("transport") != "websocket"):
                    await socket.close(code=1008, reason="握手无效")
                    return
                greeted = True
                await socket.send(json.dumps({
                    "type": "hello", "transport": "websocket", "session_id": "mia-local-test",
                    "audio_params": {"format": "opus", "sample_rate": SAMPLE_RATE,
                                     "channels": 1, "frame_duration": 60},
                }))
            elif data.get("type") == "listen" and data.get("state") == "start":
                listening = True
            elif data.get("type") == "listen" and data.get("state") == "stop":
                if listening:
                    listening = False
                    await send_response(socket)
            elif data.get("type") == "abort":
                listening = False
    except ConnectionClosed:
        pass


async def main(host: str, port: int):
    async with serve(handle_client, host, port, max_size=65_536):
        print(f"Mia 测试服务已启动: ws://{host}:{port}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
