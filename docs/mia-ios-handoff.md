# Mia iOS 跨设备 Codex 交接

最后核对：2026-10-04。仓库：`bboytang/Mia`，工作分支：`feature/mia-ios-bootstrap`。本文件记录跨设备继续开发所需的定位信息；当前进度和验收顺序以[完整方案与计划](mia-ios-roadmap.md)为准。备案期间的角色接入设计见[Live2D 运行时方案](mia-live2d-runtime-plan.md)。

**新增启动动画工作**：用户确认[分镜方案](mia-launch-animation-plan.md)，并选择先用现有 40 积分生成 360p 动作预览。[第一条视频](design/launch/mia-launch-preview-source.mp4)已生成并解码检查：约 5.04 秒、24 fps、H.264、无音轨；中段发饰/服饰有偏差且带 OpenArt 水印，尚未作为正式 `MiaLaunch.mp4` 加入应用。启动播放器已接入，提交 `b7269de` 的 [iOS CI](https://github.com/bboytang/Mia/actions/runs/37194380347)通过 32 项测试（含十项启动播放测试）、模拟器和真机编译；已检查 16 Pro 与 SE（第三代）首页截图。正式素材缺失时直接进入原首页，应用包不含测试视频。CI 录屏时长/帧数异常，SE 录制就绪晚于应用启动，不能用于启动过程验收；正式素材接入前须等待录制就绪后重验。不得将预览、测试包的黑色视频或回退截图写成动画成品通过。下一步先取得用户动作反馈、修正一致性并确认无水印导出条件，再验收素材和两种手机布局的衔接。

## 在另一台设备上开始

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
- **视觉**：用户在三款角色比较图中选定**右侧第三款**紫发 Mia 和蓝紫未来都市；比较图、最终概念图、背景、字幕板、声波及麦克风参考均在[视觉参考目录](design/README.md)。功能入口的具体种类和位置尚未最终定稿。
- **真正 Live2D**：最终必须接入 Cubism 绑定模型，并以 Mia 播放音量驱动 `ParamMouthOpenY`。[运行时接入方案](mia-live2d-runtime-plan.md)已整理，但没有接入 SDK 或模型。目前只有概念图和静态立绘，没有分层源稿、`.cmo3`、`.model3.json`、`.moc3` 或可用授权模型；用户也没有 Windows/Cubism 环境或已委托画师。此项是实际阻塞，不能用静态图、视频或模拟嘴形宣称完成。
- **云服务**：百炼方案已停止使用，迁往火山豆包流式 ASR 2.0 → 方舟 `doubao-seed-2-1-lite-260915` → Seed-TTS 2.0 双向 WebSocket。旧百炼 Provider 暂保留用于回滚；方舟与豆包语音分别使用一把 Key，不能混用。三条火山 API 已在中国 VPS 独立验证，火山新网关也已通过一次真实合成语音全链路验证。
- **VPS 与真机阻塞**：现用中国内地服务器 `43.143.230.174`，域名 `8kraw.cloud` 已解析至该地址。新 `mia-gateway` 和 Caddy 均运行，两把火山 Key 已在服务器配置，网关令牌未轮换。VPS 自身经公网域名完成真实 Opus → ASR → LLM → TTS → Opus 回合；该自测不代表外部网络可达。2026-10-04 iPhone 在 5G 与 Wi‑Fi 都报 TLS 连接失败，从另一外部环境访问 443 也在 TLS ClientHello 后被重置。用户称域名备案目前正在审核；审核及所需接入完成后，须从外部重验 TLS/WSS 和真机。证据见[路线图](mia-ios-roadmap.md)。
- **Apple**：用户没有付费 Apple Developer Program，但能自行重签 IPA。GitHub macOS runner 编译未签名 IPA；不把 TestFlight/App Store 当作当前交付途径。

## 当前代码与验证快照

| 模块 | 位置 | 已验证 | 未验证 |
| --- | --- | --- | --- |
| iOS SwiftUI 首页、设置、Keychain、麦克风、Opus、WebSocket、仅 Mia 字幕、启动播放准备 | `ios/MiaApp/`、`ios/MiaTests/` | [GitHub iOS 构建](https://github.com/bboytang/Mia/actions/runs/37194380347)通过 32 项测试、模拟器与真机编译，上传未签名 IPA、SHA-256 与两种尺寸截图；已检查截图及应用包。 | 正式启动素材及录屏验收；用户重签后在真机上的录放、耳机切换、弱网与字幕时序。 |
| 小智兼容网关、火山 Provider、Opus | `server/xiaozhi_gateway.py`、`server/volcengine_provider.py`、`server/tests/` | 23 项服务端测试在本地与 VPS 通过，[服务端 CI](https://github.com/bboytang/Mia/actions/runs/37150191264)通过；VPS 自身经公网域名调用真实云 API，返回 Mia 字幕与 91 帧可解码 Opus。百炼 Provider 保留回滚。 | 外部网络可达后，iPhone 真机录放、打断、连续多轮与弱网。 |
| Ubuntu 部署材料 | `server/deploy/`、`server/README.md` | 新进程和 Caddy 均运行；VPS 自测真实 WSS 全链路、错误令牌拒绝、受保护配置与令牌保留已验。 | 外部 TLS 在 ClientHello 后被重置；用户称备案正在审核，审核和所需接入完成后须重验。 |
| 角色 | `docs/design/`、`ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/` | 已选概念图和静态图可在 GitHub 查看，模拟器首页已展示；[运行时方案](mia-live2d-runtime-plan.md)已整理。 | 真正 Cubism 模型制作、许可、SDK 接入和运行时口型。 |

**测试边界**：自动化服务端测试使用假提供者；真实网关回合使用既有 TTS 合成音频作为输入，并非 iPhone 麦克风。模拟器构建成功和服务器回合成功都不等于 iPhone 真机语音通过。GitHub Actions 产物有有效期，继续开发时用最新成功构建。

**最新部署快照**：提交 `dcc3dbd` 已推送并通过服务端 CI；用户已在 VPS 填写两把火山 Key 并重启。VPS 自身访问公网域名完成一次真实回合：约 3.6 秒合成语音输入，返回 `start → sentence_start → stop`、91 帧 Opus（解码后 262080 字节 PCM），全程约 10.6 秒；错误令牌收到 WebSocket 1008。服务与 Caddy 验证后仍运行。Key 未进入仓库或聊天，网关令牌未改变。部署前代码与环境文件备份为 `/opt/mia/server.before-volc-dcc3dbd`、`/etc/mia/gateway.env.before-volc-dcc3dbd`。

## 下一步顺序与交接所需信息

1. **恢复外部 TLS 访问后真机联调**：用户称 `8kraw.cloud` 的备案正在审核；审核和腾讯云所需接入完成后，先从外部检查 HTTPS/WSS，再用已安装的 IPA 和已有网关令牌检查中文识别、Mia 人声、仅 Mia 字幕、打断、连续多轮、弱网、耳机路由和费用。
2. **最后接入真正 Live2D**：运行时方案已定，收到符合[素材清单](live2d-mia-asset-brief.md)的获授权绑定模型和可合法使用的 SDK 后，按[接入方案](mia-live2d-runtime-plan.md)实施、验证，再替换静态图。没有模型文件时可继续语音、字幕与 UI 工作，但不能宣称 Live2D 完成。

每次交接或阶段完成时，更新[路线图](mia-ios-roadmap.md)中的状态、证据和下一步，保留 CI 运行链接，并确认 `git status` 没有遗漏的本地修改。这样即使更换设备或 Codex 会话，也能从仓库恢复同一事实状态。
