# Mia iOS

`ios/project.yml` 是 XcodeGen 工程定义。GitHub Actions 的 `Build iOS App` 工作流在 macOS runner 上生成 Xcode 工程，并分别编译模拟器和未签名的真机应用。

工作流上传 `Mia-unsigned.ipa`、`Mia.app` 和 SHA-256 校验文件。IPA **没有 Apple 签名，不能直接安装**；使用你自己的签名方式重签后才能安装到 iPhone。无需在仓库中保存签名证书或服务器密钥。

当前已加入小智 WebSocket 版本 1 的消息解析、连接适配器和仅展示 Mia 语音的字幕时间线。首页使用原创未来都市背景，角色舞台预留给正式 Live2D 模型。麦克风按钮目前打开服务端设置；录音、Opus 编解码、实际语音播放和 Live2D 模型尚未接通，当前 IPA 不能用于语音聊天。

服务端地址在设置中填写 `wss://` URL。未来的鉴权凭据不能写入仓库或普通偏好存储；音频连接阶段将使用系统安全存储。
