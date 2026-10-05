"""Local administrator check: disposable account, no cloud calls or credential output."""

import argparse
import asyncio
import json
from pathlib import Path
import secrets
import sqlite3

import httpx
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from server.opus_pcm import OpusEncoder


async def rejected(socket):
    try:
        await asyncio.wait_for(socket.recv(), 10)
    except ConnectionClosed as error:
        if error.rcvd and error.rcvd.code == 1008 and error.rcvd.reason == "未授权":
            return
    raise RuntimeError("撤销或错误凭据未被拒绝")


async def check(origin: str, endpoint: str, database: Path):
    username = "check_" + secrets.token_hex(10)
    password = secrets.token_urlsafe(32)
    created = False
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as http:
            async def request(action, expected, **kwargs):
                response = await http.post(origin + "/api/auth/" + action, **kwargs)
                if response.status_code != expected:
                    raise RuntimeError(f"账号 {action} 失败：HTTP {response.status_code}")
                if response.headers.get("Cache-Control") != "no-store":
                    raise RuntimeError("账号响应缺少 no-store")
                return response

            registered = await request("register", 201, json={"username": username, "password": password})
            created = True
            first = registered.json()["token"]
            login = await request("login", 200, json={"username": username, "password": password})
            token = login.json()["token"]
            headers = {"Authorization": "Bearer " + token}
            async with connect(endpoint, additional_headers=headers, open_timeout=10) as socket:
                await socket.send(json.dumps({"type": "hello", "version": 1, "transport": "websocket"}))
                hello = json.loads(await asyncio.wait_for(socket.recv(), 10))
                if hello.get("type") != "hello" or not hello.get("session_id"):
                    raise RuntimeError("账号 WebSocket 握手失败")
                await request("logout", 204, headers=headers)
                await socket.send(json.dumps({"type": "listen", "state": "start"}))
                encoder = OpusEncoder(16_000)
                try:
                    await socket.send(encoder.encode(bytes(1_920)))
                finally:
                    encoder.close()
                await socket.send(json.dumps({"type": "listen", "state": "stop"}))
                await rejected(socket)
            for invalid in (token, secrets.token_urlsafe(32)):
                async with connect(endpoint, additional_headers={"Authorization": "Bearer " + invalid},
                                   open_timeout=10) as socket:
                    await rejected(socket)
            await request("logout", 204, headers={"Authorization": "Bearer " + first})
        print("账号注册、登录、握手、退出及撤销后拒绝新回合：通过")
    finally:
        if created:
            with sqlite3.connect(database) as db:
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("DELETE FROM users WHERE username=?", (username,))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8766")
    parser.add_argument("--endpoint", default="ws://127.0.0.1:8765/xiaozhi/v1/")
    parser.add_argument("--db", type=Path, default=Path("/var/lib/mia/accounts.sqlite3"))
    args = parser.parse_args()
    try:
        asyncio.run(check(args.origin, args.endpoint, args.db))
    except Exception as error:
        # Exceptions may contain request objects; never print their raw contents.
        print("账号部署自测失败：" + type(error).__name__)
        raise SystemExit(1) from None
