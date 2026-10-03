# Mia 本地语音联调服务计划

目标：在云 API、域名和 VPS 连接信息尚未准备好时，提供可运行的小智 WebSocket 版本 1 测试服务，验证 iOS 客户端的握手、聆听、Opus 播放和 Mia 字幕时序。

边界：这是开发测试服务，回答固定文字并播放测试音调，不宣称具有语音识别、对话或 TTS 能力；不得作为公开生产服务。正式服务仍需云端 ASR、LLM、TTS、WSS 与鉴权。

1. 新增 `server/mock_xiaozhi.py`，只绑定本机地址，按小智协议接收 `hello` 与 `listen/start|stop`，返回服务器 `hello`、`tts/start`、`tts/sentence_start`、原始 Opus 音频帧、`tts/stop`。
2. 使用系统 libopus 编码 24 kHz 单声道 60 ms 测试音调；二进制帧不加 Ogg 容器。
3. 测试客户端握手、消息顺序、音频帧与异常输入处理。
4. 在 GitHub Ubuntu runner 运行服务端测试，并记录本地运行方式。
