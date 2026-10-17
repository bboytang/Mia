# Mia iOS 跨设备 Codex 交接

> 本文保留此前客户端/部署/回滚历史，未在本次重新核实生产或真机状态。当前开发进度与执行授权以[人格与记忆交接](mia-persona-memory-handoff.md)为准：2026-10-17用户已确认模型和P22通过，等待下一阶段批准。本文旧“最新/下一步”不触发新的部署或开发。

## 2026-10-13 情绪伙伴升级实施中

用户已批准玻璃小球替代人物、取消启动动画和字幕、系统声音快捷指令＋灵动岛、自动长期记忆与自然性格成长。持续状态统一记录在 [新交接](mia-companion-handoff.md)、[工作记录](mia-companion-worklog.md)、[实施计划](mia-companion-implementation.md)，不要按下方历史版本恢复自动录音或字幕。

最新[情绪伙伴预览IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-0d9a7cf43a91/Mia-unsigned.ipa)原成功构建85单测/4UI及打包已通过并回下载验证；最新81项服务端测试通过且生产记忆已部署/联调。真机后台/锁屏仍未验，重复标签复核单元/UI已通过，截图状态见新交接。

服务器SSH已使用用户指定root账户恢复并完成备份部署。原生CI和真机验收状态以新记录为准。

## 2026-10-13 真机语音已正常；整句字幕修复 CI 通过（字幕真机待验）

