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
- **云服务**：阿里云百炼北京地域，已开通并有 Key；默认 `qwen3-asr-flash`、`qwen-plus`、`qwen3-tts-flash` 与 Cherry 音色。Key 从未提交到仓库。不要回退到 OpenAI 方案。
- **VPS**：现用中国内地服务器 `43.143.230.174`，域名 `8kraw.cloud` 已解析至该地址。专用公钥可登录 `ubuntu` 并使用 `sudo`；Caddy TLS、`mia-gateway` 运行和外网 WSS 令牌握手均已验证。网关依赖和源码已安装，VPS 上 9 项服务端测试通过。当前 Key 对北京百炼真实请求返回 `401 invalid_api_key`，需用户获取可用于北京地域按量付费接口的新 Key；网关令牌已生成，更新 Key 时应保留该令牌。部署进度见[路线图](mia-ios-roadmap.md)。
- **Apple**：用户没有付费 Apple Developer Program，但能自行重签 IPA。GitHub macOS runner 编译未签名 IPA；不把 TestFlight/App Store 当作当前交付途径。

## 当前代码与验证快照

| 模块 | 位置 | 已验证 | 未验证 |
| --- | --- | --- | --- |
| iOS SwiftUI 首页、设置、Keychain、麦克风、Opus、WebSocket、仅 Mia 字幕 | `ios/MiaApp/`、`ios/MiaTests/` | [GitHub iOS 构建](https://github.com/bboytang/Mia/actions/runs/37089783261)通过模拟器测试、真机编译，上传 `Mia-unsigned.ipa`、SHA-256 与首页截图；已目视检查截图。 | 用户重签后在真机上的录放、耳机切换、弱网与字幕时序。 |
| 小智兼容网关、百炼 ASR/LLM/TTS、Opus | `server/xiaozhi_gateway.py`、`server/bailian_provider.py`、`server/tests/` | 9 项本地服务端测试及[GitHub 服务端 CI](https://github.com/bboytang/Mia/actions/runs/37089492807)通过。 | 真正百炼 API 响应、费用、延迟和 VPS 运行。 |
| Ubuntu 部署材料 | `server/deploy/`、`server/README.md` | 安装脚本语法通过；新 VPS 的依赖、Caddy TLS、`mia-gateway` 和外网 WSS 令牌握手已验证。 | 当前 Key 的真实百炼调用返回 `401 invalid_api_key`，需替换并重验。 |
| 角色 | `docs/design/`、`ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/` | 已选概念图和静态图可在 GitHub 查看，模拟器首页已展示。 | 真正 Cubism 模型制作、许可和运行时口型。 |

**测试边界**：自动化服务端测试使用假提供者；VPS 上对真实百炼的最小对话请求返回 `401 invalid_api_key`，ASR/TTS 尚未验证。模拟器构建成功不等于 iPhone 真机语音通过。GitHub Actions 产物有有效期，继续开发时用最新成功构建，不要依赖这里的旧 artifact ID。

## 下一步顺序与交接所需信息

1. **修复百炼鉴权**：Caddy、`mia-gateway` 与 WSS 令牌握手已通过。重置 Key 和另一条全新“全部”权限 Key 在共享与业务空间专属地址均返回 `401 invalid_api_key`；Request ID 见路线图。用户需凭这些 ID 向阿里云百炼支持核查账号/业务空间鉴权状态。现有 VPS 的 `sudo mia-update-key` 会先验证新 Key，成功后仅替换 Key 并保留网关令牌；此前的 401 未修改配置。不要把 Key 或令牌发到聊天或工单；鉴权通过后再验真实语音和域名备案与接入要求。
2. **再做真机语音联调**：用户从最新 GitHub 构建取得未签名 IPA，自行重签安装，设置网关令牌。检查中文识别、Mia 人声、仅 Mia 字幕、打断、连续多轮、弱网、耳机路由和费用；根据具体失败修复。
3. **最后接入真正 Live2D**：收到符合[素材清单](live2d-mia-asset-brief.md)的获授权绑定模型后，接入 Cubism SDK，替换静态图并用播放音量驱动嘴部。没有模型文件时可继续语音、字幕与 UI 工作，但不能宣称 Live2D 完成。

每次交接或阶段完成时，更新[路线图](mia-ios-roadmap.md)中的状态、证据和下一步，保留 CI 运行链接，并确认 `git status` 没有遗漏的本地修改。这样即使更换设备或 Codex 会话，也能从仓库恢复同一事实状态。
