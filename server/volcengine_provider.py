"""Volcengine ASR, Ark chat, and Seed TTS for the Mia gateway."""

import asyncio
import gzip
import json
import os
import struct
import uuid

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


ASR_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"
CHAT_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
TTS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
ASR_TIMEOUT = 20
ASR_CHUNK_BYTES = 16_000 * 2 * 200 // 1_000
TTS_TIMEOUT = 60


def encode_tts_event(event: int, payload: dict | None = None,
                     session_id: str | None = None) -> bytes:
    body = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")).encode()
    packet = bytes((0x11, 0x14, 0x10, 0)) + struct.pack(">i", event)
    if session_id is not None:
        identifier = session_id.encode()
        packet += struct.pack(">I", len(identifier)) + identifier
    return packet + struct.pack(">I", len(body)) + body


def decode_tts_message(data: bytes) -> tuple[int, bytes | dict]:
    if len(data) < 4 or data[0] != 0x11:
        raise RuntimeError("火山 TTS 响应头无效")
    message_type = data[1] >> 4
    if message_type == 0xF:
        if len(data) < 12:
            raise RuntimeError("火山 TTS 错误帧不完整")
        raise RuntimeError(f"火山 TTS 错误: {struct.unpack_from('>i', data, 4)[0]}")
    if not data[1] & 0x04 or len(data) < 8:
        raise RuntimeError("火山 TTS 事件帧无效")
    event = struct.unpack_from(">i", data, 4)[0]
    offset = 8
    if event in (50, 51, 52) or event >= 150:
        if len(data) < offset + 4:
            raise RuntimeError("火山 TTS 会话帧不完整")
        length = struct.unpack_from(">I", data, offset)[0]
        offset += 4 + length
    if len(data) < offset + 4:
        raise RuntimeError("火山 TTS 负载不完整")
    size = struct.unpack_from(">I", data, offset)[0]
    payload = data[offset + 4:offset + 4 + size]
    if len(payload) != size:
        raise RuntimeError("火山 TTS 负载不完整")
    return event, payload if message_type == 0xB else json.loads(payload or b"{}")


def encode_asr_full(sequence: int, payload: dict) -> bytes:
    body = gzip.compress(json.dumps(payload, ensure_ascii=False,
                                    separators=(",", ":")).encode())
    return bytes((0x11, 0x11, 0x11, 0)) + struct.pack(">iI", sequence, len(body)) + body


def encode_asr_audio(sequence: int, pcm: bytes, final: bool) -> bytes:
    body = gzip.compress(pcm)
    flags = 0x23 if final else 0x21
    return bytes((0x11, flags, 0x01, 0)) + struct.pack(
        ">iI", -sequence if final else sequence, len(body)) + body


def decode_asr_response(data: bytes) -> dict | None:
    if len(data) < 4 or data[0] >> 4 != 1:
        raise RuntimeError("火山 ASR 响应头无效")
    offset = (data[0] & 0x0F) * 4
    message_type = data[1] >> 4
    flags = data[1] & 0x0F
    if flags & 0x01:
        offset += 4
    if message_type == 0xF:
        if len(data) < offset + 8:
            raise RuntimeError("火山 ASR 错误帧不完整")
        code = struct.unpack_from(">i", data, offset)[0]
        raise RuntimeError(f"火山 ASR 错误: {code}")
    if message_type != 0x9:
        return None
    if len(data) < offset + 4:
        raise RuntimeError("火山 ASR 响应帧不完整")
    size = struct.unpack_from(">I", data, offset)[0]
    body = data[offset + 4:offset + 4 + size]
    if len(body) != size:
        raise RuntimeError("火山 ASR 负载不完整")
    if data[2] & 0x0F == 1:
        body = gzip.decompress(body)
    payload = json.loads(body) if data[2] >> 4 == 1 else {}
    return {"text": (payload.get("result") or {}).get("text") or "",
            "final": bool(flags & 0x02)}


