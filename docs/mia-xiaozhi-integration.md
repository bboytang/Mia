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
- `MiaVoiceSession.swift`：复用 16 kHz mono PCM、60 ms Opus、实际服务端采样率播放和现有字幕推进。默认 `listen mode=auto`，由服务端判断说完；播放结束后继续聆听。启用 iOS Voice Processing 和 muted speech activity 回调，思考/播放期间讲话可触发本地清理与 abort，控制消息等待期间有界暂存新录音。45 秒无回复超时、有限断线重连（1/2/4 秒）。重连只恢复连接，不自动打开麦克风。断线/后台/中断停止音频；旧播放回调不能影响新回合。
- `ContentView.swift`：首页不再访问账号接口。启动动画结束后前台自动连接/录音，首次由系统请求麦克风权限。流光球结束/重新开启整段对话；显式结束后不因前台变化恢复录音。设置提供 WS、OTA、设备绑定与脱敏诊断；角色、背景、无图标流光球和静音启动片不变。旧账号实现及本机数据保留，未修改服务端账号库。
- `project.yml`：只为当前 IP 和回环测试地址设置 ATS 例外，不启用 `NSAllowsArbitraryLoads`。iOS 17 支持 IP 例外，见 [Apple 说明](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsexceptiondomains)。明文 HTTP/WS 的令牌和语音仍可被中间人读取；正式部署改用 HTTPS/WSS。其他明文公网主机需单独审查并调整例外，HTTPS/WSS 地址可在设置中配置。

## iPhone 激活操作

1. 安装新版未签名 IPA（需自行重签），打开设置核对 OTA 和 WebSocket 地址。
2. 点击“检查设备绑定”。首次安装显示本机激活码，不打开麦克风。
3. 在自己的智控台打开目标智能体 → 设备管理／添加设备，输入该码，确认智能体的 ASR、LLM 和 TTS 配置。
4. 返回 Mia 点击“检查设备绑定”；配置就绪后回首页点击流光球开启（后续已绑定启动会自动开启），允许麦克风并说中文；说完自动等待 Mia 语音和字幕，播放完后继续下一句。思考/说话时开口打断，再次点击流光球结束整段对话。

联调脚本的设备与 iPhone 本机身份不同；绑定联调设备不能代替绑定 iPhone。App 不登录智控台、不索取管理密钥，不下载 OTA 中的 ESP 固件。

## 测试与真实验证

