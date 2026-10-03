# Mia 本地协议测试服务

这是小智 WebSocket 版本 1 的联调夹具，不提供语音识别、AI 对话或真正的人声合成。收到 `listen/stop` 后，它返回固定的 Mia 文本与 1.2 秒 Opus 测试音，用来检查客户端连接、二进制音频解码和字幕推进。

Ubuntu 上运行：

```bash
sudo apt-get install -y libopus0 python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r server/requirements.txt
python -m server.mock_xiaozhi
```

默认只监听 `127.0.0.1:8765`。iPhone 端要求 `wss://`，所以远程联调还需在服务器上使用带 TLS 证书的反向代理转发到这个本地端口。可设置 `MIA_MOCK_TOKEN` 要求 `Authorization: Bearer <token>`；令牌只放在服务器环境中。不要把这个固定答复服务当作公开生产服务。

本地测试：`python -m unittest discover -s server/tests -v`。
