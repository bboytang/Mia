# Mia 云语音网关实施计划

目标：在现有协议测试夹具之外，实现可配置的 Ubuntu 小智 WebSocket v1 网关。用户开通 API 后由云端完成中文 ASR、LLM 和 TTS，iOS 客户端无需改变协议。

依据：OpenAI 官方接口文档列出 `gpt-4o-mini-transcribe`、`gpt-4o-mini-tts` 及 raw PCM 24 kHz/16-bit little-endian；网关默认使用这些能力和 `gpt-4o-mini` 对话模型。模型名通过环境变量可替换。计费与账号可用性上线前再核对。

约束：仅本机监听，由 TLS 反向代理提供 WSS；必须校验客户端 Bearer 令牌；服务端密钥只从环境变量读取；输入音频限制时长；断开或 abort 时取消云请求；STT 结果不发送给 iOS 主字幕。

1. 为网关封装 raw Opus 16 kHz 输入解码和 24 kHz 输出编码，并测试帧尺寸与往返。
2. 实现可替换 provider 接口；OpenAI provider 负责 WAV ASR、中文 LLM 和 PCM TTS 流，测试使用内存 fake provider，避免依赖真实 API 额度。
3. 实现 WebSocket hello/listen/abort 状态和 TTS 事件、二进制帧顺序；测试空输入、令牌、打断、超限和正常回答。
4. GitHub Ubuntu CI 安装依赖并执行测试；写出 Ubuntu systemd/Caddy 部署模板，但不预填域名或密钥。
