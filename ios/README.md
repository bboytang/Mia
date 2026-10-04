# Mia iOS

`ios/project.yml` 是 XcodeGen 工程定义。GitHub Actions 的 `Build iOS App` 工作流在 macOS runner 上生成 Xcode 工程，并分别编译模拟器和未签名的真机应用。

工作流上传 `Mia-unsigned.ipa`、`Mia.app` 和 SHA-256 校验文件。IPA **没有 Apple 签名，不能直接安装**；使用你自己的签名方式重签后才能安装到 iPhone。无需在仓库中保存签名证书或服务器密钥。

当前已加入小智 WebSocket 版本 1、Opus 编解码、麦克风采集与播放管线，以及仅展示 Mia 回答的字幕时间线。首页使用原创未来都市背景和 Mia 静态概念立绘；正式 Live2D 仍需分层绑定模型。默认服务端地址为 `wss://8kraw.cloud/xiaozhi/v1/`，首次点击麦克风会引导先在设置中填写网关令牌。链路尚未在真实服务端和 iPhone 上联调，当前不能承诺稳定语音聊天。

网关令牌保存在本机钥匙串，不写入仓库或普通偏好存储。完整进度、系统方案、验收标准和后续实施顺序见[项目路线图](../docs/mia-ios-roadmap.md)。

## 启动动画准备

已确认[约 5 秒的粒子 → Mia 旋身 → 首页方案](../docs/mia-launch-animation-plan.md)。当前[360p 动作预览](../docs/design/launch/mia-launch-preview-source.mp4)仍有中段造型偏差与 OpenArt 水印，没有作为正式 `MiaLaunch.mp4` 加入应用；素材缺失时直接进入原首页。

播放器通过本地静音 MP4 覆盖在同一首页实例上，冷启动播放一次；支持跳过、Reduce Motion、后台停止、失败回退和 7 秒上限，最后 0.25 秒按媒体播放时间淡出。它不发起联网、麦克风权限或音频会话。最终视频验收后放入 `ios/MiaApp/MiaLaunch.mp4`，由现有 XcodeGen 资源规则打包。

播放测试使用测试包内的 `MiaLaunchFixture.mp4`：16×16、2 秒、48 帧、无音轨的黑色视频，只验证 AVPlayer 生命周期和回退，不证明正式动画质量或资源已经打包。CI 将上传两台模拟器的启动录屏与首页截图；当前正式素材缺失，录屏用于核对回退。Swift/Xcode 在本地 Linux 环境不可用，编译和 XCTest 结果以新 GitHub CI 为准；真机流畅度及最终角色/圆环对齐仍待验。

## 全身首页调整（2026-10-04）

用户要求头到脚全身可见，已新增 `MiaFullBody` 透明立绘，优化腿型与身形，保留原 V 手势和伸手姿态。首页角色在标题与字幕板之间按实际空间 `scaledToFit`，不再与下方控件叠放。原 `MiaPortrait` 保留参考，语音会话和字幕推进代码未改。编译、原有测试及 16 Pro/SE 两种尺寸截图待本次 GitHub CI 核对；仍是静态角色，不代表 Live2D 完成。

用户另要求启动音效，正在准备独立短音效与全身动画参考；现有播放器仍静音，正式含音效启动资源和播放策略尚未接入或验收。
