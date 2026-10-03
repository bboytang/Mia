"""Verify the deployed WSS gateway handshake without consuming cloud API credits."""

import asyncio
import argparse
import getpass
import json

from websockets.asyncio.client import connect


async def main(endpoint: str):
    token = getpass.getpass("输入 iPhone 使用的网关令牌（不回显）：")
    async with connect(
        endpoint,
        additional_headers={"Authorization": f"Bearer {token}"},
        open_timeout=10,
    ) as socket:
        await socket.send(json.dumps({"type": "hello", "version": 1,
                                      "transport": "websocket"}))
        reply = json.loads(await asyncio.wait_for(socket.recv(), timeout=10))
        if reply.get("type") != "hello" or not reply.get("session_id"):
            raise RuntimeError(f"网关握手失败: {reply}")
        print("WSS、令牌和小智协议握手成功")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="wss://8kraw.cloud/xiaozhi/v1/")
    asyncio.run(main(parser.parse_args().endpoint))
