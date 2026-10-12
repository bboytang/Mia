# Mia 自建小智客户端集成

更新：2026-10-12；分支 `feature/mia-ios-bootstrap`。用户要求暂不使用 Mia 账号服务，改用自建 `xiaozhi-esp32-server 0.9.7`。本文记录协议核对、实现和验收边界，禁止修改运行中的服务端来绕过认证。

## 已定位的连接问题

- 原 App 只允许 WSS，首页还要求 Mia 账号会话；不能直接使用用户提供的 WS 地址。旧探测脚本则绕过 App，仅检查了裸 WebSocket。
- 原设备标识为 `ios-UUID`，未执行 OTA。完整版 [OTAController](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/manager-api/src/main/java/xiaozhi/modules/device/controller/OTAController.java) 要求 MAC 格式。它通过 [DeviceServiceImpl](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/manager-api/src/main/java/xiaozhi/modules/device/service/impl/DeviceServiceImpl.java) 下发绑定设备/客户端身份的令牌，并返回激活码。
- 已在同一实际地址对比：不带 OTA 令牌，HTTP 101 后关闭（1000，无原因）；带 OTA 令牌，可收到设备绑定提示。用户在智控台绑定联调设备后，OTA 不再返回激活要求，取得 `hello`、非空 `session_id` 和 16 kHz/mono/60 ms Opus 参数。这证明缺少 OTA 认证和设备绑定是此前探测失败的关键问题；没有服务端错误日志时，不推测其他后台异常。
- 协议依据：[websocket_server.py](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/xiaozhi-server/core/websocket_server.py)、[connection.py](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/xiaozhi-server/core/connection.py)、[helloHandle.py](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/xiaozhi-server/core/handle/helloHandle.py)、[listenMessageHandler.py](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/v0.9.7/main/xiaozhi-server/core/handle/textHandler/listenMessageHandler.py)。服务端支持查询参数兼容，但 URLSession 能发送自定义请求头，因此不把身份或令牌放入 URL。

## 最小客户端改动

- `MiaXiaozhiClient.swift`：复用持久化 UUID，保存本机逻辑 MAC（不是 iPhone 的硬件 MAC），执行 OTA POST，解析配置和激活码。WS 设置作为实际连接目标，OTA 下发地址用于核对主机与安全级别。令牌只用于本次连接，保存在内存；每次重连重新发现，不复用旧 Mia 账号/维护令牌。拒绝 OTA 重定向、跨主机凭据转发和 WSS 降级。地址修改或后台中止在途发现，迟到响应不能恢复旧配置。
- `MiaWebSocketTransport.swift`：WS/WSS、稳定身份头、协议 v1、Bearer 设备令牌。记录 HTTP 状态、关闭码、脱敏关闭原因、最后消息类别及 NSError domain/code；不记录地址中的参数、身份、语音文本或凭据。识别服务端非 JSON 的认证失败消息。
- `MiaWireProtocol.swift`：hello 必须有 session_id 和已支持的 Opus 参数；不声明 MCP/AEC。解析 STT、TTS、LLM 文本/情绪。STT 保留内存状态，不显示在 Mia 字幕。
- `MiaVoiceSession.swift`：复用 16 kHz mono PCM、60 ms Opus、实际服务端采样率播放和现有字幕推进。手动 listen/stop、尾帧补齐、思考/播放期间 abort、30 秒录音上限、45 秒无回复超时、有限断线重连（1/2/4 秒）。重连只恢复连接，不自动打开麦克风。断线/后台/中断停止音频；旧播放回调不能影响新回合。
- `ContentView.swift`：首页不再访问账号接口。设置提供 WS、OTA、设备绑定与脱敏诊断；角色、背景、无图标流光球和静音启动片不变。旧账号实现及本机数据保留，未修改服务端账号库。
- `project.yml`：只为当前 IP 和回环测试地址设置 ATS 例外，不启用 `NSAllowsArbitraryLoads`。iOS 17 支持 IP 例外，见 [Apple 说明](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsexceptiondomains)。明文 HTTP/WS 的令牌和语音仍可被中间人读取；正式部署改用 HTTPS/WSS。其他明文公网主机需单独审查并调整例外，HTTPS/WSS 地址可在设置中配置。

## iPhone 激活操作

