# Mia 正式 Live2D 素材交付说明

## 角色参考

以 `ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png` 为造型参考：紫色短发、紫瞳、黑紫未来街头服饰、晶体发饰，面向镜头，友好而有活力。当前图片是单张静态概念立绘，不能直接作为 Live2D 模型。正式立绘需要重新绘制分层、补画遮挡部分，并在 Cubism Editor 中绑定。

## 必需交付物

- 可用于 Mia iOS 应用的明确授权，包含应用内展示、随 IPA 分发和必要的美术修改。
- 分层源文件（PSD 或 Clip Studio 文件），至少分离脸型、前后发、眉、眼白、虹膜、眼睑、上下唇、口腔、牙齿、舌、颈、身体、衣服和前后手臂。头发及衣服需补画转动后会露出的部分。
- Cubism 工程 `.cmo3`、运行文件 `.model3.json`、`.moc3`、贴图图集、表情和动作文件。素材路径应相对 `.model3.json`，文件名仅用英文和数字。
- 至少包含 `ParamAngleX/Y/Z`、`ParamEyeLOpen`、`ParamEyeROpen`、`ParamMouthOpenY`、`ParamMouthForm`、`ParamBreath` 以及头发和身体摆动参数。嘴部开合应从闭嘴到张嘴连续、自然地变化，供语音播放音量驱动。
- 提供静音待机、聆听、思考、说话四种状态的表情或动作组合；屏幕竖向半身构图，不挡字幕与麦克风。

## 验收

用 Cubism Viewer 或 Editor 打开 `.model3.json`，确认文件不缺失、无明显裁切；在 iPhone 上验证眨眼、转头、呼吸、动作、中断恢复和按 TTS 音量驱动的嘴部开合。目标为常见 iPhone 上流畅运行，并检查内存与发热。没有 `.moc3` 时，客户端不能称为真正 Live2D。

当前仓库中的概念立绘和背景可继续用于联调，但它们不满足以上分层绑定交付。取得正式模型后，把文件放入 iOS 资源目录，再接入 Cubism SDK 并替换静态立绘。
