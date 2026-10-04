# Mia 已确定的视觉参考

下面的图片已纳入 GitHub，供其他设备上的 Codex、画师和绑定师查看。请以图片本身作为角色与画面风格的首要参考。

| 文件 | 用途 |
| --- | --- |
| [三款角色比较图](mia-three-character-options.png) | 用户明确选择**右侧第三款**。左侧和中间两款均未选定，不应在后续设计中误用。 |
| [已选首页概念图](mia-approved-screen-concept.png) | 用户选定的第三版方向：紫色短发、紫瞳、黑紫赛博服饰与晶体发饰的 Mia；蓝紫未来都市；底部字幕板、声波和麦克风。右侧功能入口的具体内容尚待设计。 |
| [干净城市背景](mia-approved-city-background.png) | 与概念图同方向的无角色背景原图，适合后续重新适配不同 iPhone 尺寸。 |
| [正面全身透明立绘](mia-full-body-transparent.png) | 用于图生模型 AI 网站的输入参考：1024 × 1536 PNG，已核验透明通道。使用 imagegen 按已选 Mia 造型、正面全身、双臂稍展开、透明背景生成；参考图未展示的鞋靴进行了补全。它是衍生参考，非分层源稿或 Cubism 模型。 |
| [启动动画动作预览](launch/mia-launch-preview-source.mp4) | 用户选择先用 40 积分生成的 360p、约 5 秒静音预览。包含粒子演变与角色动作，但中段造型有偏差且带 OpenArt 水印；未验收、未加入正式启动资源。分镜、提示词和待修正事项见[制作计划](../mia-launch-animation-plan.md)。 |
| [启动动画外部生成交付包](launch/mia-launch-external-generation-brief.md) | 用户自行在其他平台生成用：首末帧链接、角色参考、完整提示词与验收要求。仍沿用既定 Mia，不代表视频成品已经完成。 |

应用当前使用的[透明静态角色立绘](../../ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png)和[背景 JPG](../../ios/MiaApp/Assets.xcassets/CityBackground.imageset/city-background.jpg)是运行资源。静态立绘是已选造型的展示图，并非分层源稿或 Live2D 模型。若衍生图与已选首页概念图在造型或色彩上有差异，正式角色设计以已选首页概念图为准。

正式 Live2D 必须另有获授权的分层 PSD/CSP、Cubism 工程 `.cmo3`、运行用 `.model3.json` 与 `.moc3`、贴图及动作/表情文件，至少支持眨眼、头部与身体动作和 `ParamMouthOpenY`。具体交付与验收见[Live2D 素材说明](../live2d-mia-asset-brief.md)。单张 PNG 无法直接变成真正的 `.moc3`。

用户最初上传的视频仅用于表达期望的界面和动画效果，原附件不在 GitHub；未经确认不将可能含第三方作品的视频公开上传。跨设备开发以此目录的已选视觉图和仓库内运行资源为准。
