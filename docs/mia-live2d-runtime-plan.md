# Mia iOS Live2D 运行时接入方案

状态：**方案已确定，尚未接入 SDK 或模型**。2026-10-04 在域名 ICP 备案审核期间整理；正式实施须先取得可随应用分发的 Mia 绑定模型及获许可的 Cubism SDK。角色造型沿用[三款对比图右侧第三款](design/README.md)，素材要求见[交付说明](live2d-mia-asset-brief.md)。

## 接入边界

- 使用官方稳定版 **Cubism 5 SDK for Native R5** 的 iOS Metal 路线，不引入 Unity 或 WebView。现有 SwiftUI 首页、城市背景、字幕板、麦克风操作与小智 WebSocket/Opus 链路保持原样。
- 仅将 `ContentView` 中 `MiaPortrait` 所在的角色区域替换为 SwiftUI `UIViewRepresentable` 包装的 `MTKView`。由薄 Objective-C++ 桥接层持有 Cubism Framework/Core、Metal 渲染器与模型生命周期；Swift 只传角色状态及 `0...1` 的嘴部音量。渲染层不访问网络、令牌或用户识别文本。
- 从应用资源中的 `.model3.json` 加载模型，按其中的相对路径读取 `.moc3`、贴图、动作和表情。运行前核对文件完整性、iOS 构建包含资源、模型分发授权及 SDK 使用条款；缺文件或加载失败时保留现有静态立绘并记录可诊断错误，不把回退画面标为 Live2D 已运行。
- 先用官方 Native Metal 示例验证 SDK 与模型在项目的 iOS 17+、arm64 构建中可用，再接入 Mia 首页。官方 GitHub 仓库不包含专有 Cubism Core；不得仅凭克隆示例仓库宣称已可编译，也不得在授权未确认前提交 SDK Core 或第三方示例模型。

## 会话状态与口型

`MiaVoiceSession` 保留现有协议状态及字幕时间线，另向角色视图提供视觉状态 `idle / listening / thinking / speaking`。连接前和空闲时为 `idle`；开始采集后为 `listening`；结束采集、等待回答期间为 `thinking`；收到 `ttsStart` 后为 `speaking`；回答播完、服务端出错或断开后回到 `idle`。打断回答后立即清零嘴部音量并切至 `listening`。状态只选择模型已有的表情或动作，不改变网关消息。

口型取自**正在输出的 Mia 音频**，不取麦克风或收到但尚未播放的 Opus 数据。现有 `MiaAudioIO.play()` 在排队 PCM 时计算整块 RMS，却要等 `.dataPlayedBack` 才回调；该回调继续用于字幕推进和播放完成判定。接入时在 `AVAudioPlayerNode` 输出总线安装音频 tap，按实际渲染缓冲计算 RMS，仅传标量，合并到约每秒 30 次主线程更新；停止音频引擎时移除 tap。将音量映射并限制在 `0...1`，仅在 `speaking` 时用于口型；静音、打断、停止、错误和断线时立即置零。首版映射增益按真机播放音量校准，不用字幕进度反推嘴形，也不宣称音素级同步。

渲染循环按官方 Framework 的模型更新顺序应用动作、表情、眨眼、呼吸和物理，再将平滑后的播放音量写入模型 `LipSync` 组中的 `ParamMouthOpenY`，最后更新和绘制模型。使用 R5 的 `CubismUpdateScheduler`/官方 Native 示例顺序，避免动作或物理覆盖口型。模型必须实际提供该参数及连续的闭合到张开形变；若缺失，验收失败，不能以 UI 动画代替。

## 实施与验收顺序

1. **素材与许可**：取得[素材清单](live2d-mia-asset-brief.md)中的源稿、Cubism 工程、完整运行文件及可随 IPA 分发的书面授权；由项目所有者接受 SDK 条款，确定 SDK/Core 在仓库与 CI 中的合法获取方式。未满足前不引入二进制或替换静态角色。
2. **模型与渲染**：先在官方示例中加载正式 Mia 模型，再在 XcodeGen 工程中接入桥接层、Metal 视图和资源。模拟器构建及未签名真机 IPA 构建都通过；真机检查透明背景、构图、眨眼、动作及缺文件时的静态回退。
3. **播放驱动**：给音量归一化、静音/打断归零和视觉状态转换增加小范围单元测试；保留并运行现有 Opus、字幕和 WebSocket 测试。用获授权的预录 Mia PCM 离线验证口型随输出音频变化，字幕仍按 `.dataPlayedBack` 推进，麦克风噪声不会张嘴。
4. **真机验收**：检查连续语音回合、打断、前后台恢复及音频路由切换；记录实际帧率、峰值内存和发热观察，不用模拟器结果替代 iPhone 结论。外部 TLS 恢复后，再与真实 VPS/WSS 语音链路联调。

完成上述真机检查且正式模型确已渲染和随 Mia 播放张嘴，才将路线图的“Live2D 接入”标记完成。备案审核期间只交付本方案及进度记录。

## 依据

- Live2D：[Native 平台支持](https://docs.live2d.com/en/cubism-sdk-manual/platform/)、[SDK 下载](https://www.live2d.com/en/sdk/download/native/)、[Native Core 分发说明](https://docs.live2d.com/en/cubism-sdk-manual/cubism-sdk-for-native/)、[模型加载](https://docs.live2d.com/en/cubism-sdk-manual/model/)、[口型同步](https://docs.live2d.com/en/cubism-sdk-manual/lipsync/)、[R5 更新顺序](https://docs.live2d.com/en/cubism-sdk-manual/model-param-updater/)。
- Apple：[音频节点 tap](https://developer.apple.com/documentation/avfaudio/avaudionode)、[`.dataPlayedBack` 回调时机](https://developer.apple.com/documentation/avfaudio/avaudioplayernodecompletioncallbacktype/dataplayedback)。
