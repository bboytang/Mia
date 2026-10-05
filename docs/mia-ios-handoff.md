# Mia iOS 跨设备 Codex 交接

最后核对：2026-10-05。仓库：`bboytang/Mia`，工作分支：`feature/mia-ios-bootstrap`。本文件记录跨设备继续开发所需的定位信息；当前进度和验收顺序以[完整方案与计划](mia-ios-roadmap.md)为准。备案期间的角色接入设计见[Live2D 运行时方案](mia-live2d-runtime-plan.md)。

**半身星雾 UI（已实现，CI 与两尺寸静态截图通过）**：用户最终恢复原版半身 Mia，批准[星雾首页](design/mia-approved-starmist-ui.png)，取消左上全部文字，以无麦克风图标的蓝紫粉流光球替换旧圆按钮和柱状波形。运行资源恢复 `MiaPortrait`，背景改为 `StarMistBackground`；原生 SwiftUI 流光按实际录音/播放音量变化，前景星雾与渐隐承接人物下沿。此前全身资产保留历史，不再用于当前首页或新视频默认参考。新末帧与提示词已同步，16 项视频工具测试通过。2026-10-05 用户确认另一次约 2.50 元 H3 5 秒 768P 生成，任务 `448953378521398` 成功；[带音效预览](design/launch/mia-starmist-preview-with-sound.mp4)与[抽帧](design/launch/mia-starmist-preview-contact.jpg)已保存。实际 768×1376、24 fps、5.167 秒，下沿持续星雾改善切口，但中途造型/尺度漂移和较亮凝形光带仍待验。原创音效按动作调整，视频帧与原片完全一致；实际账单、设备试听和原生首页交接未验。此为生成当时记录；用户随后选择静音视频接入，见下方最新状态。详见[制作记录](mia-launch-animation-plan.md)。

**静音启动版已选择接入**：用户取消音效并要求按静音版推送，现将[星雾静音视频](design/launch/mia-starmist-preview-silent.mp4)原样放入 `ios/MiaApp/MiaLaunch.mp4`。本地检查 H.264、768×1376、24 fps、124 帧、5.167 秒、无音轨，文件与预览哈希一致；播放器保持静音，未修改账号、语音或网关。CI 新增真机包内视频与源文件一致性检查；新构建和两尺寸实际启动录屏待核对，真机衔接待验。音效候选保留制作历史，不再等待音效确认。

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