1. 安装新版未签名 IPA（需自行重签），打开设置核对 OTA 和 WebSocket 地址。
2. 点击“检查设备绑定”。首次安装显示本机激活码，不打开麦克风。
3. 在自己的智控台打开目标智能体 → 设备管理／添加设备，输入该码，确认智能体的 ASR、LLM 和 TTS 配置。
4. 返回 Mia 点击“检查设备绑定”；配置就绪后回首页点击流光球，允许麦克风并说中文，点击结束；等待 Mia 语音和字幕。思考/说话时再次点击会打断并开始新录音。

联调脚本的设备与 iPhone 本机身份不同；绑定联调设备不能代替绑定 iPhone。App 不登录智控台、不索取管理密钥，不下载 OTA 中的 ESP 固件。

## 测试与真实验证

- 开发前本地 49 项服务端回归通过，未改动该服务端。Linux 无 Swift/Xcode，iOS 编译、XCTest 和原生 URLSession 网络测试使用既有 GitHub macOS CI。
- 新增回环协议夹具，必须校验设备 ID、协议版本和模拟设备令牌。原生测试覆盖 OTA、激活、重定向/HTTP 错误/取消、请求头、严格 hello、双向 Opus、STT/LLM/TTS 顺序、认证失败和主动断开后的恢复。夹具不连接真实云服务。[CI 已通过](https://github.com/bboytang/Mia/actions/runs/38303047948)：62 项单测、2 项 UI 测试、模拟器与设备目标编译、两尺寸屏幕录制、启动资源一致性及 IPA 打包上传。安装包见 [GitHub artifact](https://github.com/bboytang/Mia/actions/runs/38303047948/artifacts/11772390185)，需用户自行重签。
- 本地已检查夹具 OTA → hello → listen → Opus → STT/LLM/TTS 顺序与 Opus 回环；脚本编译检查通过。此项不是 iOS 原生测试或真实模型验收。
- CI 首轮 App 编译通过，但协议夹具启动阻塞。启动堆栈确认 `HTTPServer.server_bind` 的本机反向 DNS 查询停滞；夹具现直接绑定回环地址，已本地验证禁止反向 DNS 时仍可绑定。[复测](https://github.com/bboytang/Mia/actions/runs/38301157333) 已通过夹具启动、全部原生 OTA/Opus/消息顺序/重连测试和两项 UI 测试，但 62 项单测中一项请求头 CRLF 校验失败。Swift 将 CRLF 视作一个字符，逐个 `contains` 检查会漏掉；现改为 Unicode 标量检查，并补测 CR、LF、CRLF。[复测](https://github.com/bboytang/Mia/actions/runs/38302201785) 的 62 项单测已全部通过，但设置页 UI 测试出现 AX 自动滚动定位失败；已增加可点击等待并对固定按钮执行中心点击，保留设置页实际出现断言。[完整 CI](https://github.com/bboytang/Mia/actions/runs/38303047948) 已全部通过。
- 实际服务：OTA 200、绑定完成、带设备令牌的 101/hello/session_id 成功。上传仓库中文录音后 90 秒内无 STT/TTS/音频，延后开始发送的复测也超时；没有证明 ASR → LLM → TTS 成功。用户授权后已 SSH 只读检查，未改运行中的服务端。固定日志标签确认实际 ASR 资源为 `volc.seedasr.sauc.concurrent`，上游返回 `quota exceeded for types: concurrency`；[官方错误码说明](https://docs.volcengine.com/docs/DoubaoVoice/error-code-query-1?lang=zh)将其列为超并发。此前已成功验证的资源为 `volc.seedasr.sauc.duration`。需用户在控制台确认资源开通/额度并在智控台调整，未自动更改服务端或索取 Key。
- 用户将 ASR 改为按时长后首次复测仍使用旧资源。只读源码确认 `check_asr_update` 仅比较模块名称与类型，未比较资源 ID；用户明确批准后只重启语音容器，未改源码或服务器配置文件。随后真实复测收到 STT、TTS start、LLM 事件；仍无音频且 TTS 报 HTTP 403。实际 TTS 使用双向流式端点、资源 `volc.service_type.10029`，与此前已验证的 `seed-tts-2.0` 不同，已请用户在智控台调整。不能把 STT 成功当作完整对话验收。
- 尚未执行 iPhone 真机麦克风 → 真实 ASR → LLM → TTS → Mia 播放。不能把协议夹具、Python 合成录音测试、模拟器构建或单元测试当成这一完整验收。
