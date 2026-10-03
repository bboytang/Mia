# Mia iOS

`ios/project.yml` 是 XcodeGen 工程定义。GitHub Actions 的 `Build iOS App` 工作流在 macOS runner 上生成 Xcode 工程，并分别编译模拟器和未签名的真机应用。

工作流上传 `Mia-unsigned.ipa`、`Mia.app` 和 SHA-256 校验文件。IPA **没有 Apple 签名，不能直接安装**；使用你自己的签名方式重签后才能安装到 iPhone。无需在仓库中保存签名证书或服务器密钥。

当前已加入小智 WebSocket 版本 1、Opus 编解码、麦克风采集与播放管线，以及仅展示 Mia 语音的字幕时间线。首页使用原创未来都市背景，角色舞台预留给正式 Live2D 模型。填写服务端地址后，麦克风按钮尝试连接、开始/结束说话；这条链路尚未在真实服务端和 iPhone 上联调，当前不能承诺可稳定语音聊天。

服务端地址在设置中填写 `wss://` URL。可选访问令牌保存在本机钥匙串，不写入仓库或普通偏好存储。
