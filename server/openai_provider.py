"""Cloud ASR, chat, and 24 kHz PCM speech through the OpenAI HTTP API."""

import io
import os
import wave

import httpx


class OpenAIProvider:
    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("缺少 OPENAI_API_KEY")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=60)
        self.owns_client = client is None
        self.asr_model = os.environ.get("MIA_ASR_MODEL", "gpt-4o-mini-transcribe")
        self.chat_model = os.environ.get("MIA_CHAT_MODEL", "gpt-4o-mini")
        self.tts_model = os.environ.get("MIA_TTS_MODEL", "gpt-4o-mini-tts")
        self.voice = os.environ.get("MIA_TTS_VOICE", "coral")

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
        response = await self.client.post(
            self.base_url + "/audio/transcriptions", headers=self.headers,
            data={"model": self.asr_model, "language": "zh"},
            files={"file": ("mia-voice.wav", output.getvalue(), "audio/wav")},
        )
        response.raise_for_status()
        return response.json().get("text", "").strip()

    async def reply(self, user_text: str) -> str:
        response = await self.client.post(
            self.base_url + "/chat/completions", headers=self.headers,
            json={
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": "你是 Mia，亲切、简洁的中文语音伙伴。回答适合直接朗读，通常不超过两句话。"},
                    {"role": "user", "content": user_text},
                ],
                "max_tokens": 180,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def speech(self, text: str):
        async with self.client.stream(
            "POST", self.base_url + "/audio/speech", headers=self.headers,
            json={"model": self.tts_model, "voice": self.voice, "input": text,
                  "response_format": "pcm", "instructions": "用自然亲切的普通话说话。"},
            timeout=120,
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk

    async def close(self):
        if self.owns_client:
            await self.client.aclose()
