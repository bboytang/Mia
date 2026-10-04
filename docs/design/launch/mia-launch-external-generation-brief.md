# Mia 启动动画：外部平台生成交付包

更新：2026-10-04。用户已批准半身星雾 UI：取消左上角全部文字，底部使用无麦克风标识的蓝紫粉流光球。此决定取代此前全身城市方案；MiniMax 默认请求与外部生成参考同步为下列版本。本文件提供参考图、首末帧框架和可复制提示词；它不是视频成品或所有设备精确布局的验收记录。沿用已选右侧第三款 Mia，不替换角色或服装。

## 参考资料与上传顺序

| 文件 | 用途 |
| --- | --- |
| [Mia 原半身立绘](../../../ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png) | 当前角色身份参考：原紫色卷短发、晶体发饰、服装与 V/伸手姿态。App 恢复使用此角色资源。 |
| [粒子首帧](mia-particle-start.png) | 开场画面；933×1686，只含原创蓝紫粒子云，没有角色与 UI。 |
| [半身星雾闭场参考](mia-halfbody-starmist-end-reference.png) | 941×1672；原半身角色、深蓝紫星雾、永久下沿雾和无图标流光球，没有文字、字幕板或设置图标。它是构图参考，不是所有 iPhone 尺寸的精确截图。 |
| [批准的 UI 设计稿](../mia-approved-starmist-ui.png) | 941×1672；展示字幕面板与无图标流光球等首页关系，仅作设计依据，不把文字和原生控件生成进视频。 |
| [星雾背景](../../../ios/MiaApp/Assets.xcassets/StarMistBackground.imageset/star-mist-background.png) | App 当前独立背景；需要背景参考时使用，不使用旧城市地面。 |

用户原视频只参考前段纤维般细密、柔软立体、蓝紫渐变的粒子质感，不照搬后段胶状物或其他作品标识；原附件没有公开上传。

若平台支持，指定粒子图为首帧、半身星雾闭场图为末帧；只有平台允许时才另外加入原半身角色参考。MiniMax H3 的首末帧模式不能与独立参考媒体混用，本工具只提交两张首末图。首帧 933×1686、末帧 941×1672，尺寸与比例不同；MiniMax 使用已验证字段 `ratio=adaptive`，实际输出尺寸与构图待生成后检查。外部平台选择 9:16 时需核对两张图的裁切/适配，不能猜测自动处理结果。

旧城市半身末帧、全身立绘与全身末帧保留历史，当前不用于生成；不得与批准的半身星雾参考混用。原 `MiaPortrait` 重新成为当前身份参考。

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
Use the approved half-body star-mist ending image as the composition reference. Preserve the original Mia portrait identity: violet eyes, layered wavy lilac bob, large faceted purple crystal ornaments in black angular frames and original black-and-purple outfit details. Keep her smiling slight head tilt, the screen-right V gesture beside her face and the other hand reaching toward the viewer. Keep the camera, character scale and position supplied in the ending image. Deep blue-violet stars, floating crystals and layered purple foreground mist surround her. The lower portrait edge stays permanently concealed in irregular mist and fine filaments, without a straight crop or visible severed body. A blue-violet-pink flowing aurora orb sits at the supplied lower position, with no microphone glyph. No city, floor, invented legs or boots, lettering, title, logo, subtitle panel, settings icon, new costume or 3D restyling.
```

## 连续视频主提示词

```text
Create one uninterrupted five-second portrait launch animation for Mia. Use the supplied first frame for the airy violet-cyan fine-filament cloud, and the supplied last frame for the approved HALF-BODY Mia, deep blue-violet star mist, floating crystals and icon-free aurora orb. Preserve the same established 2D anime character, wavy lilac bob, violet eyes, faceted purple crystal hair ornaments in black angular frames, black-and-purple outfit, near-face V gesture on screen right and other hand reaching toward the viewer. This is a close half-body portrait, not a full-body scene. Do not invent visible lower legs, boots, a ground plane or a city.