- 开发前本地 49 项服务端回归通过，未改动该服务端。Linux 无 Swift/Xcode，iOS 编译、XCTest 和原生 URLSession 网络测试使用既有 GitHub macOS CI。
- 新增回环协议夹具，必须校验设备 ID、协议版本和模拟设备令牌。原生测试覆盖 OTA、激活、重定向/HTTP 错误/取消、请求头、严格 hello、双向 Opus、STT/LLM/TTS 顺序、认证失败和主动断开后的恢复。夹具不连接真实云服务。[CI 已通过](https://github.com/bboytang/Mia/actions/runs/38303047948)：62 项单测、2 项 UI 测试、模拟器与设备目标编译、两尺寸屏幕录制、启动资源一致性及 IPA 打包上传。安装包见 [GitHub artifact](https://github.com/bboytang/Mia/actions/runs/38303047948/artifacts/11772390185)，需用户自行重签。
- 本地已检查夹具 OTA → hello → listen → Opus → STT/LLM/TTS 顺序与 Opus 回环；脚本编译检查通过。此项不是 iOS 原生测试或真实模型验收。
- CI 首轮 App 编译通过，但协议夹具启动阻塞。启动堆栈确认 `HTTPServer.server_bind` 的本机反向 DNS 查询停滞；夹具现直接绑定回环地址，已本地验证禁止反向 DNS 时仍可绑定。[复测](https://github.com/bboytang/Mia/actions/runs/38301157333) 已通过夹具启动、全部原生 OTA/Opus/消息顺序/重连测试和两项 UI 测试，但 62 项单测中一项请求头 CRLF 校验失败。Swift 将 CRLF 视作一个字符，逐个 `contains` 检查会漏掉；现改为 Unicode 标量检查，并补测 CR、LF、CRLF。[复测](https://github.com/bboytang/Mia/actions/runs/38302201785) 的 62 项单测已全部通过，但设置页 UI 测试出现 AX 自动滚动定位失败；已增加可点击等待并对固定按钮执行中心点击，保留设置页实际出现断言。[完整 CI](https://github.com/bboytang/Mia/actions/runs/38303047948) 已全部通过。
- 实际服务：OTA 200、绑定完成、带设备令牌的 101/hello/session_id 成功。上传仓库中文录音后 90 秒内无 STT/TTS/音频，延后开始发送的复测也超时；没有证明 ASR → LLM → TTS 成功。用户授权后已 SSH 只读检查，未改运行中的服务端。固定日志标签确认实际 ASR 资源为 `volc.seedasr.sauc.concurrent`，上游返回 `quota exceeded for types: concurrency`；[官方错误码说明](https://docs.volcengine.com/docs/DoubaoVoice/error-code-query-1?lang=zh)将其列为超并发。此前已成功验证的资源为 `volc.seedasr.sauc.duration`。需用户在控制台确认资源开通/额度并在智控台调整，未自动更改服务端或索取 Key。
- 用户将 ASR 改为按时长后首次复测仍使用旧资源。只读源码确认 `check_asr_update` 仅比较模块名称与类型，未比较资源 ID；用户明确批准后只重启语音容器，未改源码或服务器配置文件。随后真实复测收到 STT、TTS start、LLM 事件；仍无音频且 TTS 报 HTTP 403。实际 TTS 使用双向流式端点、资源 `volc.service_type.10029`，与此前已验证的 `seed-tts-2.0` 不同，已请用户在智控台调整。不能把 STT 成功当作完整对话验收。
- 用户已将 TTS 资源改为 `seed-tts-2.0`，新连接只读配置核对确认生效且未再出现先前 HTTP 403；复测仍只收到 STT、TTS start、LLM 事件，90 秒内没有音频。差异化配置中智能体 `private_voice` 覆盖了默认音色，实际仍为旧版 `_moon_bigtts` 音色；[官方双向流式说明](https://docs.volcengine.com/docs/DoubaoVoice/WebSocketBidirectionalStreaming-V3?lang=zh)要求 2.0 资源配 2.0 音色。已请用户将智能体与模型默认音色统一为此前 Mia 实测的 `zh_female_vv_uranus_bigtts` 后复测。未修改服务端源码，未将音色调整前的无音频结果写成成功。
- 用户新增/切换音色后管理页试听失败。只读官方 `TtsModel.vue`/`AudioPlayer.vue` 确认音色管理试听播放 `voiceDemo` 示例地址，不等价于实际 TTS 请求。实际连接仍无音频；差异化配置中智能体覆盖编码以 `zh_` 开头、无空白，但缺少完整 `_bigtts` 结尾，默认音色仍是旧版小何。已核对服务端日志脱敏函数不截断音色字段，已请用户检查新增记录的音色编码、智能体选择和模型默认音色。未输出任意配置/日志原文或凭据。
- 最新真实服务复测通过：完整音色编码替换后，差异化配置确认 `zh_female_vv_uranus_bigtts` 与 `seed-tts-2.0` 生效。Python 脚本上传仓库中文录音，收到 `stt → tts:start → llm → tts:sentence_start → Opus → tts:stop`，80 个 Opus 音频包成功解码为 16 kHz mono PCM，153600 字节（4.8 秒），RMS 2709.39，非静音。这证明真实服务端识别、回复字幕和合成音频的联调链路可用；使用的是现有诊断脚本（hello 后等待 3 秒再发录音），不是 iPhone 原生麦克风、播放或延迟验收。未继续增加无必要的云调用。
- 自动对话新版 [CI](https://github.com/bboytang/Mia/actions/runs/38314950163) 已通过：67 项单测、3 项 UI 测试、模拟器/设备编译、两尺寸屏幕录制与 IPA 打包上传。[安装包](https://github.com/bboytang/Mia/actions/runs/38314950163/artifacts/11776614004) 对应代码提交 `448e787`。回环原生测试涵盖连续两轮、等待实际播放完成再恢复采集、讲话事件触发 abort、旧播放/讲话回调丢弃、控制等待时暂存新录音、明确停止不允许自动重启及拒绝麦克风；UI 测试覆盖无点击自动 OTA 激活页面。
- 新版真实后端协议验证：`listen mode=auto`、无 `listen.stop`，静音后自动回复收到 59 个 Opus 包（PCM 113280 字节）；第一轮音频开始后发 abort，同一连接继续第二轮，收到第二次 STT、110 个 Opus 包（PCM 211200 字节）及 TTS stop。只读固定日志标签确认两次大模型收到用户消息，未见 LLM 处理错误，完成第二轮语音合成。均为 Python 协议脚本，不是 iPhone 的系统讲话检测实验。
- 用户旧版真机反馈能与 Mia 说话并听到回复，但每轮需点击发送、播放期间讲话不能打断。自动对话新版的 iPhone 麦克风、外放回声、首字完整性、系统语音打断及字幕实际推进仍待用户反馈；不能把回环音频替身/协议脚本当作该项验收。自定义后台/锁屏唤醒仅完成[限制评估](mia-voice-wakeup-assessment.md)，没有新增常驻录音、关键词模型或 Siri 入口。

## 2026-10-12 自动对话无响应排查（真机原因待确认）

用户反馈新版打开后讲话没有响应，自动对话真机验收未通过。只读服务器固定标签统计发现近 20 分钟有连接初始化，但无大模型收到消息事件；这不足以断言麦克风故障。代码确认网络断开后的重连调用 `connect()` 默认不启动录音，现保留原对话意图，在自动重连后重新聆听；主动停止仍取消重连，手动仅连接的流程仍不启动麦克风。增加回环断开后继续语音回答、重连等待期间主动停止两项测试。

设置页增加对话状态、采集音频帧、上传音频帧和输入峰值，不保存或输出录音、识别文本或凭据；断开后保留数值，下一次连接重置，便于用户回传诊断。当前只定位并修复重连缺陷，未证明它是本次 iPhone 无响应的全部原因；等待首页状态、流光反馈和系统麦克风指示。未修改运行中的小智服务端，未新增后台录音或唤醒模型。本地 49 项服务端回归通过；本次 iOS 测试、编译及 IPA 以随后 CI 为准。
