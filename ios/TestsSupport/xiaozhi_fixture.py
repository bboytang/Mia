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
    if not valid_identity(headers) or headers.get("Authorization") != "Bearer fixture-only":
        await ws.send("认证失败")
        await ws.close()
        return
    assert headers.get("Protocol-Version") == "1"
    hello = json.loads(await ws.recv())
    assert hello["type"] == "hello" and hello["version"] == 1
    assert not hello.get("features")
    assert hello["audio_params"] == {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60}
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

    async def automatic_response(packet):
        await asyncio.sleep(.1)
        for message in [{"type": "stt", "text": "用户识别文本"},
                        {"type": "tts", "state": "start"},
                        {"type": "tts", "state": "sentence_start", "text": "Mia 自动回复"}]:
            await ws.send(json.dumps(message))
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
        if event["type"] == "listen" and event["state"] == "start":
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