代码 `b9e5346` 的 [完整 CI](https://github.com/bboytang/Mia/actions/runs/38335899635) 全部成功：78 项单元测试、4 项 UI 测试、模拟器/设备编译、静音资源一致性、两尺寸录制与 IPA 打包。新增真实 URLSession 回环回归实际验证两句先排队再播放、第二轮清空、重复旧播放回调及打断后的字幕隔离。独立代码审查通过。

[直接下载字幕修复 IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-b9e534672920/Mia-unsigned.ipa)：13890950 字节，约 14 MB，未签名，需沿用原签名与 Bundle ID 覆盖升级。SHA-256 `416af10964b3d240be1929648558e3694e0d1facd527ff1e16fe86840b276848`。[独立发布 CI](https://github.com/bboytang/Mia/actions/runs/38337737482) 成功，回下载逐字节比对通过。用户已确认前版语音对话与打断正常；本版整句字幕在真实 iPhone 上的显示时延仍待安装确认。

发布过程曾因构建提交包含工作流改动且没有现有引用而返回 HTTP 403；参考 [GitHub 工作流权限说明](https://github.blog/changelog/2023-11-02-github-actions-enforcing-workflow-scope-when-creating-a-release/)，用已有授权 Git 身份创建指向已验证代码的轻量标签后发布成功。发布工作流现要求标签预先存在，校验标签提交等于构建 SHA，并使用 `--verify-tag`；后续发布前应创建/推送 `mia-ios-<代码 SHA 前 12 位>` 标签，再指定成功的 Build iOS App run ID。不扩展令牌权限、不写入新密钥、不覆盖已有发布文件。

用户已确认当前 iPhone 语音对话与开口打断正常；剩余问题是字幕滞后、讲话结束才显示、上一轮文字残留。检查确认旧字幕在收到下一句 `sentence_start` 时立即换计时，却仍被上一句排队音频的回调推进；固定每秒 6 字不适配语速；旧字幕没有在新 STT 时清空。

用户明确选择“按播放切换完整句字幕”。本版把每个 Opus 播放包 UUID 关联到收到该包时的句子 ID；首个实际 `.dataPlayedBack` 回调显示完整当前句，下一句的音频回调才切换。每包约 60 ms，因此显示使用这一粒度，不宣称采样级或字级同步。收到下一句文字不会提前覆盖上一句；TTS stop 不再补显示整段文字，避免播完才闪现。新 STT、打断、断开同时清理字幕与旧播放包映射；句子 ID 单调增长，旧/重复/乱序回调不能恢复旧字幕。最后一句可保留供阅读，下一轮识别到用户说话后清空。

保留已通过真机反馈的录音、Voice Processing、Opus、自动对话及打断，不修改小智服务端。新增字幕单测和真实 URLSession 回环测试覆盖两句提前排队、逐包播放切换、下一轮清空、重复/旧回调与打断；本地 Python fixture 编译及两轮 WebSocket 消息顺序验证通过，独立差异审查未发现需继续修改的问题。Linux 无 Xcode，原生 XCTest/编译已由上述 CI 验证；本版字幕真机时延仍需安装验证。交付继续提供单独 IPA，不让用户下载包含录屏和测试结果的大 ZIP。


## 2026-10-13 绑定误报与音频恢复循环修复（CI 通过，真机待验）

代码 `c3a6080` 的 [完整 CI](https://github.com/bboytang/Mia/actions/runs/38332993004) 通过 74 项单元测试、4 项 UI 测试、模拟器/设备编译、静音资源一致性、两尺寸录制和打包。原生 UI 回归实际完成待绑定→检查成功→返回首页无旧错误；音频恢复回归确认同一连接、无正常恢复弹窗、播放中恢复后可继续下一轮及失败不循环。

用户要求只下载 IPA，不下载含 App、测试结果和录屏的大 ZIP。[直接下载 IPA](https://github.com/bboytang/Mia/releases/download/mia-ios-c3a6080172b3/Mia-unsigned.ipa)：13886244 字节（约 14 MB），未签名，需自行重签覆盖升级。SHA-256 `0a0a769028a6b906f7f3fd2605da7c59153fe0812e6322f03475258284507e38`。新增独立 `Publish standalone IPA` 工作流，只读取该分支已成功的 iOS 构建，核对打包校验，再上传一个 IPA 到 GitHub 预发布下载页；[发布 CI](https://github.com/bboytang/Mia/actions/runs/38334274352) 通过，并回下载逐字节比对。不重复编译、不把生成安装包提交进 Git。后续可手动指定已通过的 Build iOS App run ID。

真机采集、外放回声和语音打断仍待用户安装验证，不能将本次回环/界面测试记作真机完整验收。

用户真机反馈：检查设备绑定成功后仍出现“请先绑定”弹窗；进入聆听即出现“音频设备发生变化，正在恢复对话”。前一版 `5b05979` 未通过真机验收，不能继续按其 CI 成功推断采集正常。

已定位绑定检查没有清除 `MiaVoiceSession.errorMessage`，OTA 返回已绑定并清空激活码时，旧错误被首页弹窗显示。新增 `checkDeviceBinding()` 在结束旧会话后清除错误，再执行现有 OTA provider；仍需绑定的设备保留激活流程。设置页关闭后沿用自动启动条件，明确结束对话的用户不会被重新开启麦克风。

前版将音频配置变化送入网络故障重连，重建 AVAudioSession/Voice Processing 引发重复恢复。本版在现有引擎内 prepare/start，保留 WebSocket、认证和音频会话，不把配置通知当作用户可见错误。已运行的引擎忽略重复通知；等待或播放阶段恢复后，复用 abort/清空待播/重新 listen 流程，旧播放回调被轮次保护丢弃。实际恢复失败只停止并提示一次，不自动重建服务端连接。保留原生 Voice Processing、16 kHz 单声道 Opus、自动分句、仅 Mia 字幕和语音打断。

新增/更新回归：绑定错误清除后可以聆听、重复音频通知不重连/不弹窗、播放中恢复后继续下一轮、恢复失败不循环，以及原生 UI 的待绑定→检查成功→返回首页无旧弹窗。本地 Python fixture 编译、两次 OTA 绑定状态转换通过。Linux 无 Xcode；本版原生测试/编译和单独 IPA 发布均已通过 CI；真机采集与外放打断仍需安装反馈。未修改运行中的小智服务端，未关闭认证。


## 2026-10-13 采集恢复修复构建通过（真机待验）

代码提交 `5b05979`（包含 `448a55d` 的重连修复）[完整 CI](https://github.com/bboytang/Mia/actions/runs/38319552307) 成功：71 项单元测试、3 项 UI 测试、模拟器与未签名真机编译、静音启动资源一致性、两尺寸录制、IPA 打包上传。新增四项回归覆盖自动对话重连后采集/回复、主动停止取消重连、音频引擎停止后的恢复及旧错误回调隔离、真实 AVAudioConverter 格式切换到非静音 Opus。现有 49 项服务端测试本地通过，运行中的小智服务端未修改。

[最新安装包](https://github.com/bboytang/Mia/actions/runs/38319552307/artifacts/11779066442) 需自行重签。用户应确认打开后说话时流光有变化并能自动回答；如仍无响应，讲话几秒后回传设置中的对话状态、采集音频帧、上传音频帧、输入峰值和连接诊断，不发送令牌或 Key。暂不宣称真机麦克风已恢复，也不把系统配置变化视为已经在用户手机上直接观测到的唯一根因。


## 2026-10-12 自动对话无响应排查（真机原因待确认）

用户随后确认：界面为“正在聆听”，系统有麦克风提示，讲话时流光不变化。新增处理系统 `AVAudioEngineConfigurationChange` 导致的引擎停止：异步退出旧音频/连接，再以原对话意图自动恢复，旧音频错误回调不能影响新连接。依据 [Apple 的配置变化说明](https://developer.apple.com/documentation/avfaudio/avaudioengineconfigurationchangenotification)，采样率/通道变化会停止并解除初始化引擎；不在通知回调中同步销毁引擎。采集 tap 使用当前原生格式，转换器根据实际帧格式建立/更新，转换失败明确报错，避免静默丢弃；16 kHz/mono/60 ms Opus 保持。增加真实 AVAudioConverter 的 48 kHz、44.1 kHz 双通道、16 kHz 切换及非静音 Opus 回归，不仅测试音频替身。

当前服务器单轮自动对话复测成功：中文录音上传后无 `listen.stop`，返回 STT、字幕、73 个 Opus 包，解码 PCM 140160 字节；不是 iPhone 麦克风验收。以上是代码中可确认的恢复/格式处理缺陷，尚不能证明手机已经触发该系统通知，实际修复效果待新版安装反馈。

用户反馈新版打开后讲话没有响应，自动对话真机验收未通过。只读服务器固定标签统计发现近 20 分钟有连接初始化，但无大模型收到消息事件；这不足以断言麦克风故障。代码确认网络断开后的重连调用 `connect()` 默认不启动录音，现保留原对话意图，在自动重连后重新聆听；主动停止仍取消重连，手动仅连接的流程仍不启动麦克风。增加回环断开后继续语音回答、重连等待期间主动停止两项测试。

设置页增加对话状态、采集音频帧、上传音频帧和输入峰值，不保存或输出录音、识别文本或凭据；断开后保留数值，下一次连接重置，便于用户回传诊断。当前只定位并修复重连缺陷，未证明它是本次 iPhone 无响应的全部原因；等待首页状态、流光反馈和系统麦克风指示。未修改运行中的小智服务端，未新增后台录音或唤醒模型。本地 49 项服务端回归通过；本次 iOS 测试、编译及 IPA 以随后 CI 为准。


## 2026-10-12 自动连续对话与语音打断（CI 通过，真机待验）

用户真机反馈已能对话，但每句仍需开始/发送按钮且不能开口打断。用户明确要求打开即聊；客户端已改为启动动画结束后前台自动连接、自动聆听、说完自动回复、实际播放完毕后继续聆听，按钮用于结束/重新开启整段对话。启用原生 Voice Processing 和 muted speech activity 回调；播放中讲话会停止本地待播音频、清理字幕并发送 abort，再恢复录音。后台和音频中断仍清理资源；不虚报服务端 AEC/MCP。打断检测后立即恢复采集，以现有有界队列暂存等待控制消息期间的首帧；明确点结束后，本次 App 会话不会被前台回调重新开启麦克风，手动点开始可恢复。[CI](https://github.com/bboytang/Mia/actions/runs/38314950163) 已全部通过：67 项单测、3 项 UI 测试、模拟器/设备编译、两尺寸录制、静音资源一致性和未签名 IPA 上传。[新版安装包](https://github.com/bboytang/Mia/actions/runs/38314950163/artifacts/11776614004) 需自行重签。

真实服务先行验证：`listen mode=auto`，不发送 `listen.stop`，上传中文录音及静音后，服务端自动返回 STT、字幕、59 个 Opus 包与 TTS stop，解码 PCM 113280 字节。另一次真实协议验证在第一轮音频开始后发送 abort，同一连接继续完成第二轮 STT、110 个 Opus 包及 TTS stop，解码 PCM 211200 字节。固定日志标签确认两次大模型收到用户消息，未见 LLM 处理错误；成功合成第二轮语音。这些脚本验证不等于 iPhone 回声处理、系统讲话检测或首字完整性验收。

用户要求后台/锁屏自定义“Mia”唤醒，不接受 Siri，本阶段仅评估。已开启录音后的后台延续和挂起/终止后的系统级唤醒不同；未新增后台常驻录音或关键词引擎。见[限制评估](mia-voice-wakeup-assessment.md)。


## 2026-10-12 小智 0.9.7 正式集成（实施中）

最新验收（真实服务链路通过，iPhone 待验）：用户替换完整音色编码后，新连接确认有效音色 `zh_female_vv_uranus_bigtts` 与资源 `seed-tts-2.0`。Python 联调脚本上传仓库中文录音，经真实小智服务收到 `stt → tts:start → llm → tts:sentence_start → Opus → tts:stop`；共 80 个 Opus 包，解码为 16 kHz 单声道 PCM，153600 字节、4.8 秒，音频非静音。此结果不是原生 iPhone 麦克风/播放验收；下一步安装已通过 CI 的 IPA，绑定 iPhone 自己的激活码，确认声音、仅 Mia 字幕、字幕推进及打断。

用户补充实际运行 Debian 13.2 / 小智 0.9.7，并要求完成正式 OTA、设备绑定及双向语音。已对照官方 v0.9.7 源码，正常 OTA 获取设备令牌后完成联调设备绑定，获得 hello/session_id；不带令牌的连接仍以 1000 关闭。此前缺少 OTA 认证、MAC 格式身份和激活流程是已定位的问题，旧 App 另有仅 WSS/账号入口限制。

客户端已实现独立 `MiaXiaozhiClient`、稳定 UUID/逻辑 MAC、OTA/激活界面、WS/WSS、严格 hello、脱敏诊断、有限自动重连及音频异常清理，保留既有 Opus 和仅 Mia 字幕，取消账号 UI 但不删除旧账号代码/数据。WS 配置是实际连接目标，OTA 下发地址用于核对主机与安全级别，令牌仅绑定本机身份；不使用智控台管理密钥。局部 ATS 例外允许当前服务器明文，未全局关闭 ATS。新增原生回环协议测试及 UI 测试，编译和 CI 已通过（见下方验证边界）。

真实语音探测上传仓库中文录音、发送 listen stop 后 90 秒内没有 STT/TTS/音频；延后发送复测同样超时。用户授权后已 SSH 只读排查，未修改运行中的服务端。日志固定标签确认 ASR 使用 `volc.seedasr.sauc.concurrent`，初始化返回 `quota exceeded for types: concurrency`；这与此前已验证的按时长资源 `volc.seedasr.sauc.duration` 不同。用户已在智控台改为按时长资源，并明确批准仅重启语音容器；其他容器未动。已读源码确认 ASR 更新判定仅比较模块名称/类型，修改同模型资源 ID 需要重载。重启后复测收到 STT、TTS start、LLM 事件，但没有音频；当时 TTS HTTP 403，双流端点正确但实际资源为 `volc.service_type.10029`，与已实测的 `seed-tts-2.0` 不同。用户已调整 TTS 资源，新连接确认生效且未再见 403，但仍无音频；智能体 `private_voice` 仍覆盖为旧版 `_moon_bigtts` 音色，已请用户将智能体和模型默认音色统一为已实测的 `zh_female_vv_uranus_bigtts` 后复测。客户端 [CI](https://github.com/bboytang/Mia/actions/runs/38303047948) 全部通过：62 项单测、2 项 UI 测试、模拟器/设备编译、两尺寸录制及未签名 IPA 打包上传。此探测是 Python 客户端，不是 iPhone 麦克风或完整原生验收，不能宣称全链路成功。完整实现、绑定操作和验证边界见[小智集成记录](mia-xiaozhi-integration.md)。

历史音色排查：用户新增/切换音色后，管理页试听失败。音色管理试听使用独立 `voiceDemo` 示例地址；实际语音复测仍无音频。已确认下发的智能体音色覆盖编码缺少完整 `_bigtts` 结尾，默认音色仍为旧版小何；已请用户核对音色编码及智能体选中记录，不能据此宣称链路完成。

## 2026-10-12 自建小智直连方向（最新决定）

用户已在腾讯云部署“小智 AI 服务端 0.5.7”应用模板，并明确暂不使用 Mia 账号服务，提供地址 `ws://43.143.230.174:8000/xiaozhi/v1/`。下一步以自建小智直连为目标；原角色、星雾 UI、静音启动片、Opus、仅 Mia 字幕与打断保留。旧账号代码和数据不删除，不把历史 Mia 网关部署状态当作重装后现状。

本次外部只读检查：WebSocket 升级成功；用现有 `ios-UUID` 和随机本地 MAC 格式分别发送现有 v1 hello，两次均在收到 hello 前由服务器正常关闭（1000、无原因）。未发送音频、listen 或调用收费 API；还没有真实语音互通证据。需用户确认管理后台智能体和 ASR/LLM/TTS 是否配置、其他设备能否聊天，再定位服务端关闭原因。没有依据认为“免账号”等于“免设备绑定或鉴权”。

本地 `feature/mia-ios-bootstrap` 核对前干净，49 项服务端基线测试在允许回环套接字的环境通过。当前 App 仍仅允许 WSS，且保留账号入口；尚未改为直连、未生成新 IPA。用户提供的是明文 WS，后续需要明确处理连接限制与语音传输安全，不能仅改默认 URL 或全局关闭安全策略。先前临时 SSH 密钥/known-hosts 文件当前不存在，未能核对新服务器日志；不要绕过主机验证或索取密钥明文。

最后核对：2026-10-05。仓库：`bboytang/Mia`，工作分支：`feature/mia-ios-bootstrap`。本文件记录跨设备继续开发所需的定位信息；当前进度和验收顺序以[完整方案与计划](mia-ios-roadmap.md)为准。备案期间的角色接入设计见[Live2D 运行时方案](mia-live2d-runtime-plan.md)。

**半身星雾 UI（已实现，CI 与两尺寸静态截图通过）**：用户最终恢复原版半身 Mia，批准[星雾首页](design/mia-approved-starmist-ui.png)，取消左上全部文字，以无麦克风图标的蓝紫粉流光球替换旧圆按钮和柱状波形。运行资源恢复 `MiaPortrait`，背景改为 `StarMistBackground`；原生 SwiftUI 流光按实际录音/播放音量变化，前景星雾与渐隐承接人物下沿。此前全身资产保留历史，不再用于当前首页或新视频默认参考。新末帧与提示词已同步，16 项视频工具测试通过。2026-10-05 用户确认另一次约 2.50 元 H3 5 秒 768P 生成，任务 `448953378521398` 成功；[带音效预览](design/launch/mia-starmist-preview-with-sound.mp4)与[抽帧](design/launch/mia-starmist-preview-contact.jpg)已保存。实际 768×1376、24 fps、5.167 秒，下沿持续星雾改善切口，但中途造型/尺度漂移和较亮凝形光带仍待验。原创音效按动作调整，视频帧与原片完全一致；实际账单、设备试听和原生首页交接未验。此为生成当时记录；用户随后选择静音视频接入，见下方最新状态。详见[制作记录](mia-launch-animation-plan.md)。

**静音启动版已选择接入**：用户取消音效并要求按静音版推送，现将[星雾静音视频](design/launch/mia-starmist-preview-silent.mp4)原样放入 `ios/MiaApp/MiaLaunch.mp4`。本地检查 H.264、768×1376、24 fps、124 帧、5.167 秒、无音轨，文件与预览哈希一致；播放器保持静音，未修改账号、语音或网关。CI 已加入真机包内资源一致性检查。[静音版 CI](https://github.com/bboytang/Mia/actions/runs/37250809373)（代码 `13dd7ce`）通过 49 项单元测试、2 项 UI 测试、模拟器与未签名真机编译、资源一致性检查；IPA 已上传。已下载核对 App 视频与源文件一致，并抽查 16 Pro/SE 实际录屏均有粒子、Mia 与回到首页。主录屏 177.15 秒、542 帧，SE 22.83 秒、443 帧，均无音轨；时长包含模拟器启动等待，不代表真机速度。结尾角色/流光球与原生布局有位置及尺度变化，未宣称像素级无缝；真机流畅度和衔接待验。音效候选保留制作历史，不再等待音效确认。

构建 `305a45d` 的 [iOS CI](https://github.com/bboytang/Mia/actions/runs/37213166341)通过 35 项测试、模拟器与未签名真机编译。已目视核对 CI 导出的 [16 Pro](design/verification/mia-starmist-16pro-preview.jpg)与 [SE 第三代](design/verification/mia-starmist-se-preview.jpg)首页缩略截图：设置处于安全区域，字幕卡两侧间距与圆角完整，流光球没有图标，人物下沿由星雾承接。真实麦克风音量反馈、播放时流光及打断仍待 iPhone 验收。

**账号接入（已实现、已部署，真机待验）**：按已批准的[用户名＋密码设计](mia-account-access-plan.md)和[实施计划](superpowers/plans/2026-10-04-mia-account-access.md)完成注册即登录、来源绑定 Keychain、退出撤销、过期重登录、每日额度与并发限制。新安装无需手填令牌；旧令牌只保留首次升级迁移和显式高级维护。独立审查发现的“会话到期后进入登录页仍录音”已补回归测试并修复。发布代码 `abe1ae4` 的 [iOS CI](https://github.com/bboytang/Mia/actions/runs/37246486540)通过 49 项单元测试（含真实 Keychain）和 2 项 UI 测试、两种构建、截图/录屏及未签名 IPA；[服务端 CI](https://github.com/bboytang/Mia/actions/runs/37246004648)通过 49 项测试。VPS 已部署同一服务端代码并重启，loopback 8765/8766、Caddy 账号路由、数据库 `0700/0600` 验证通过；本机 HTTP 与域名 HTTPS/WSS 均验证注册、登录、握手、退出、撤销后拒绝新回合，临时账号清理完成，没有调用云 API。外部 HTTPS 复测仍被重置，真实 iPhone 账号与语音尚未验收。

**MiniMax 预览已生成**：用户确认仅重试一次，直接传入两张原图的任务 `448781796409606` succeeded。原片为 768×1376、24 fps、约 5.17 秒、124 帧、含一条音轨；[静音预览](design/launch/mia-minimax-preview-silent.mp4)仅移除音轨，逐帧解码哈希与原片相同。已抽九帧检查：能看到粒子凝聚、侧身转向、V 手势与下方圆环，但侧向幅度大于原定约 35 度，角色尺度/服饰中途变化，约 2.5–3.5 秒人物下沿有明显水平截断。未验收为正式启动素材，未加入 iOS。实际费用待账户核对，未再提交任务。原片、静音版和[清理元数据](design/launch/mia-minimax-preview-metadata.json)已保存。

**新增启动动画工作**：用户确认[分镜方案](mia-launch-animation-plan.md)，并选择先用现有 40 积分生成 360p 动作预览。[第一条视频](design/launch/mia-launch-preview-source.mp4)已生成并解码检查：约 5.04 秒、24 fps、H.264、无音轨；中段发饰/服饰有偏差且带 OpenArt 水印，尚未作为正式 `MiaLaunch.mp4` 加入应用。启动播放器已接入，提交 `9295439` 的 [iOS CI](https://github.com/bboytang/Mia/actions/runs/37196200664)通过 32 项测试（含十项启动播放测试）、模拟器和真机编译；已检查 16 Pro 与 SE（第三代）录屏首末帧及首页截图。正式素材缺失时直接进入原首页，应用包不含测试视频。旧 CI 的录制就绪竞态已修复；新日志和两段录屏均证明先就绪、后启动，副录屏不再只有一帧。不得将预览、测试包的黑色视频或缺素材回退录屏写成动画成品通过。下一步先评审已生成的 MiniMax 预览及待修正画面，再验收合格素材与两种手机布局的衔接。

**MiniMax 接入进度**：用户要求接入中国平台 `MiniMax-H3`，已增加独立[离线生成工具](mia-minimax-video.md)，使用现有首尾帧、5 秒 768P，并按官方 V2 嵌套图片字段编码。Key 在交互终端隐藏写入仓库外 0600 文件，不影响火山语音配置。提交 `554c302` 的 [视频工具 CI](https://github.com/bboytang/Mia/actions/runs/37202954070)通过 14 项离线测试和请求准备；本地 98 项固件测试与 23 项服务端测试也通过。首次真实提交结果见上方记录。用户随后选定在当前 Codex 工作环境运行，不依赖 VPS SSH；`/root/projects/Mia` 工具、虚拟环境、离线请求和 MiniMax HTTPS 连通性已检查，短命令 `bash /tmp/mia-minimax-key` 已准备，无鉴权查询返回 HTTP 401。用户已隐藏设置 Key，文件权限 0600；配置后的不存在任务查询返回 HTTP 500／`server_error`。随后真实创建已受理但素材读取失败，内嵌图片重试已成功，质量待验收；不得宣称动画成品完成。

## 在另一台设备上开始

**启动视频当前交付方式**：已提供[首末帧与完整提示词交付包](design/launch/mia-launch-external-generation-brief.md)，用户随后要求直接接入 MiniMax H3，按上方结果先验收已生成预览的角色、真实旋身、指尖光弧、输出参数，再决定后续制作与首页衔接。录屏就绪修复 `9295439` 的 [CI](https://github.com/bboytang/Mia/actions/runs/37196200664)已成功；两台首帧为 iOS 桌面，末帧与各自原首页截图一致。主录屏约 154.01 秒、47 帧，包含很长的 `simctl launch` 等待；副录屏约 8.21 秒、67 帧。该时长不能用于推断真机启动速度，正式动画仍未收到。

在 Codex 中连接同一个 GitHub 仓库，选择 `feature/mia-ios-bootstrap` 分支；若使用终端，可执行：

```bash
git clone --branch feature/mia-ios-bootstrap https://github.com/bboytang/Mia.git
cd Mia
git status --short
```

把下面这段话发给新设备上的 Codex：

> 请在 `bboytang/Mia` 的 `feature/mia-ios-bootstrap` 分支继续 Mia iOS 项目。先读 `docs/mia-ios-handoff.md`、`docs/mia-ios-roadmap.md`、`docs/design/README.md`、`docs/live2d-mia-asset-brief.md`、`server/README.md` 和 `ios/README.md`，再核对 GitHub Actions 与工作区状态。已选角色造型和视觉参考已经固定在 `docs/design/`，不要重新猜测或替换。继续路线图中尚未验收的步骤；每完成一步更新进度、验证结果和阻塞条件并推送到 GitHub。不要把静态立绘当成真正 Live2D，也不要向我索取或提交密码、API Key、网关令牌。

如果新 Codex 默认打开仓库主分支，先切到上述工作分支。根目录 `AGENTS.md`主要描述原有 ESP-IDF 固件；iOS 应用和语音网关分别位于 `ios/`、`server/`。

## 不应丢失的既定决定

- **产品**：iPhone 独立中文语音聊天；按键开始/结束说话；只显示 Mia 的回答字幕，尽量随播放逐字出现，不显示用户 STT。
- **视觉**：角色仍为三款比较图**右侧第三款**紫发 Mia；用户最终批准半身星雾首页，左上无文字、下方无图标流光球、仅 Mia 字幕，齿轮设置保留。[最新参考](design/mia-approved-starmist-ui.png)取代全身/城市首页方向；原比较图和历史资产保留。
- **真正 Live2D**：最终必须接入 Cubism 绑定模型，并以 Mia 播放音量驱动 `ParamMouthOpenY`。[运行时接入方案](mia-live2d-runtime-plan.md)已整理，但没有接入 SDK 或模型。目前只有概念图和静态立绘，没有分层源稿、`.cmo3`、`.model3.json`、`.moc3` 或可用授权模型；用户也没有 Windows/Cubism 环境或已委托画师。此项是实际阻塞，不能用静态图、视频或模拟嘴形宣称完成。
- **云服务**：百炼方案已停止使用，迁往火山豆包流式 ASR 2.0 → 方舟 `doubao-seed-2-1-lite-260915` → Seed-TTS 2.0 双向 WebSocket。旧百炼 Provider 暂保留用于回滚；方舟与豆包语音分别使用一把 Key，不能混用。三条火山 API 已在中国 VPS 独立验证，火山新网关也已通过一次真实合成语音全链路验证。
- **VPS 与真机阻塞**：现用中国内地服务器 `43.143.230.174`，域名 `8kraw.cloud` 已解析至该地址。新 `mia-gateway` 和 Caddy 均运行，两把火山 Key 已在服务器配置，网关令牌未轮换。VPS 自身经公网域名完成真实 Opus → ASR → LLM → TTS → Opus 回合；该自测不代表外部网络可达。2026-10-04 iPhone 在 5G 与 Wi‑Fi 都报 TLS 连接失败，从另一外部环境访问 443 也在 TLS ClientHello 后被重置。用户称域名备案目前正在审核；审核及所需接入完成后，须从外部重验 TLS/WSS 和真机。证据见[路线图](mia-ios-roadmap.md)。
- **Apple**：用户没有付费 Apple Developer Program，但能自行重签 IPA。GitHub macOS runner 编译未签名 IPA；不把 TestFlight/App Store 当作当前交付途径。

## 当前代码与验证快照

| 模块 | 位置 | 已验证 | 未验证 |
| --- | --- | --- | --- |
| iOS SwiftUI 首页、设置、Keychain、麦克风、Opus、WebSocket、仅 Mia 字幕、启动播放准备 | `ios/MiaApp/`、`ios/MiaTests/` | 账号版 `abe1ae4` 的 [GitHub iOS 构建](https://github.com/bboytang/Mia/actions/runs/37246486540)通过 49 项单元测试、2 项 UI 测试、模拟器与未签名真机编译；已上传 IPA、SHA-256、两尺寸录屏与截图，核对账号页及两尺寸首页。此前 `9295439` 已检查录制顺序、首末帧和缺素材回退。 | 正式启动素材及动画衔接验收；用户重签后在真机上的录放、音量反馈、耳机切换、弱网与字幕时序。 |
| 小智兼容网关、火山 Provider、Opus | `server/xiaozhi_gateway.py`、`server/volcengine_provider.py`、`server/tests/` | 49 项服务端测试在本地、[CI](https://github.com/bboytang/Mia/actions/runs/37246004648)与 VPS 通过；账号会话与旧维护令牌回归通过。此前 VPS 自身真实云 API 回合返回 Mia 字幕与 91 帧 Opus；本次账号自测不调用云 API。百炼 Provider 保留回滚。 | 外部网络可达后，iPhone 真机录放、打断、连续多轮与弱网。 |
| Ubuntu 部署材料 | `server/deploy/`、`server/README.md` | 账号版网关/Caddy 已运行；VPS HTTP/HTTPS/WSS 账号自测、49 项服务端测试、配置/数据权限与原密钥保留已验。 | 外部 TLS 在 ClientHello 后被重置；用户称备案正在审核，审核和所需接入完成后须重验。 |
| 角色 | `docs/design/`、`ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/` | 已选概念图和静态图可在 GitHub 查看，模拟器首页已展示；[运行时方案](mia-live2d-runtime-plan.md)已整理。 | 真正 Cubism 模型制作、许可、SDK 接入和运行时口型。 |

**测试边界**：自动化服务端测试使用假提供者；真实网关回合使用既有 TTS 合成音频作为输入，并非 iPhone 麦克风。模拟器构建成功和服务器回合成功都不等于 iPhone 真机语音通过。GitHub Actions 产物有有效期，继续开发时用最新成功构建。

**最新部署快照（2026-10-05）**：运行代码 `abe1ae4c4f0fe5af6e8679855a8b15bf8e6c56d0`，标记在 `/opt/mia/DEPLOYED_COMMIT`。远端 `/home/ubuntu/Mia` 是源码快照，不是 Git checkout；使用该提交的受审查 git archive 发布。上线前备份为 `/var/backups/mia/before-accounts-abe1ae4c4f0f/`（root `0700`），包含旧 `server/`、`gateway.env`、systemd 服务及 Caddy 配置。部署前没有账号库；之后回滚必须保留 `/var/lib/mia/accounts.sqlite3`，不要以旧备份覆盖新用户数据。原环境文件字节前缀核对一致，Key、旧维护令牌及火山参数保持。安装器在独立 venv 增加 aiohttp，只补缺失的账号配置，Caddy 只增本域名 `/api/auth/*`；服务和 Caddy active，VPS 49 项测试与 pip check 通过。旧火山真实合成语音回合证据仍有效，但本次账号自测不调用付费 API，也不代表外部/iPhone 可达。

## 下一步顺序与交接所需信息

1. **恢复外部 TLS 访问后真机联调**：用户称 `8kraw.cloud` 的备案正在审核；审核和腾讯云所需接入完成后，先从外部检查 HTTPS/WSS，再用账号版 IPA 注册/登录检查中文识别、Mia 人声、仅 Mia 字幕、打断、连续多轮、弱网、耳机路由和费用。
2. **最后接入真正 Live2D**：运行时方案已定，收到符合[素材清单](live2d-mia-asset-brief.md)的获授权绑定模型和可合法使用的 SDK 后，按[接入方案](mia-live2d-runtime-plan.md)实施、验证，再替换静态图。没有模型文件时可继续语音、字幕与 UI 工作，但不能宣称 Live2D 完成。

每次交接或阶段完成时，更新[路线图](mia-ios-roadmap.md)中的状态、证据和下一步，保留 CI 运行链接，并确认 `git status` 没有遗漏的本地修改。这样即使更换设备或 Codex 会话，也能从仓库恢复同一事实状态。
