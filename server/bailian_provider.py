"""Alibaba Cloud Model Studio ASR, chat, and streamed 24 kHz PCM speech."""

import base64
import io
import json
import os
import wave

import httpx


REGION_HOSTS = {
    "cn-beijing": "dashscope.aliyuncs.com",
    "ap-southeast-1": "dashscope-intl.aliyuncs.com",
}


class BailianProvider:
    def __init__(self, api_key: str | None = None, region: str | None = None,
                 client: httpx.AsyncClient | None = None):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("缺少 DASHSCOPE_API_KEY")
        self.region = region or os.environ.get("MIA_BAILIAN_REGION")
        if self.region not in REGION_HOSTS:
            raise ValueError("MIA_BAILIAN_REGION 必须是 cn-beijing 或 ap-southeast-1")
        host = REGION_HOSTS[self.region]
        self.chat_url = f"https://{host}/compatible-mode/v1/chat/completions"
        self.tts_url = f"https://{host}/api/v1/services/aigc/multimodal-generation/generation"
        self.client = client or httpx.AsyncClient(timeout=60)
        self.owns_client = client is None
        self.asr_model = os.environ.get("MIA_ASR_MODEL", "qwen3-asr-flash")
        self.chat_model = os.environ.get("MIA_CHAT_MODEL", "qwen-plus")
        self.tts_model = os.environ.get("MIA_TTS_MODEL", "qwen3-tts-flash")
        self.voice = os.environ.get("MIA_TTS_VOICE", "Cherry")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    async def transcribe(self, pcm: bytes) -> str:
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16_000)
            wav.writeframes(pcm)
        audio = base64.b64encode(output.getvalue()).decode("ascii")
        response = await self.client.post(
            self.chat_url, headers=self.headers,
            json={"model": self.asr_model, "messages": [{"role": "user", "content": [{
                "type": "input_audio", "input_audio": {"data": f"data:audio/wav;base64,{audio}"},
            }]}], "stream": False, "asr_options": {"language": "zh"}},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def reply(self, user_text: str) -> str:
        response = await self.client.post(
            self.chat_url, headers=self.headers,
            json={"model": self.chat_model, "messages": [
                {"role": "system", "content": "你是 Mia，亲切、简洁的中文语音伙伴。回答适合直接朗读，通常不超过两句话。"},
                {"role": "user", "content": user_text},
            ], "max_tokens": 180},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def speech(self, text: str):
        async with self.client.stream(
            "POST", self.tts_url,
            headers={**self.headers, "X-DashScope-SSE": "enable"},
            json={"model": self.tts_model, "input": {
                "text": text, "voice": self.voice, "language_type": "Chinese"}},
            timeout=120,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event.get("code"):
                    raise RuntimeError(f"百炼 TTS 错误: {event['code']}")
                data = (event.get("output") or {}).get("audio") or {}
                if data.get("data"):
                    yield base64.b64decode(data["data"])

    async def close(self):
        if self.owns_client:
            await self.client.aclose()
