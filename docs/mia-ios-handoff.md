# Mia iOS 跨设备 Codex 交接

最后核对：2026-10-04。仓库：`bboytang/Mia`，工作分支：`feature/mia-ios-bootstrap`。本文件记录跨设备继续开发所需的定位信息；当前进度和验收顺序以[完整方案与计划](mia-ios-roadmap.md)为准。备案期间的角色接入设计见[Live2D 运行时方案](mia-live2d-runtime-plan.md)。

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
- **视觉**：用户在三款角色比较图中选定**右侧第三款**紫发 Mia 和蓝紫未来都市；比较图、最终概念图、背景、字幕板、声波及麦克风参考均在[视觉参考目录](design/README.md)。功能入口的具体种类和位置尚未最终定稿。
- **真正 Live2D**：最终必须接入 Cubism 绑定模型，并以 Mia 播放音量驱动 `ParamMouthOpenY`。[运行时接入方案](mia-live2d-runtime-plan.md)已整理，但没有接入 SDK 或模型。目前只有概念图和静态立绘，没有分层源稿、`.cmo3`、`.model3.json`、`.moc3` 或可用授权模型；用户也没有 Windows/Cubism 环境或已委托画师。此项是实际阻塞，不能用静态图、视频或模拟嘴形宣称完成。
- **云服务**：百炼方案已停止使用，迁往火山豆包流式 ASR 2.0 → 方舟 `doubao-seed-2-1-lite-260915` → Seed-TTS 2.0 双向 WebSocket。旧百炼 Provider 暂保留用于回滚；方舟与豆包语音分别使用一把 Key，不能混用。三条火山 API 已在中国 VPS 独立验证，火山新网关也已通过一次真实合成语音全链路验证。
- **VPS 与真机阻塞**：现用中国内地服务器 `43.143.230.174`，域名 `8kraw.cloud` 已解析至该地址。新 `mia-gateway` 和 Caddy 均运行，两把火山 Key 已在服务器配置，网关令牌未轮换。VPS 自身经公网域名完成真实 Opus → ASR → LLM → TTS → Opus 回合；该自测不代表外部网络可达。2026-10-04 iPhone 在 5G 与 Wi‑Fi 都报 TLS 连接失败，从另一外部环境访问 443 也在 TLS ClientHello 后被重置。用户称域名备案目前正在审核；审核及所需接入完成后，须从外部重验 TLS/WSS 和真机。证据见[路线图](mia-ios-roadmap.md)。
- **Apple**：用户没有付费 Apple Developer Program，但能自行重签 IPA。GitHub macOS runner 编译未签名 IPA；不把 TestFlight/App Store 当作当前交付途径。

## 当前代码与验证快照

| 模块 | 位置 | 已验证 | 未验证 |
| --- | --- | --- | --- |
| iOS SwiftUI 首页、设置、Keychain、麦克风、Opus、WebSocket、仅 Mia 字幕、启动播放准备 | `ios/MiaApp/`、`ios/MiaTests/` | [GitHub iOS 构建](https://github.com/bboytang/Mia/actions/runs/37196200664)通过 32 项测试、模拟器与真机编译，上传未签名 IPA、SHA-256、两种尺寸录屏与截图；已检查录制顺序、首末帧、截图及应用包。 | 正式启动素材及动画衔接验收；用户重签后在真机上的录放、耳机切换、弱网与字幕时序。 |
| 小智兼容网关、火山 Provider、Opus | `server/xiaozhi_gateway.py`、`server/volcengine_provider.py`、`server/tests/` | 23 项服务端测试在本地与 VPS 通过，[服务端 CI](https://github.com/bboytang/Mia/actions/runs/37150191264)通过；VPS 自身经公网域名调用真实云 API，返回 Mia 字幕与 91 帧可解码 Opus。百炼 Provider 保留回滚。 | 外部网络可达后，iPhone 真机录放、打断、连续多轮与弱网。 |
| Ubuntu 部署材料 | `server/deploy/`、`server/README.md` | 新进程和 Caddy 均运行；VPS 自测真实 WSS 全链路、错误令牌拒绝、受保护配置与令牌保留已验。 | 外部 TLS 在 ClientHello 后被重置；用户称备案正在审核，审核和所需接入完成后须重验。 |
| 角色 | `docs/design/`、`ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/` | 已选概念图和静态图可在 GitHub 查看，模拟器首页已展示；[运行时方案](mia-live2d-runtime-plan.md)已整理。 | 真正 Cubism 模型制作、许可、SDK 接入和运行时口型。 |

**测试边界**：自动化服务端测试使用假提供者；真实网关回合使用既有 TTS 合成音频作为输入，并非 iPhone 麦克风。模拟器构建成功和服务器回合成功都不等于 iPhone 真机语音通过。GitHub Actions 产物有有效期，继续开发时用最新成功构建。

**最新部署快照**：提交 `dcc3dbd` 已推送并通过服务端 CI；用户已在 VPS 填写两把火山 Key 并重启。VPS 自身访问公网域名完成一次真实回合：约 3.6 秒合成语音输入，返回 `start → sentence_start → stop`、91 帧 Opus（解码后 262080 字节 PCM），全程约 10.6 秒；错误令牌收到 WebSocket 1008。服务与 Caddy 验证后仍运行。Key 未进入仓库或聊天，网关令牌未改变。部署前代码与环境文件备份为 `/opt/mia/server.before-volc-dcc3dbd`、`/etc/mia/gateway.env.before-volc-dcc3dbd`。

## 下一步顺序与交接所需信息

1. **恢复外部 TLS 访问后真机联调**：用户称 `8kraw.cloud` 的备案正在审核；审核和腾讯云所需接入完成后，先从外部检查 HTTPS/WSS，再用已安装的 IPA 和已有网关令牌检查中文识别、Mia 人声、仅 Mia 字幕、打断、连续多轮、弱网、耳机路由和费用。
2. **最后接入真正 Live2D**：运行时方案已定，收到符合[素材清单](live2d-mia-asset-brief.md)的获授权绑定模型和可合法使用的 SDK 后，按[接入方案](mia-live2d-runtime-plan.md)实施、验证，再替换静态图。没有模型文件时可继续语音、字幕与 UI 工作，但不能宣称 Live2D 完成。

每次交接或阶段完成时，更新[路线图](mia-ios-roadmap.md)中的状态、证据和下一步，保留 CI 运行链接，并确认 `git status` 没有遗漏的本地修改。这样即使更换设备或 Codex 会话，也能从仓库恢复同一事实状态。
