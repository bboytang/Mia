"""Loopback-only protocol fixture. Never connects to a cloud model or real device."""
import faulthandler

# Keep startup failures visible when a runner stalls before opening the ports.
faulthandler.dump_traceback_later(10)
import asyncio
import json
import re
import socketserver
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from websockets.asyncio.server import serve


def valid_identity(headers):
    return bool(re.fullmatch(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", headers.get("Device-Id", "")))


activation_once = set()


class OTA(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Requests contain identities; never log them.

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ready")

    def do_POST(self):
        params = parse_qs(urlsplit(self.path).query)
        status = int(params.get("status", [200])[0])
        if "delay" in params:
            time.sleep(.5)
        if not valid_identity(self.headers):
            status = 400
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if status == 302:
            self.send_header("Location", "http://127.0.0.1:8770/redirect-must-not-be-followed")
        self.end_headers()
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        assert body.get("mac_address") == self.headers.get("Device-Id")
        assert body.get("uuid") == self.headers.get("Client-Id")
        result = {"websocket": {"url": "ws://127.0.0.1:8769/xiaozhi/v1/", "token": "fixture-only"}}
        device = self.headers.get("Device-Id")
        if "activation" in params or ("activation_once" in params and device not in activation_once):
            result["activation"] = {"code": "123456"}
            if "activation_once" in params:
                activation_once.add(device)
        self.wfile.write(json.dumps(result).encode())


closed_once = set()


class LoopbackHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        # The fixture needs no reverse DNS; macOS runners can stall resolving localhost.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address


async def websocket(ws):
    headers = ws.request.headers
    params = parse_qs(urlsplit(ws.request.path).query)
    queued_subtitles = params.get("subtitles") == ["queued"]
    if not valid_identity(headers) or headers.get("Authorization") != "Bearer fixture-only":
        await ws.send("认证失败")
        await ws.close()
        return
    assert headers.get("Protocol-Version") == "1"
    hello = json.loads(await ws.recv())
    assert hello["type"] == "hello" and hello["version"] == 1
    assert not hello.get("features")
    assert hello["audio_params"] == {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60}
    if params.get("private_auth") == ["required"]:
        await ws.send(json.dumps({"type": "mia_authorization", "status": "required"}))
        await ws.wait_closed()
        return
    await ws.send(json.dumps({"type": "hello", "transport": "websocket", "session_id": "fixture-session", "audio_params": hello["audio_params"]}))
    device = headers["Device-Id"]
    if "close_once" in ws.request.path and device not in closed_once:
        closed_once.add(device)
        await asyncio.sleep(.3)
        await ws.close(code=1001)
        return
    frames = []
    mode = "manual"
    response_task = None
    memory = {"memories": [{"id": "fixture-memory", "category": "preference", "content": "喜欢直接的反馈",
                           "source": "请直接指出问题", "session_id": "earlier-session", "confirmed": True,
                           "created_at": 1800000000, "updated_at": 1800000000}],
              "paused": False, "personality": {"version": 0, "traits": []}}

    extensions = params.get("memory") == ["extensions"]
    extension_actions = ["job_status", "events", "event_delete", "emotion_consent", "emotion_status", "observations",
                         "observation_update", "observation_delete", "emotion_clear"]
    if extensions:
        memory["management"] = {"version": 1, "actions": extension_actions}
    tracking = {"consent": {"enabled": 0, "version": 0}, "trend": {"status": "disabled"},
                "observations": [{"id": "fixture-observation", "source_kind": "self_report", "tendency": "negative",
                    "confidence": .9, "observed_at": 1800000000, "source_excerpt": "我今天很难过", "version": 1}]}
    events = {"events": [{"id": "fixture-event", "event_type": "boundary", "state": "active", "version": 1}]}

    async def automatic_response(packet):
        await asyncio.sleep(.1)
        await ws.send(json.dumps({"type": "stt", "text": "用户识别文本"}))
        if params.get("thinking") == ["delayed"]:
            await asyncio.sleep(.5)
        await ws.send(json.dumps({"type": "tts", "state": "start"}))
        sentences = ["第一句回复", "下一句回复"] if queued_subtitles else ["Mia 自动回复"]
        for index, text in enumerate(sentences):
            sentence = {"type": "tts", "state": "sentence_start", "text": text}
            if queued_subtitles:
                sentence.update(emotion="happy" if index == 0 else "caring", intensity=.8 if index == 0 else .6)
            await ws.send(json.dumps(sentence))
            for _ in range(2 if queued_subtitles else 1):
                await ws.send(packet)
        await ws.send(json.dumps({"type": "tts", "state": "stop"}))

    async for raw in ws:
        if isinstance(raw, bytes):
            frames.append(raw)
            if mode == "auto" and response_task is None:
                response_task = asyncio.create_task(automatic_response(raw))
            continue
        event = json.loads(raw)
        assert event.get("session_id") == "fixture-session"
        if event["type"] == "mia_memory":
            request_id = event["request_id"]
            assert str(uuid.UUID(request_id)).lower() == request_id.lower()
            if params.get("memory") == ["wrong_id_first"]:
                await ws.send(json.dumps({"type": "mia_memory", "request_id": str(uuid.uuid4()),
                                          "result": {"memories": [], "paused": True,
                                                     "personality": {"version": 99, "traits": []}}}))
                await asyncio.sleep(.1)
            if params.get("memory") == ["delayed"]:
                await asyncio.sleep(.5)
            action = event["action"]
            if extensions and action in extension_actions + ["job_status"]:
                if action == "event_delete":
                    events["events"] = [item for item in events["events"] if item["id"] != event["id"]]
                elif action == "emotion_consent":
                    tracking["consent"] = {"enabled": int(event["enabled"]), "version": tracking["consent"]["version"] + 1}
                    tracking["trend"] = {"status": "insufficient_observations" if event["enabled"] else "disabled"}
                elif action == "observation_update":
                    tracking["observations"][0].update(tendency=event["tendency"], version=2)
                elif action in ["observation_delete", "emotion_clear"]:
                    tracking["observations"] = []
                result = events if action in ["events", "event_delete"] else tracking
                if action == "job_status":
                    result = {"id": event.get("id", "fixture-task"), "state": "committed", "confirmation_required": True}
                await ws.send(json.dumps({"type": "mia_memory", "request_id": request_id, "result": result}))
                continue
            if action == "pause":
                memory["paused"] = event["paused"]
            elif action == "update":
                for item in memory["memories"]:
                    if item["id"] == event["id"]:
                        item["content"] = event["content"]
                        item["confirmed"] = event.get("confirmed", item["confirmed"])
            elif action == "delete":
                memory["memories"] = [item for item in memory["memories"] if item["id"] != event["id"]]
            elif action == "clear":
                memory["memories"] = []
                memory["personality"] = {"version": memory["personality"]["version"] + 1, "traits": []}
            elif action == "reset_personality":
                memory["personality"] = {"version": memory["personality"]["version"] + 1, "traits": []}
            elif action not in ["list", "personality"]:
                await ws.send(json.dumps({"type": "mia_memory", "request_id": request_id,
                                          "error": {"code": "invalid_input", "message": "Unknown action"}}))
                continue
            await ws.send(json.dumps({"type": "mia_memory", "request_id": request_id, "result": memory}))
            if extensions and action == "list":
                await ws.send(json.dumps({"type": "mia_memory_job", "status": "accepted", "accepted": True,
                                          "id": "fixture-task", "state": "pending", "turn_id": "fixture-turn"}))
        elif event["type"] == "listen" and event["state"] == "start":
            assert event["mode"] in ["manual", "auto"]
            mode = event["mode"]
            response_task = None
            frames.clear()
        elif event["type"] == "listen" and event["state"] == "stop":
            assert frames
            for message in [{"type": "stt", "text": "用户识别文本"}, {"type": "llm", "emotion": "happy"},
                            {"type": "tts", "state": "start"}, {"type": "tts", "state": "sentence_start", "text": "Mia 回复"}]:
                await ws.send(json.dumps(message))
            for frame in frames:
                await ws.send(frame)
            await ws.send(json.dumps({"type": "tts", "state": "stop"}))
        elif event["type"] == "abort":
            if response_task:
                response_task.cancel()
                response_task = None
            frames.clear()


async def main():
    server = LoopbackHTTPServer(("127.0.0.1", 8770), OTA)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    async with serve(websocket, "127.0.0.1", 8769):
        faulthandler.cancel_dump_traceback_later()
        print("Xiaozhi fixture ready", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    assert valid_identity({"Device-Id": "02:11:22:33:44:55"})
    assert not valid_identity({"Device-Id": "ios-invalid"})
    asyncio.run(main())
