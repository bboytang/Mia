# Mia 启动动画：MiniMax H3 API 工具

2026-10-04。此工具只用于离线制作启动视频，不接入 iOS、语音网关或火山密钥配置。沿用已确认角色与[分镜](mia-launch-animation-plan.md)，没有替换 Live2D。用户已在当前环境隐藏设置 MiniMax Key，真实创建请求已被受理；首条任务因参考图片读取失败，用户确认的一次内嵌图片重试已成功生成预览；正式成品质量尚未验收。

## 协议依据与生成参数

- [官方创建接口](https://platform.minimax.cn/docs/api-reference/video-generation-v2-create)：`POST https://api.minimax.cn/v2/video_generation`，Bearer 鉴权。
- [官方查询接口](https://platform.minimax.cn/docs/api-reference/video-generation-v2-query)：`GET /v2/query/video_generation/{task_id}`；查询近七天任务。
- 图片项使用 `{"type":"image_url","image_url":{"url":"HTTPS 地址"},"role":"first_frame"}`；尾帧 role 为 `last_frame`。首尾帧不能与独立参考媒体混用，本工具仅实现首尾帧模式。
- 默认 `MiniMax-H3`、5 秒、`768P`、`ratio=adaptive`、`aigc_watermark=false`。当前首帧为 933×1686 的原粒子图，末帧为 941×1672 的批准半身星雾图，二者尺寸与比例不同；不能宣称输出必为严格 9:16 或推测平台如何适配，实际比例与构图以查询和下载文件为准。
- [当前提示词](design/launch/mia-minimax-prompt.txt)按用户批准的半身星雾分镜更新：从人物下沿向上重叠凝形、身体完整后旋身、指尖光弧落入无图标流光球。下沿雾永久保留，不生成全身、城市或裸露切口；没有左上角文字或麦克风标识。末帧中的原半身 Mia 定义身份，不把带水印且造型漂移的 OpenArt 预览或历史全身图作为参考。
- [官方中国平台价格](https://platform.minimax.cn/docs/pricing/overview)：核对当天 H3 768P 为 0.50 元/秒，2K 为 0.80 元/秒，五张以内图片免费。默认单次预估 2.50 元，5 秒 2K 为 4.00 元；以账户实际计费为准。代码不承诺或硬编码账单。

H3 没有在此协议声明静音参数，提示词要求静音仍须实际检查音轨；不发送其他平台的 `generateSound` 字段。输出水印、角色身份、真正转身与自然衔接均需逐帧验收，不能仅凭成功状态认为成品通过。

## 隐藏配置 Key

本地使用项目虚拟环境，已安装 `httpx==0.28.1`，无需新增 SDK：

```bash
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py configure
```

只在交互终端提示中粘贴中国 MiniMax 开放平台 API Key。不回显，原子写入仓库外 `~/.config/mia/minimax.key`，权限 0600。重复运行可更新；不会验证鉴权、提交任务或扣费。也支持 `MINIMAX_API_KEY` 环境注入，但不要把值写进命令历史、仓库、聊天或日志。此 Key 不放入 `/etc/mia/gateway.env`。

## 当前环境部署（用户选定）

用户改为在当前 Codex 工作环境运行工具，路径 `/root/projects/Mia`，不依赖 Mia VPS 的 SSH 授权。已验证项目虚拟环境、离线请求准备和到中国 MiniMax API 的 HTTPS 连通性；无鉴权查询探测返回 HTTP 401，不能据此宣称真实 Key 已通过。

隐藏配置短入口已放在当前环境 `/tmp/mia-minimax-key`（只包装上述 configure，不含 Key、不发生成请求）：

```bash
bash /tmp/mia-minimax-key
```

请在当前工作环境的交互终端运行。临时入口不随 Git 保存；换环境后用上方 Python 完整命令重新配置。密钥仍位于仓库外 `~/.config/mia/minimax.key`，不进入 iOS 或火山语音服务。用户已设置；只核对了存在性与 0600 权限，未输出内容。两次带 Key 的不存在任务查询均返回 HTTP 500，第二次标准错误为 `server_error`；与先前无鉴权 HTTP 401 不同，但不足以宣称真实鉴权及生成权限验证通过。没有创建任务或扣费，等待单次预算确认。

## 准备、提交与恢复

以下命令以仓库根目录为工作目录。`prepare` 不读取 Key，也不发网络请求：

```bash
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py prepare
```

确认首尾图、提示词、参数与费用后，才提交一次付费任务：

```bash
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py create --confirm-charge --state /tmp/mia-h3-task.json
```

输出任务 ID，状态文件只保存 ID，权限 0600，不保存 Key 或签名下载地址。文件必须不存在；同一路径不能重复提交。创建超时不自动重试，会留下 `submission_pending`，先查 MiniMax 控制台确认是否受理，不能直接换文件名重提。

用实际 ID 替换 `TASK_ID`，所有后续操作复用同一任务：

```bash
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py status TASK_ID
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py wait TASK_ID
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py download TASK_ID --output /tmp/mia-h3-original.mp4
```

等待默认最多 900 秒，每十秒查询；超时可继续等待，不重新生成。failed/cancelled 明确终止。下载使用独立无鉴权客户端、仅 HTTPS、不跟随重定向、不覆盖现有文件，失败清理临时文件。HTTP 错误只输出状态，不打印上游正文或签名 URL。原始视频先保留在仓库外，验收通过后再决定 App 资源。

## 验证边界

### 首次真实提交与素材传输修正

用户要求“开始生成”后，按既定首尾图、5 秒 768P 提交一次，创建返回任务 `448779139891511`。查询状态为 failed，错误码 2013，错误内容归类为参考素材读取/下载失败；没有输出上游错误正文或 Key，也没有自动重试。usage 为空，不能宣称实际已扣或已退多少费用。

为避免平台访问 GitHub 图片地址失败，新增本地 PNG/JPEG 路径输入，按官方 `image_url.url` 支持的 `data:image/png;base64,...` 直接内嵌原图，不修改图片。逐图检查 30 MB 上限、整个请求检查 64 MB 上限；现有两张 PNG 请求约 6.32 MB。15 项离线测试通过，包括原图字节的 Base64 往返；提交 `b388b62` 的 [内嵌图片修正 CI](https://github.com/bboytang/Mia/actions/runs/37203924922)通过 15 项测试及 URL/内嵌两种请求准备；用户随后确认一次重试，内嵌图片任务已生成成功（见下方记录）。

准备修正请求（不联网、不收费）：

```bash
/root/projects/Mia/.venv/bin/python scripts/mia_minimax_video.py prepare --first docs/design/launch/mia-particle-start.png --last docs/design/launch/mia-home-end-reference.png > /tmp/mia-h3-inline-request.json
```

用户已确认重试一次，使用新任务与状态文件 `/tmp/mia-h3-task-20261004-inline.json`，保留失败任务记录。模型、时长、清晰度、首尾图和提示词保持原方案。

离线测试覆盖请求字段、鉴权、错误正文隐藏、不重试付费请求、查询、等待终止与超时、下载与文件保护、0600 Key、交互输入以及付费确认与状态保留。CI 不配置真实 Key，不创建付费任务。

```bash
/root/projects/Mia/.venv/bin/python -m unittest scripts.video_tests.test_mia_minimax_video -v
```

提交 `554c302` 的 [CI](https://github.com/bboytang/Mia/actions/runs/37202954070)已通过 14 项测试和离线请求准备。本地另有 98 项固件测试、23 项服务端测试通过（后者需允许绑定本地测试套接字）。

Key 已在当前环境隐藏配置，真实创建已受理；首条任务失败，用户确认的一次内嵌图片重试成功。下载完成后检查实际分辨率、时长、帧率、音轨、水印、Mia 造型和动作，再验证首页衔接。当前无合格正式 `MiaLaunch.mp4`，不得标记启动动画完成。

## 内嵌图片真实生成结果

任务 `448781796409606` 已成功，usage 报告 output_seconds=5、input_image_count=2；账单实际金额未核对。原片 768×1376、24 fps、约 5.167 秒、124 帧、包含一条音轨，与所请求的整 5 秒略有差异。

- [原始视频](design/launch/mia-minimax-preview-source.mp4)：保留平台原输出。
- [静音预览](design/launch/mia-minimax-preview-silent.mp4)：只重新封装视频流，移除音轨；逐帧 RGB 解码哈希与原片一致，无重画、裁切或水印处理。
- [清理后的元数据](design/launch/mia-minimax-preview-metadata.json)：尺寸、时长、音轨数、文件与解码帧校验值；没有 Key 或签名下载地址。

九帧检查可见粒子旋绕凝成人物、侧面转向、V 手势与圆环亮起。但侧面角度大于原定约 35 度，约 2.5–3.5 秒人物下沿出现明显水平截断，服饰和人物尺度在中途变化；还不能证明指尖光弧、圆环和所有手机首页衔接满足既定方案。未见所抽帧中出现平台文字水印，不作完整版权或逐帧无水印认证。

该视频只供预览，未验收、未作为 `MiaLaunch.mp4` 加入 iOS。需要继续修正前先取得用户对画面与新一次费用的决定；不自动生成第三条任务。

## 当前批准半身星雾版本与启动音效准备

用户已批准[半身星雾 UI](design/mia-approved-starmist-ui.png)，取消左上角全部文字，并将底部控件改为没有麦克风标识的蓝紫粉流光球。当前角色身份参考恢复为 `ios/MiaApp/Assets.xcassets/MiaPortrait.imageset/mia-portrait.png`；[当前末帧](design/launch/mia-halfbody-starmist-end-reference.png)为 941×1672，包含原半身人物、永久下沿雾和流光球，没有文字、字幕板或设置图标。原生控件由 App 单独绘制；此图只是构图参考，不是两种手机精确首页截图。

脚本默认首帧仍为原粒子图，末帧已改为批准的半身星雾图，均直接内嵌本地文件。[当前提示词](design/launch/mia-minimax-prompt.txt)和[外部生成交付包](design/launch/mia-launch-external-generation-brief.md)同步相同角色与分镜：0–1 秒细云旋转，1–1.6 秒提速并向人物下沿汇聚，1.6–2.8 秒按裙腰、肩臂、脸发重叠向上显现，2.8–4.4 秒旋身和手势，4.4–5 秒光弧落入无图标流光球；下沿雾在结尾继续遮住切口，不用整齐扫描、头部先显或城市地面。准备命令仍为 `prepare`，无需额外文件参数；此阶段未调用生成 API。

本地 16 项离线测试通过，包括默认末帧与文件字节一致性及下沿提示词检查；`prepare` 通过，新请求 5,795,294 字节，首末帧 Base64 还原与源文件完全相同，主提示词 3,698 字符，与外部交付包相同。工作流已更新首末帧触发路径与离线准备命令；当前提交的 GitHub CI 尚待核对，未读取 Key 或发网络请求。

**全身方向历史**：此前按用户全身、腿型与比例要求生成的 `MiaFullBody` 和 `mia-full-body-end-reference.png` 已同步过当时 App 与默认请求。用户随后改为批准原半身星雾方案，因此这些资源保留历史，不再作为当前默认输入。初版提示词继续保存在 `mia-minimax-preview-prompt.txt`，用于复现既有半身城市预览，不能与当前末帧混用。

[原创音效草稿](design/launch/mia-launch-sound-v1.wav)为 5 秒、48 kHz、双声道 PCM16，细粒子声加速、凝聚晶体响、手势轻响、圆环柔和收尾；没有借用录音。峰值约 -13.98 dBFS，起止为零，已检查不削波；需按新版实际动作重新对齐，结尾对应流光球。声音尚未在设备试听或加入启动播放器；不能把音效草稿当成 App 音效已验收。

2026-10-05 用户重新确认一次 H3、5 秒、768P 任务（预估 2.50 元），任务 `448953378521398` 已成功，未重复提交。保存[星雾原片](design/launch/mia-starmist-preview-source.mp4)、[静音版](design/launch/mia-starmist-preview-silent.mp4)、[带原创音效版](design/launch/mia-starmist-preview-with-sound.mp4)和[元数据](design/launch/mia-starmist-preview-metadata.json)。实际 768×1376、24 fps、5.167 秒、124 帧；原片含 AAC，两种合成版画面解码哈希与原片一致。账单实际金额未核对。

持续下沿星雾遮住旧版裸露切口，但约 2 秒出现较亮的凝形光带，中段角色服饰和尺度仍漂移；未通过正式素材验收，未加入 App。原创草稿已按实际动作分段调整，约 2.167/3.417/4.25 秒对应凝形、手势、流光球；独立 WAV 峰值 −13.99 dBFS、无削波、起止零，真机试听和首页交接仍待验。本地 16 项工具测试和 `pip check` 通过；本阶段没有更改代码或 CI 路径文件，因此未触发新 CI。费用授权已经使用，后续新生成需另行确认。
