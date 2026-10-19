# 蓝金星环皮肤素材

用户提供的三张照片为同一球体的正面与侧面参考。采用 imagegen 内置工具制作可复用的透明球壳和独立耳环，动态脸、粒子、姿态和耳环响应由 SwiftUI 实时绘制；图片本身不是动画。

资源：`ios/YoumiApp/Assets.xcassets/YoumiHolographicShell.imageset/shell.png`、`ios/YoumiApp/Assets.xcassets/YoumiHolographicEar.imageset/ear.png`。两张均为带 alpha 的 PNG。默认保留玻璃流体主题；`mia.appearance.skin` 保存用户选择。

参考图片仅用于素材生成，不直接打包整张参考照片。球壳边缘仍包含部分静态侧面反射，独立耳环覆盖并做音量响应；流动荧光采用有界粒子绘制，不能将静态高光称为流动动画。后台暂停绘制；减少动态效果关闭眨眼/摇摆/时间流动，保留音量亮度和嘴形反馈。

增加主题时，在 `YoumiSkin` 添加稳定的raw值、标题和说明，在 `YoumiAvatarView` 路由到对应视图；选择页根据 `CaseIterable` 显示，不需要新增皮肤框架。已发布raw值不要重命名，以免丢失用户选择。

## 球壳提示词（内置 imagegen，透明背景）

Use case: precise-object-edit. Asset type: a production iOS animated character's static shell layer, RGBA transparent PNG. Edit the reference image into ONE front-facing, perfectly symmetrical spherical shell only. Preserve the reference's very high quality glossy 3D glass, polished dark metallic shell segments, intense electric-blue and warm gold illuminated outer rings, photoreal specular reflections. REMOVE BOTH SIDE EAR DISCS completely (they will be separate animated native layers), remove the pedestal, floor, light beam and black background outside the sphere. REMOVE ALL eyes, eyebrows, mouth, nose and facial marks: the central front inner face area must be smooth dark navy/black, blank and clean so animated facial layers can be drawn there. Remove discrete interior glowing particle dots; retain polished shell bands/reflection texture mainly around the OUTER 20 percent of sphere, keep middle 60 percent blank dark face. Sphere silhouette entirely round, not an ellipse. Center the sphere, fill exactly approximately 88 percent of square canvas width and height, leave even transparent margin. Genuine alpha outside sphere. No ears, no face, no pedestal, no text, no watermark, no additional objects. This is a layered character asset, not a finished illustration: do not put any facial features back. Render at 1024x1024.

## 耳环提示词（内置 imagegen，透明背景）

Use case: precise-object-edit. Production layered animated iOS character asset. Extract and reconstruct ONLY ONE of the mechanical round side ear/acoustic discs from the supplied blue/gold robot sphere reference. Show this SINGLE disc dead straight front-on as a perfectly circular disc, NOT angled and NOT oval (native app will foreshorten it). Extreme glossy photoreal 3D detail matching the reference: dark chrome beveled outer ring, small radial metallic segments/ticks, brilliant electric-blue outer accents, bright orange-gold concentric glowing inner rings, dark navy recessed central round glass speaker surface. Isolated single ear disc occupies 86% of a square canvas with even TRANSPARENT background around it. No sphere, no facial features, no pedestal, no arms, no other objects, no text, no watermark. Keep all rings circular and concentric. Transparent RGBA sprite, 1024x1024.