Keep the camera locked, and keep Mia at the last frame's scale and screen position from her first appearance. The lower portrait edge must always remain inside overlapping, irregular layers of dark violet foreground mist, luminous filaments and fine particles. The mist is part of the final composition and stays after the reveal; it must never clear to expose a straight crop or a severed body. Keep the face and hands clear. Do not replace the mist with a flat horizontal strip, a solid pedestal, a scan line or a rectangular pasted layer. The lower aurora orb keeps the position and size supplied in the last frame and never acquires a microphone glyph.

0.0–1.0 seconds: Begin on the supplied fine violet-cyan cloud. It breathes gently and rotates clockwise. Deep blue-violet stars and soft mist begin appearing continuously behind it, with restrained crystal glints. All particles stay airy and translucent, never forming a solid jelly dome, opaque cone or smooth sheet.

1.0–1.6 seconds: Accelerate the SAME clockwise filaments smoothly and draw them toward the lower portrait edge, where a layered violet mist gathers. Light trails spiral upward from this base and naturally carry the motion into character formation. Do not introduce a detached head, face or shoulders above an absent torso.

1.6–2.8 seconds: Reveal Mia from the lower portrait edge upward: skirt and waist first, then torso, shoulders and arms, then face, hair and crystal ornaments. These regions resolve at overlapping times through uneven, flowing particle strands, not through a tidy horizontal wipe or scanning curtain. The lower edge stays concealed by foreground mist throughout. Residual particles link the emerging outfit, sleeves and hair to the same original cloud. Maintain a modest three-quarter orientation until the torso and head are coherent. No size jump, camera pullback, flash, hard cut or sudden background replacement.

2.8–4.4 seconds: With the body already coherent, Mia turns gracefully toward the viewer, with head, shoulders and chest moving together. Hair and loose sleeves trail with gentle inertia. The hand on screen right sweeps a small arc beside her face, a thin crystal light trail following the fingertips, then settles into the supplied V gesture. The other hand reaches toward the viewer as in the ending image. Keep the half-body framing and persistent layered mist, and retain the recognizable face and outfit throughout.

4.4–5.0 seconds: The same fingertip light arc travels into the lower icon-free aurora orb. Violet, cyan and a little pink light flow through it in a restrained pulse, then settle naturally. Ease into the exact supplied ending pose, scale and star-mist composition and hold the last 0.3 seconds. Hair, sleeves and particles slow gently while the lower portrait edge remains concealed. No city, floor, visible cut, detached body, extra limbs, text, logo, lettering, subtitle panel, settings icon or microphone symbol. No dialogue or music; a separate synchronized launch sound will be added after generation.
```

## 可选负面提示词

仅在平台有独立负面提示栏时填写；没有时，把关键限制保留在主提示词即可。

```text
different character, identity drift, changing face, changing costume, simplified clothes, smooth straight bob, missing crystal ornaments, small silver replacement clips, missing straps or chains, full-body scene, invented legs or boots, city, floor, exposed lower crop, detached head, severed torso, horizontal scan wipe, rectangular pasted layer, solid jelly dome, extra limbs, extra hands, malformed fingers, both hands pointing at the face, light ribbon before the fingertip gesture, static-image zoom, camera pullback, camera orbit, hard cut, flash transition, flicker, 3D restyling, live action, generated text, title, microphone glyph, settings icon, subtitle panel, logo, audio
```

## 返回与验收

保留原始 MP4 和平台输出参数。生成后检查：从下沿向上按裙腰、肩臂、脸发顺序重叠凝形，没有孤立头部或整齐扫描；永久前景雾始终遮住下沿；身体完整凝形后头肩共同旋身，画 V 的手先画弧，另一手保持伸出；全程原发饰/脸/服装一致；末尾姿态稳定，无图标流光球位置不漂移；无音轨和可合法使用的无水印输出。正式视频仍待后续费用审批、制作和验收，当前只准备参考和离线请求。

如果平台可另导出透明前景或逐帧遮罩，也一并保留，便于不同手机画幅合成；不能为了方便而重画角色。最终 App 衔接仍需在真实布局中对齐、录屏并验收，尤其要检查原生流光球与视频末帧之间的交接。不同手机的裁切与安全区域不同，不能仅凭静态参考或淡出宣称已匹配所有 iPhone。
