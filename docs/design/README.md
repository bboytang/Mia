# Mia 已确定的视觉参考

下面的图片已纳入 GitHub，供其他设备上的 Codex、画师和绑定师查看。请以图片本身作为角色与画面风格的首要参考。2026-10-04 用户最终批准下列星雾半身首页；此前全身与城市版本保留历史，不能混用为当前动画参考。

| 文件 | 用途 |
| --- | --- |
| [最新批准星雾首页](mia-approved-starmist-ui.png) | 当前视觉依据：原半身 Mia、无左上文字、星雾承接下沿、蓝紫粉无图标流光球、仅 Mia 字幕及设置。静态设计稿，不是精确原生截图。 |
| [16 Pro 原生首页缩略截图](verification/mia-starmist-16pro-preview.jpg)、[SE 第三代原生首页缩略截图](verification/mia-starmist-se-preview.jpg) | 构建 `305a45d` 的 CI 导出 JPEG，最长边 600px；已目视检查控件间距、安全区域和下沿融合，不是用户真机截图或语音反馈验证。完整 PNG、录屏与未签名 IPA 见 [CI 产物](https://github.com/bboytang/Mia/actions/runs/37213166341)。 |
| [星雾闭场参考](launch/mia-halfbody-starmist-end-reference.png) | 与最新设计同一身份/背景/流光球，去掉字幕文字和设置等 UI，用于新视频默认末帧。永久前景雾覆盖下沿；不是视频成品或所有设备的精确布局。 |
| [新版星雾带音效预览](launch/mia-starmist-preview-with-sound.mp4) | 2026-10-05 单次确认后生成，768×1376、24 fps、5.167 秒；原创音效按动作调整并替换平台音轨。下沿雾改善切口，中途造型/尺度和凝形光带仍待验，未加入 App。[静音版](launch/mia-starmist-preview-silent.mp4)、[抽帧](launch/mia-starmist-preview-contact.jpg)、[元数据](launch/mia-starmist-preview-metadata.json)。 |
| [科幻启动音效独立预览](launch/mia-scifi-sound-v2-preview.mp3) | 历史候选：用户随后取消音效，选择静音视频推送；此音效不合成、不打包到 App。[WAV](launch/mia-scifi-sound-v2-preview.wav)、[参数](launch/mia-scifi-sound-v2-preview.json)。 |
| [当前静音启动视频](launch/mia-starmist-preview-silent.mp4) | 用户已选择采用，原样接入 `ios/MiaApp/MiaLaunch.mp4`；H.264、768×1376、24 fps、5.167 秒、无音轨。[CI](https://github.com/bboytang/Mia/actions/runs/37250809373)及资源一致性检查通过；[16 Pro 抽帧](verification/mia-silent-launch-16pro-contact.jpg)、[SE 抽帧](verification/mia-silent-launch-se-contact.jpg)确认播放并进入首页，真机流畅度与最终衔接待验。 |
| [三款角色比较图](mia-three-character-options.png) | 用户明确选择**右侧第三款**。左侧和中间两款均未选定，不应在后续设计中误用。 |
| [已选首页概念图](mia-approved-screen-concept.png) | 用户选定的第三版方向：紫色短发、紫瞳、黑紫赛博服饰与晶体发饰的 Mia；蓝紫未来都市；底部字幕板、声波和麦克风。右侧功能入口的具体内容尚待设计。 |
| [干净城市背景](mia-approved-city-background.png) | 与概念图同方向的无角色背景原图，适合后续重新适配不同 iPhone 尺寸。 |
| [正面全身透明立绘](mia-full-body-transparent.png) | 用于图生模型 AI 网站的输入参考：1024 × 1536 PNG，已核验透明通道。使用 imagegen 按已选 Mia 造型、正面全身、双臂稍展开、透明背景生成；参考图未展示的鞋靴进行了补全。它是衍生参考，非分层源稿或 Cubism 模型。 |
| [启动动画动作预览](launch/mia-launch-preview-source.mp4) | 用户选择先用 40 积分生成的 360p、约 5 秒静音预览。包含粒子演变与角色动作，但中段造型有偏差且带 OpenArt 水印；未验收、未加入正式启动资源。分镜、提示词和待修正事项见[制作计划](../mia-launch-animation-plan.md)。 |
| [MiniMax H3 静音启动预览](launch/mia-minimax-preview-silent.mp4) | 用户确认重试一次后生成，768×1376、24 fps、约 5.17 秒；从含音轨的[原片](launch/mia-minimax-preview-source.mp4)直接封装为静音版，画面帧完全一致。已见转身，但中途造型/尺度变化和人物下沿截断未通过成品验收，未加入 App。[元数据](launch/mia-minimax-preview-metadata.json)。 |
| [启动动画外部生成交付包](launch/mia-launch-external-generation-brief.md) | 用户自行在其他平台生成用：首末帧链接、角色参考、完整提示词与验收要求。仍沿用既定 Mia，不代表视频成品已经完成。 |

应用首页恢复[原半身立绘](../../ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png)，使用[干净星雾背景](../../ios/MiaApp/Assets.xcassets/StarMistBackground.imageset/star-mist-background.png)和原生 SwiftUI 字幕/流光球；同构图前景雾与角色渐隐承接下沿。录音时流光按输入 PCM 音量响应，回答时按播放音量响应；两尺寸静态截图已核对通过，真实语音反馈仍待 iPhone 验收。[全身立绘](../../ios/MiaApp/Assets.xcassets/MiaFullBody.imageset/mia-full-body.png)和[城市背景](../../ios/MiaApp/Assets.xcassets/CityBackground.imageset/city-background.jpg)保留历史；不再作为当前默认参考。角色仍是静态图，不是分层源稿或 Live2D 模型。新背景与关键帧使用内置 imagegen，提示词约束沿用当前 Mia、蓝紫星雾、无地面，移除指定 UI 以提取背景/闭场参考；没有创建新收费视频任务。

正式 Live2D 必须另有获授权的分层 PSD/CSP、Cubism 工程 `.cmo3`、运行用 `.model3.json` 与 `.moc3`、贴图及动作/表情文件，至少支持眨眼、头部与身体动作和 `ParamMouthOpenY`。具体交付与验收见[Live2D 素材说明](../live2d-mia-asset-brief.md)。单张 PNG 无法直接变成真正的 `.moc3`。

用户最初上传的视频仅用于表达期望的界面和动画效果，原附件不在 GitHub；未经确认不将可能含第三方作品的视频公开上传。跨设备开发以此目录的已选视觉图和仓库内运行资源为准。

## 账号接入原生页面核对（2026-10-05）

来自账号版 `abe1ae4` 的 [成功 CI](https://github.com/bboytang/Mia/actions/runs/37246486540)：

- [登录页](verification/mia-account-login-preview.jpg)：用户名/密码、取消、注册入口，没有令牌输入。
- [注册页](verification/mia-account-register-preview.jpg)：确认密码、用户名/长度说明、注册即登录和切回登录。大标题截帧局部未完整绘制，完整导航标签测试通过；此帧不作为稳定标题显示的验收，需真机复核。
- [普通设置](verification/mia-account-settings-preview.jpg)：账号入口与折叠的高级维护，默认不出现维护令牌输入。
- [16 Pro 首页](verification/mia-account-home-16pro-preview.jpg)与 [SE 第三代首页](verification/mia-account-home-se-preview.jpg)：已批准半身、星雾、无图标流光球保持，登录提示位于球下方；设置、字幕圆角/间距和安全区域未发现截断。

三张账号图取自未输入任何凭据的原生 UI 测试；完整截图保存在 `.xcresult` 产物。测试通过不等于真实网络注册、麦克风、声音及打断验收。
