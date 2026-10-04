# Mia iOS 跨设备 Codex 交接

最后核对：2026-10-03。仓库：`bboytang/Mia`，工作分支：`feature/mia-ios-bootstrap`。本文件记录跨设备继续开发所需的定位信息；当前进度和验收顺序以[完整方案与计划](mia-ios-roadmap.md)为准。最近一次代码、CI 和网络核对结果见路线图的“2026-10-03 继续开发核对”。

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
- **真正 Live2D**：最终必须接入 Cubism 绑定模型，并以 Mia 播放音量驱动 `ParamMouthOpenY`。目前只有概念图和静态立绘，没有分层源稿、`.cmo3`、`.model3.json`、`.moc3` 或可用授权模型；用户也没有 Windows/Cubism 环境或已委托画师。此项是实际阻塞，不能用静态图、视频或模拟嘴形宣称完成。
- **云服务**：百炼方案已停止使用，迁往火山豆包流式 ASR 2.0 → 方舟 `doubao-seed-2-1-lite-260915` → Seed-TTS 2.0 双向 WebSocket。旧百炼 Provider 暂保留用于回滚；方舟与豆包语音分别使用一把 Key，不能混用。三条火山 API 已在中国 VPS 独立验证，火山新网关也已通过一次真实合成语音全链路验证。
- **VPS**：现用中国内地服务器 `43.143.230.174`，域名 `8kraw.cloud` 已解析至该地址。专用公钥可登录 `ubuntu` 并使用 `sudo`；用户已在受保护环境文件中填写两把火山 Key 并重启，新 `mia-gateway` 和 Caddy 均运行。公网 WSS 完成真实 Opus → ASR → LLM → TTS → Opus 回合，错误令牌被拒绝。网关令牌未轮换。部署证据见[路线图](mia-ios-roadmap.md)。
- **Apple**：用户没有付费 Apple Developer Program，但能自行重签 IPA。GitHub macOS runner 编译未签名 IPA；不把 TestFlight/App Store 当作当前交付途径。

## 当前代码与验证快照

| 模块 | 位置 | 已验证 | 未验证 |
| --- | --- | --- | --- |
| iOS SwiftUI 首页、设置、Keychain、麦克风、Opus、WebSocket、仅 Mia 字幕 | `ios/MiaApp/`、`ios/MiaTests/` | [GitHub iOS 构建](https://github.com/bboytang/Mia/actions/runs/37089783261)通过模拟器测试、真机编译，上传 `Mia-unsigned.ipa`、SHA-256 与首页截图；已目视检查截图。 | 用户重签后在真机上的录放、耳机切换、弱网与字幕时序。 |
| 小智兼容网关、火山 Provider、Opus | `server/xiaozhi_gateway.py`、`server/volcengine_provider.py`、`server/tests/` | 23 项服务端测试在本地与 VPS 通过，[服务端 CI](https://github.com/bboytang/Mia/actions/runs/37150191264)通过；公网 WSS 经真实云 API 返回 Mia 字幕与 91 帧可解码 Opus。百炼 Provider 保留回滚。 | iPhone 真机录放、打断、连续多轮与弱网。 |
| Ubuntu 部署材料 | `server/deploy/`、`server/README.md` | 新进程和 Caddy 均运行；真实 WSS 全链路、错误令牌拒绝、受保护配置与令牌保留已验。 | 真机与长期稳定性。 |
| 角色 | `docs/design/`、`ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/` | 已选概念图和静态图可在 GitHub 查看，模拟器首页已展示。 | 真正 Cubism 模型制作、许可和运行时口型。 |

**测试边界**：自动化服务端测试使用假提供者；真实网关回合使用既有 TTS 合成音频作为输入，并非 iPhone 麦克风。模拟器构建成功和服务器回合成功都不等于 iPhone 真机语音通过。GitHub Actions 产物有有效期，继续开发时用最新成功构建。

**最新部署快照**：提交 `dcc3dbd` 已推送并通过服务端 CI；用户已在 VPS 填写两把火山 Key 并重启。新进程完成一次公网 WSS 真实回合：约 3.6 秒合成语音输入，返回 `start → sentence_start → stop`、91 帧 Opus（解码后 262080 字节 PCM），全程约 10.6 秒；错误令牌收到 WebSocket 1008。服务与 Caddy 验证后仍运行。Key 未进入仓库或聊天，网关令牌未改变。部署前代码与环境文件备份为 `/opt/mia/server.before-volc-dcc3dbd`、`/etc/mia/gateway.env.before-volc-dcc3dbd`。

## 下一步顺序与交接所需信息

1. **真机语音联调**：用户从最新 GitHub 构建取得未签名 IPA，自行重签安装，设置已有网关令牌。检查中文识别、Mia 人声、仅 Mia 字幕、打断、连续多轮、弱网、耳机路由和费用；根据具体失败修复。
2. **最后接入真正 Live2D**：收到符合[素材清单](live2d-mia-asset-brief.md)的获授权绑定模型后，接入 Cubism SDK，替换静态图并用播放音量驱动嘴部。没有模型文件时可继续语音、字幕与 UI 工作，但不能宣称 Live2D 完成。

每次交接或阶段完成时，更新[路线图](mia-ios-roadmap.md)中的状态、证据和下一步，保留 CI 运行链接，并确认 `git status` 没有遗漏的本地修改。这样即使更换设备或 Codex 会话，也能从仓库恢复同一事实状态。
