# Mia 启动动画：外部平台生成交付包

更新：2026-10-04。用户选择自行在其他平台生成。本文件提供参考图、首末帧框架和可复制提示词；它不是成品验收记录。沿用已选右侧第三款 Mia，不替换角色或服装。

## 参考资料与上传顺序

| 文件 | 用途 |
| --- | --- |
| [Mia 原立绘](../../../ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png) | 首要角色身份、脸、卷曲短发、晶体发饰、服装和最后手势参考。 |
| [粒子首帧](mia-particle-start.png) | 开场画面；只含原创蓝紫粒子云，没有角色与 UI。 |
| [闭场参考](mia-home-end-reference.png) | 原城市、原 Mia 姿态和下方圆形发光位置；没有文字和麦克风图标。它是参考构图，不是所有 iPhone 尺寸的精确截图。 |
| [城市背景](../../../ios/MiaApp/Assets.xcassets/CityBackground.imageset/city-background.jpg) | 需要独立背景参考时上传；不要重新生成不同城市。 |
| [全身衍生参考](../mia-full-body-transparent.png) | 仅在平台需要全身补充时使用；鞋靴是补全，不能覆盖原立绘的头脸与服装设计。 |

用户原视频只参考前段纤维般细密、柔软立体、蓝紫渐变的粒子质感，不照搬后段胶状物或其他作品标识；原附件没有公开上传。

若平台支持，指定粒子图为首帧、闭场图为末帧，并将原立绘加入独立角色参考。多张视觉参考不等于首末帧锁定，平台能力不同，不保证都能同时设置。现有首末参考均为 933×1686；选择 9:16 输出时，对两张图采用一致的裁切/适配，生成后检查构图。

## 输出设置

- 竖屏 9:16；约 5 秒；静音；一镜连续演绎。
- 优先输出平台支持的 1080p、24 或 30 fps、H.264 MP4；先生成一条预览检查动作，再输出正式清晰版本。
- 固定镜头、固定角色尺度；关闭自动多镜头、镜头变焦、自动字幕和文字生成。
- 正式交付使用平台提供的合法无水印输出。原有带水印且造型漂移的 360p 视频只供动作讨论，不作身份或成品参考。

## 首帧提示词

```text
Vertical portrait opening frame for the Mia app. A deep midnight navy space, with a soft three-dimensional cloud made of extremely fine luminous particles and delicate flowing filaments. The cloud is centered slightly above the middle, with violet and cyan outer layers and a restrained rosy lilac glow inside. Dense, airy, elegant, volumetric and softly luminous, ready to rotate clockwise. Keep the bottom area dark and uncluttered. No character, buildings, text, logo, UI, large sparks or solid jelly-like object. Follow the supplied original particle image.
```

## 末帧提示词

```text
Use the supplied ending image as the composition reference. The exact same Mia from the original character image, with the original detailed 2D anime illustration style, violet eyes, layered wavy lilac bob, large faceted purple crystal ornaments in black angular frames, and every original black-and-purple outfit detail intact. She smiles toward the viewer with the original slight head tilt. The hand on screen right forms the original V gesture beside her face; the other hand reaches toward the viewer in the original open-hand pose. Keep the supplied blue-violet futuristic city, character scale and position. A restrained violet-cyan circle glows at the exact position shown near the lower center, approximately x=0.5, y=0.839 of the frame. Hair and jacket have settled. No lettering, microphone glyph, buttons, extra accessories, new costume or 3D restyling.
```

## 连续视频主提示词

```text
Create one uninterrupted five-second portrait animation for the Mia app: soft gradient stardust accelerates, assembles into Mia, she physically turns toward the viewer, and her fingertip draws a crystal light arc that activates the lower circular glow.

REFERENCE PRIORITY: The original Mia character image defines identity, exact face, violet eye proportions, detailed 2D anime rendering, layered wavy lilac bob, large black-framed purple crystal ornaments, hair accessories and all costume details. Preserve the original straps, jacket sleeves, waist decorations, chains and asymmetric fishnet stocking. The particle image defines the opening texture and composition. The ending image defines the original city, final character pose and lower glow position. Do not reinterpret or redesign Mia.

0.0–1.2 seconds: Begin with the supplied soft violet-cyan particle cloud in a dark space. It breathes gently and starts a coherent clockwise rotation. Fine flowing filaments remain dense and volumetric; avoid sparse large glitter dots.

1.2–2.2 seconds: The same rotation accelerates smoothly. Orbital trails tighten into a single elegant spiral and stretch into the head, shoulders and body silhouette. The original crystal ornaments become solid first. Preserve continuous motion and lighting without a cut or flash.

2.2–3.3 seconds: Hair, face, jacket, clothing and hands progressively resolve into the exact original Mia. Her head, shoulders and chest initially face approximately 35 degrees away from the camera. Keep her at the final character scale; do not zoom out. Residual particles flow along her contours. The supplied city appears gradually behind her, its buildings staying stationary.

3.3–4.5 seconds: Mia clearly turns her head, shoulders and chest through those 35 degrees toward the viewer. Nose perspective and clothing straps rotate coherently with her body. Hair tips, loose sleeves and hanging ornaments trail with inertia, then settle. She gives the original warm smile. The hand on screen right, which will form the final V gesture, makes one small graceful sweep beside her face. A thin crystal light trail follows those fingertips, then that same hand naturally closes into the original V pose. The other hand stays extended toward the viewer. The arc must be caused by this hand movement; do not create an unrelated halo around her head or a ribbon sweeping across her whole body.

4.5–5.0 seconds: The completed light arc leaves the fingertips and flows downward into the supplied lower circular glow, approximately normalized x=0.5, y=0.839 from the top-left. It energizes the circle without moving or resizing it. By 4.7 seconds, Mia has settled into the supplied ending pose and composition, with only very subtle residual particles. Hold the ending calmly for the last 0.3 seconds to allow a natural transition into the app homepage.

Locked camera. Real articulated head, shoulder and hand movement; no static-image pan, scale animation or zoom used in place of a turn. Keep one character, two anatomically consistent hands and the same face and costume throughout. Fluid acceleration followed by gentle deceleration. Detailed 2D illustration throughout, no live-action or 3D conversion. No hard cuts, jump cuts, white flash, generated UI, lettering, logos or sound. Use the platform's watermark-free output when available.
```

## 可选负面提示词

仅在平台有独立负面提示栏时填写；没有时，把关键限制保留在主提示词即可。

```text
different character, identity drift, changing face, changing costume, simplified clothes, smooth straight bob, missing crystal ornaments, small silver replacement clips, missing straps or chains, symmetric stockings, extra limbs, extra hands, malformed fingers, both hands pointing at the face, light ribbon before the fingertip gesture, static-image zoom, camera pullback, camera orbit, hard cut, flash transition, flicker, 3D restyling, live action, generated text, UI symbols, logo, audio
```

## 返回与验收

保留原始 MP4 和平台输出参数。生成后检查：凝成时确实侧向、头肩共同旋身；画 V 的手先画弧，另一手保持伸出；全程原发饰/脸/服装一致；末尾姿态稳定、圆环位置不漂移；无音轨和可合法使用的无水印输出。

如果平台可另导出透明前景或逐帧遮罩，也一并保留，便于不同手机画幅合成；不能为了方便而重画角色。最终 App 衔接仍需在真实布局中对齐、录屏并验收。单一 9:16 视频在 16 Pro 与 SE 的裁切不同，不能仅凭末帧参考或淡出宣称已匹配所有 iPhone。
