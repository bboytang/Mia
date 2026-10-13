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

用户随后确认：界面为“正在聆听”，系统有麦克风提示，讲话时流光不变化。新增处理系统 `AVAudioEngineConfigurationChange` 导致的引擎停止：异步退出旧音频/连接，再以原对话意图自动恢复，旧音频错误回调不能影响新连接。依据 [Apple 的配置变化说明](https://developer.apple.com/documentation/avfaudio/avaudioengineconfigurationchangenotification)，采样率/通道变化会停止并解除初始化引擎；不在通知回调中同步销毁引擎。采集 tap 使用当前原生格式，转换器根据实际帧格式建立/更新，转换失败明确报错，避免静默丢弃；16 kHz/mono/60 ms Opus 保持。增加真实 AVAudioConverter 的 48 kHz、44.1 kHz 双通道、16 kHz 切换及非静音 Opus 回归，不仅测试音频替身。

当前服务器单轮自动对话复测成功：中文录音上传后无 `listen.stop`，返回 STT、字幕、73 个 Opus 包，解码 PCM 140160 字节；不是 iPhone 麦克风验收。以上是代码中可确认的恢复/格式处理缺陷，尚不能证明手机已经触发该系统通知，实际修复效果待新版安装反馈。

用户反馈新版打开后讲话没有响应，自动对话真机验收未通过。只读服务器固定标签统计发现近 20 分钟有连接初始化，但无大模型收到消息事件；这不足以断言麦克风故障。代码确认网络断开后的重连调用 `connect()` 默认不启动录音，现保留原对话意图，在自动重连后重新聆听；主动停止仍取消重连，手动仅连接的流程仍不启动麦克风。增加回环断开后继续语音回答、重连等待期间主动停止两项测试。

设置页增加对话状态、采集音频帧、上传音频帧和输入峰值，不保存或输出录音、识别文本或凭据；断开后保留数值，下一次连接重置，便于用户回传诊断。当前只定位并修复重连缺陷，未证明它是本次 iPhone 无响应的全部原因；等待首页状态、流光反馈和系统麦克风指示。未修改运行中的小智服务端，未新增后台录音或唤醒模型。本地 49 项服务端回归通过；本次 iOS 测试、编译及 IPA 以随后 CI 为准。

## 2026-10-13 采集恢复修复构建通过（真机待验）

代码提交 `5b05979`（包含 `448a55d` 的重连修复）[完整 CI](https://github.com/bboytang/Mia/actions/runs/38319552307) 成功：71 项单元测试、3 项 UI 测试、模拟器与未签名真机编译、静音启动资源一致性、两尺寸录制、IPA 打包上传。新增四项回归覆盖自动对话重连后采集/回复、主动停止取消重连、音频引擎停止后的恢复及旧错误回调隔离、真实 AVAudioConverter 格式切换到非静音 Opus。现有 49 项服务端测试本地通过，运行中的小智服务端未修改。

[最新安装包](https://github.com/bboytang/Mia/actions/runs/38319552307/artifacts/11779066442) 需自行重签。用户应确认打开后说话时流光有变化并能自动回答；如仍无响应，讲话几秒后回传设置中的对话状态、采集音频帧、上传音频帧、输入峰值和连接诊断，不发送令牌或 Key。暂不宣称真机麦克风已恢复，也不把系统配置变化视为已经在用户手机上直接观测到的唯一根因。

## 2026-10-13 绑定误报与音频恢复循环修复（CI 通过，真机待验）

代码 `c3a6080` 的 [完整 CI](https://github.com/bboytang/Mia/actions/runs/38332993004) 通过 74 项单元测试、4 项 UI 测试、模拟器/设备编译、静音资源一致性、两尺寸录制和打包。原生 UI 回归实际完成待绑定→检查成功→返回首页无旧错误；音频恢复回归确认同一连接、无正常恢复弹窗、播放中恢复后可继续下一轮及失败不循环。

用户要求只下载 IPA，不下载含 App、测试结果和录屏的大 ZIP。[直接下载 IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-c3a6080172b3/Mia-unsigned.ipa)：13886244 字节（约 14 MB），未签名，需自行重签覆盖升级。SHA-256 `0a0a769028a6b906f7f3fd2605da7c59153fe0812e6322f03475258284507e38`。新增独立 `Publish standalone IPA` 工作流，只读取该分支已成功的 iOS 构建，核对打包校验，再上传一个 IPA 到 GitHub 预发布下载页；[发布 CI](https://github.com/bboytang/Mia/actions/runs/38334274352) 通过，并回下载逐字节比对。不重复编译、不把生成安装包提交进 Git。后续可手动指定已通过的 Build iOS App run ID。

真机采集、外放回声和语音打断仍待用户安装验证，不能将本次回环/界面测试记作真机完整验收。

用户真机反馈：检查设备绑定成功后仍出现“请先绑定”弹窗；进入聆听即出现“音频设备发生变化，正在恢复对话”。前一版 `5b05979` 未通过真机验收，不能继续按其 CI 成功推断采集正常。

已定位绑定检查没有清除 `MiaVoiceSession.errorMessage`，OTA 返回已绑定并清空激活码时，旧错误被首页弹窗显示。新增 `checkDeviceBinding()` 在结束旧会话后清除错误，再执行现有 OTA provider；仍需绑定的设备保留激活流程。设置页关闭后沿用自动启动条件，明确结束对话的用户不会被重新开启麦克风。

前版将音频配置变化送入网络故障重连，重建 AVAudioSession/Voice Processing 引发重复恢复。本版在现有引擎内 prepare/start，保留 WebSocket、认证和音频会话，不把配置通知当作用户可见错误。已运行的引擎忽略重复通知；等待或播放阶段恢复后，复用 abort/清空待播/重新 listen 流程，旧播放回调被轮次保护丢弃。实际恢复失败只停止并提示一次，不自动重建服务端连接。保留原生 Voice Processing、16 kHz 单声道 Opus、自动分句、仅 Mia 字幕和语音打断。

新增/更新回归：绑定错误清除后可以聆听、重复音频通知不重连/不弹窗、播放中恢复后继续下一轮、恢复失败不循环，以及原生 UI 的待绑定→检查成功→返回首页无旧弹窗。本地 Python fixture 编译、两次 OTA 绑定状态转换通过。Linux 无 Xcode；本版原生测试/编译和单独 IPA 发布均已通过 CI；真机采集与外放打断仍需安装反馈。未修改运行中的小智服务端，未关闭认证。

## 2026-10-13 真机语音已正常；整句字幕修复 CI 通过（字幕真机待验）

代码 `b9e5346` 的 [完整 CI](https://github.com/bboytang/Mia/actions/runs/38335899635) 全部成功：78 项单元测试、4 项 UI 测试、模拟器/设备编译、静音资源一致性、两尺寸录制与 IPA 打包。新增真实 URLSession 回环回归实际验证两句先排队再播放、第二轮清空、重复旧播放回调及打断后的字幕隔离。独立代码审查通过。

[直接下载字幕修复 IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-b9e534672920/Mia-unsigned.ipa)：13890950 字节，约 14 MB，未签名，需沿用原签名与 Bundle ID 覆盖升级。SHA-256 `416af10964b3d240be1929648558e3694e0d1facd527ff1e16fe86840b276848`。[独立发布 CI](https://github.com/bboytang/Mia/actions/runs/38337737482) 成功，回下载逐字节比对通过。用户已确认前版语音对话与打断正常；本版整句字幕在真实 iPhone 上的显示时延仍待安装确认。

发布过程曾因构建提交包含工作流改动且没有现有引用而返回 HTTP 403；参考 [GitHub 工作流权限说明](https://github.blog/changelog/2023-11-02-github-actions-enforcing-workflow-scope-when-creating-a-release/)，用已有授权 Git 身份创建指向已验证代码的轻量标签后发布成功。发布工作流现要求标签预先存在，校验标签提交等于构建 SHA，并使用 `--verify-tag`；后续发布前应创建/推送 `mia-ios-<代码 SHA 前 12 位>` 标签，再指定成功的 Build iOS App run ID。不扩展令牌权限、不写入新密钥、不覆盖已有发布文件。

用户已确认当前 iPhone 语音对话与开口打断正常；剩余问题是字幕滞后、讲话结束才显示、上一轮文字残留。检查确认旧字幕在收到下一句 `sentence_start` 时立即换计时，却仍被上一句排队音频的回调推进；固定每秒 6 字不适配语速；旧字幕没有在新 STT 时清空。

用户明确选择“按播放切换完整句字幕”。本版把每个 Opus 播放包 UUID 关联到收到该包时的句子 ID；首个实际 `.dataPlayedBack` 回调显示完整当前句，下一句的音频回调才切换。每包约 60 ms，因此显示使用这一粒度，不宣称采样级或字级同步。收到下一句文字不会提前覆盖上一句；TTS stop 不再补显示整段文字，避免播完才闪现。新 STT、打断、断开同时清理字幕与旧播放包映射；句子 ID 单调增长，旧/重复/乱序回调不能恢复旧字幕。最后一句可保留供阅读，下一轮识别到用户说话后清空。

保留已通过真机反馈的录音、Voice Processing、Opus、自动对话及打断，不修改小智服务端。新增字幕单测和真实 URLSession 回环测试覆盖两句提前排队、逐包播放切换、下一轮清空、重复/旧回调与打断；本地 Python fixture 编译及两轮 WebSocket 消息顺序验证通过，独立差异审查未发现需继续修改的问题。Linux 无 Xcode，原生 XCTest/编译已由上述 CI 验证；本版字幕真机时延仍需安装验证。交付继续提供单独 IPA，不让用户下载包含录屏和测试结果的大 ZIP。
