# Mia 启动动画：外部平台生成交付包

更新：2026-10-04。当前参考已按用户全身、腿型与比例反馈更新；MiniMax 默认请求已同步，外部平台生成同样使用下列最新参考。本文件提供参考图、首末帧框架和可复制提示词；它不是成品验收记录。沿用已选右侧第三款 Mia，不替换角色或服装。

## 参考资料与上传顺序

| 文件 | 用途 |
| --- | --- |
| [Mia 当前全身立绘](../../../ios/MiaApp/Assets.xcassets/MiaFullBody.imageset/mia-full-body.png) | 唯一当前角色参考：完整头到鞋靴、自然腿型与修长比例、原 V/伸手姿态。与 App 实际资源为同一文件。 |
| [粒子首帧](mia-particle-start.png) | 开场画面；只含原创蓝紫粒子云，没有角色与 UI。 |
| [全身闭场参考](mia-full-body-end-reference.png) | 以当前全身立绘生成的城市构图参考，完整鞋靴与下方圆形发光位置；没有文字和麦克风图标。它是参考构图，不是所有 iPhone 尺寸的精确截图。 |
| [城市背景](../../../ios/MiaApp/Assets.xcassets/CityBackground.imageset/city-background.jpg) | 需要独立背景参考时上传；不要重新生成不同城市。 |

用户原视频只参考前段纤维般细密、柔软立体、蓝紫渐变的粒子质感，不照搬后段胶状物或其他作品标识；原附件没有公开上传。

若平台支持，指定粒子图为首帧、闭场图为末帧，并将当前全身立绘加入独立角色参考。多张视觉参考不等于首末帧锁定，平台能力不同，不保证都能同时设置。现有首末参考均为 933×1686；选择 9:16 输出时，对两张图采用一致的裁切/适配，生成后检查构图。

旧半身 `MiaPortrait`、旧半身末帧和旧 A 姿势全身图保留历史，不再作为本次上传参考；不得混用导致人物形象或比例不同。

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
Use the current full-body ending image as the composition reference. Keep the entire head, hair ornaments, hands, complete legs and both boot soles visible. Preserve the refined natural leg alignment and elegant adult proportions of the current Mia full-body image. The exact same Mia from the current full-body character image, with the established detailed 2D anime illustration style, violet eyes, layered wavy lilac bob, large faceted purple crystal ornaments in black angular frames, and every original black-and-purple outfit detail intact. She smiles toward the viewer with the original slight head tilt. The hand on screen right forms the original V gesture beside her face; the other hand reaches toward the viewer in the original open-hand pose. Keep the supplied blue-violet futuristic city, character scale and position. A restrained violet-cyan circle glows at the exact position shown near the lower center, approximately x=0.5, y=0.839 of the frame. Hair and jacket have settled. No lettering, microphone glyph, buttons, extra accessories, new costume or 3D restyling.
```

## 连续视频主提示词

```text
Create a single uninterrupted five-second portrait Mia launch animation. Repair priorities: continuous organic particle-to-character formation, and absolutely no straight horizontal cutoff or rectangular pasted character layer. Preserve the character and final pose from the supplied last frame. Use the first frame for the fine violet-cyan filament cloud. The last frame now shows Mia completely from head crystals to both boot soles: preserve her complete natural adult silhouette. Both legs, knees, calves, ankles and boots must remain visible at all times after formation, with clear margin around the entire figure.

Keep the camera locked and the character at the final frame's scale and screen position from her very first appearance. Hair, crystals, face, jacket and outfit should remain recognizably the supplied Mia; minor natural clothing movement is acceptable. The near-face hand on screen right finishes in the supplied V pose, the other hand reaches toward the viewer. The lower circle keeps its exact supplied center and size. Keep the refined natural leg alignment and elegant adult proportions exactly as shown. No bowed shins, no knee distortion or extra limbs. Keep both entire boots visible above the lower UI area, never crop at the thighs or knees.

0.0–1.0 seconds: Start exactly on the supplied airy violet-cyan fine-filament cloud. It breathes gently and rotates clockwise. The original city begins to emerge very slowly behind the cloud as faint stationary lights, not as a sudden replacement scene. Keep all particles fine, airy and translucent; they must never become a solid jelly mound, opaque cone or smooth sheet.

1.0–2.6 seconds: Gradually accelerate the SAME clockwise flow. One continuous volumetric cloud stretches into Mia's ENTIRE visible silhouette at its FINAL scale and position: head, shoulders, torso, arms, skirt, complete legs and both boots begin resolving together through translucent filaments. Crystals resolve a little earlier, while the rest resolves gradually at overlapping times. Do not introduce an isolated head or detached upper torso first. Particle density falls smoothly over the WHOLE figure, not as a rising or falling horizontal reveal curtain. All body parts resolve at overlapping times; translucent particles briefly surround the complete legs and boots. Do not expose severed thigh or waist edges at any stage. Residual filaments continuously link the original cloud to the emerging hair, sleeves and boots. The stationary city becomes fully visible through the SAME continuous transition by about 2.6 seconds. No jump in character size, position or lighting, no cut, flash, sudden pop-in or camera zoom.

2.6–3.8 seconds: Mia completes a graceful physical turn from a modest three-quarter angle toward the viewer, with head, shoulders and chest moving together. Hair and loose jacket sleeves trail with gentle inertia. Maintain the full visible figure throughout; no horizontal pedestal, black belt-shaped background obstruction, rectangular overlay or cropped body segment. The emerging character and city already occupy their final composition, so there is no later camera pullback.

3.8–4.5 seconds: The hand on screen right makes one small sweep beside the face, a thin crystal trail visibly following the fingertips, then settles into the supplied V gesture. The other hand stays extended toward the viewer. The same light arc flows down to the lower circle and gives it a restrained pulse. Keep the face visible, the city stationary and the complete legs and boots visible, with tiny residual particles around them.

4.5–5.0 seconds: Ease into the exact supplied ending pose, scale and composition. Hair, sleeves and particles settle gently. The complete figure stands naturally with both boot soles clearly visible; no body truncation, feathered lower body or disappearing legs. Hold the settled ending for the last 0.3 seconds. No camera movement, no reframing, no body zoom or scale jump, no text, UI symbols, logo, dialogue or music; a separate synchronized launch sound will be added after generation.
```

## 可选负面提示词

仅在平台有独立负面提示栏时填写；没有时，把关键限制保留在主提示词即可。

```text
different character, identity drift, changing face, changing costume, simplified clothes, smooth straight bob, missing crystal ornaments, small silver replacement clips, missing straps or chains, symmetric stockings, extra limbs, extra hands, malformed fingers, both hands pointing at the face, light ribbon before the fingertip gesture, static-image zoom, camera pullback, camera orbit, hard cut, flash transition, flicker, 3D restyling, live action, generated text, UI symbols, logo, audio
```

## 返回与验收

保留原始 MP4 和平台输出参数。生成后检查：凝成时确实侧向、头肩共同旋身；画 V 的手先画弧，另一手保持伸出；全程原发饰/脸/服装一致；末尾姿态稳定、圆环位置不漂移；无音轨和可合法使用的无水印输出。

如果平台可另导出透明前景或逐帧遮罩，也一并保留，便于不同手机画幅合成；不能为了方便而重画角色。最终 App 衔接仍需在真实布局中对齐、录屏并验收。单一 9:16 视频在 16 Pro 与 SE 的裁切不同，不能仅凭末帧参考或淡出宣称已匹配所有 iPhone。
