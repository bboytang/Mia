# Mia iOS

`ios/project.yml` 是 XcodeGen 工程定义。GitHub Actions 的 `Build iOS App` 工作流在 macOS runner 上生成 Xcode 工程，并分别编译模拟器和未签名的真机应用。

工作流上传 `Mia-unsigned.ipa`、`Mia.app` 和 SHA-256 校验文件。IPA **没有 Apple 签名，不能直接安装**；使用你自己的签名方式重签后才能安装到 iPhone。无需在仓库中保存签名证书或服务器密钥。

当前已加入小智 WebSocket 版本 1、Opus 编解码、麦克风采集与播放管线，以及仅展示 Mia 回答的字幕时间线。首页已按用户批准改用原半身 Mia 与星雾背景、无图标流光球；正式 Live2D 仍需分层绑定模型。默认服务端地址为 `wss://8kraw.cloud/xiaozhi/v1/`。现有鉴权仍使用设置页的网关令牌；用户新选的[用户名＋密码方案](../docs/mia-account-access-plan.md)待设计确认后接入，不能将它写成已能注册。服务器已通过真实合成语音回合，但外部 TLS 与 iPhone 联调尚未通过。

网关令牌保存在本机钥匙串，不写入仓库或普通偏好存储。完整进度、系统方案、验收标准和后续实施顺序见[项目路线图](../docs/mia-ios-roadmap.md)。

## 启动动画准备

已确认[约 5 秒的粒子 → Mia 旋身 → 首页方案](../docs/mia-launch-animation-plan.md)。当前[360p 动作预览](../docs/design/launch/mia-launch-preview-source.mp4)仍有中段造型偏差与 OpenArt 水印，没有作为正式 `MiaLaunch.mp4` 加入应用；素材缺失时直接进入原首页。

播放器通过本地静音 MP4 覆盖在同一首页实例上，冷启动播放一次；支持跳过、Reduce Motion、后台停止、失败回退和 7 秒上限，最后 0.25 秒按媒体播放时间淡出。它不发起联网、麦克风权限或音频会话。最终视频验收后放入 `ios/MiaApp/MiaLaunch.mp4`，由现有 XcodeGen 资源规则打包。

播放测试使用测试包内的 `MiaLaunchFixture.mp4`：16×16、2 秒、48 帧、无音轨的黑色视频，只验证 AVPlayer 生命周期和回退，不证明正式动画质量或资源已经打包。CI 将上传两台模拟器的启动录屏与首页截图；当前正式素材缺失，录屏用于核对回退。Swift/Xcode 在本地 Linux 环境不可用，编译和 XCTest 结果以新 GitHub CI 为准；真机流畅度及最终角色/圆环对齐仍待验。

## 半身星雾首页（2026-10-04）

用户最终恢复原半身形象，并批准星雾背景、取消左上文字、保留设置及字幕、用无图标流光球替换旧麦克风圆钮与柱状波形。`MiaPortrait` 与 `StarMistBackground` 分层展示，前景星雾和渐隐覆盖人物下沿；`MiaFullBody` 和城市资产保留历史。

流光使用原生 `TimelineView`/`Canvas`，上限 24 fps，后台暂停；Reduce Motion 时几何静止但亮度仍能反馈声音。录音输入每 60 ms PCM 帧计算 RMS，Mia 回答继续复用原播放音量；停止录音或断开时归零，旧播放回调不覆盖新聆听反馈。字幕推进和录音/Opus协议保持，点击仍可开始、结束及打断。新增 3 项 PCM 能量测试；编译、全套 XCTest 与 16 Pro/SE 截图待新 CI 核对，真机音量灵敏度待验。

新半身末帧与从下沿向上凝形的提示词已同步；用户要求的启动音效已有独立草稿，现有播放器仍静音。正式新版视频、音画对齐与播放策略尚未接入或验收；这次没有创建新收费任务。