class VolcengineProvider:
    def __init__(self, ark_api_key: str | None = None, voice_api_key: str | None = None,
                 client: httpx.AsyncClient | None = None):
        self.ark_api_key = ark_api_key or os.environ.get("VOLC_ARK_API_KEY")
        self.voice_api_key = voice_api_key or os.environ.get("VOLC_VOICE_API_KEY")
        if not self.ark_api_key or not self.voice_api_key:
            raise ValueError("必须设置 VOLC_ARK_API_KEY 和 VOLC_VOICE_API_KEY")
        self.client = client or httpx.AsyncClient(timeout=60)
        self.owns_client = client is None
        self.chat_model = os.environ.get("MIA_CHAT_MODEL", "doubao-seed-2-1-lite-260915")
        self.asr_resource_id = os.environ.get("MIA_ASR_RESOURCE_ID",
                                              "volc.seedasr.sauc.duration")
        self.tts_resource_id = os.environ.get("MIA_TTS_RESOURCE_ID", "seed-tts-2.0")

    async def transcribe(self, pcm: bytes) -> str:
        headers = {"X-Api-Key": self.voice_api_key,
                   "X-Api-Resource-Id": self.asr_resource_id,
                   "X-Api-Request-Id": str(uuid.uuid4())}
        request = {
            "user": {"uid": f"mia-{uuid.uuid4().hex}"},
            "audio": {"format": "pcm", "codec": "raw", "rate": 16_000,
                      "bits": 16, "channel": 1},
            "request": {"model_name": "bigmodel", "enable_itn": True,
                        "enable_punc": True, "enable_ddc": True,
                        "show_utterances": True, "enable_nonstream": True},
        }
        text = ""
        try:
            async with connect(ASR_URL, additional_headers=headers, open_timeout=15,
                               close_timeout=5, max_size=None) as socket:
                await socket.send(encode_asr_full(1, request))
                sequence = 2
                for offset in range(0, len(pcm), ASR_CHUNK_BYTES):
                    chunk = pcm[offset:offset + ASR_CHUNK_BYTES]
                    final = offset + ASR_CHUNK_BYTES >= len(pcm)
                    await socket.send(encode_asr_audio(sequence, chunk, final))
                    if not final:
                        sequence += 1
                        await asyncio.sleep(0.2)
                while True:
                    frame = decode_asr_response(await asyncio.wait_for(
                        socket.recv(), ASR_TIMEOUT))
                    if frame is None:
                        continue
                    if frame["text"]:
                        text = frame["text"]
                    if frame["final"]:
                        return text
        except ConnectionClosed as exc:
            raise RuntimeError("火山 ASR 连接提前关闭") from exc

    async def reply(self, user_text: str) -> str:
        response = await self.client.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {self.ark_api_key}"},
            json={"model": self.chat_model, "thinking": {"type": "disabled"},
                  "messages": [
                      {"role": "system", "content": "你是 Mia，亲切、简洁的中文语音伙伴。回答适合直接朗读，通常不超过两句话。"},
                      {"role": "user", "content": user_text},
                  ], "max_tokens": 180},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def speech(self, text: str):
        headers = {"X-Api-Key": self.voice_api_key,
                   "X-Api-Resource-Id": self.tts_resource_id,
                   "X-Api-Connect-Id": str(uuid.uuid4())}
        session_id = str(uuid.uuid4())
        try:
            async with connect(TTS_URL, additional_headers=headers, open_timeout=15,
                               close_timeout=5, max_size=None) as socket:
                async def expect(expected):
                    event, payload = decode_tts_message(await asyncio.wait_for(
                        socket.recv(), TTS_TIMEOUT))
                    if event != expected:
                        raise RuntimeError(f"火山 TTS 事件异常: {event}, 预期 {expected}")
                    return payload

                await socket.send(encode_tts_event(1))
                await expect(50)
                await socket.send(encode_tts_event(100, {
                    "namespace": "BidirectionalTTS", "user": {"uid": "mia-gateway"},
                    "req_params": {"speaker": "zh_female_vv_uranus_bigtts",
                                   "audio_params": {"format": "pcm", "sample_rate": 24_000}},
                }, session_id))
                await expect(150)
                await socket.send(encode_tts_event(200, {
                    "namespace": "BidirectionalTTS", "req_params": {"text": text},
                }, session_id))
                await socket.send(encode_tts_event(102, session_id=session_id))
                while True:
                    event, payload = decode_tts_message(await asyncio.wait_for(
                        socket.recv(), TTS_TIMEOUT))
                    if event == 352:
                        if payload:
                            yield payload
                    elif event == 152:
                        break
                    elif event == 153:
                        raise RuntimeError("火山 TTS 会话失败")
                await socket.send(encode_tts_event(2))
        except ConnectionClosed as exc:
            raise RuntimeError("火山 TTS 连接提前关闭") from exc

    async def close(self):
        if self.owns_client:
            await self.client.aclose()
