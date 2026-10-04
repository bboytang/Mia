# Mia 启动动画：MiniMax H3 API 工具

2026-10-04。此工具只用于离线制作启动视频，不接入 iOS、语音网关或火山密钥配置。沿用已确认角色与[分镜](mia-launch-animation-plan.md)，没有替换 Live2D。真实 MiniMax 鉴权、生成质量与最终 App 衔接尚待验证。

## 协议依据与生成参数

- [官方创建接口](https://platform.minimax.cn/docs/api-reference/video-generation-v2-create)：`POST https://api.minimax.cn/v2/video_generation`，Bearer 鉴权。
- [官方查询接口](https://platform.minimax.cn/docs/api-reference/video-generation-v2-query)：`GET /v2/query/video_generation/{task_id}`；查询近七天任务。
- 图片项使用 `{"type":"image_url","image_url":{"url":"HTTPS 地址"},"role":"first_frame"}`；尾帧 role 为 `last_frame`。首尾帧不能与独立参考媒体混用，本工具仅实现首尾帧模式。
- 默认 `MiniMax-H3`、5 秒、`768P`、`ratio=adaptive`、`aigc_watermark=false`。使用现有 933×1686 首尾图，不能宣称输出必为严格 9:16；实际比例以查询和下载文件为准。
- [提示词](design/launch/mia-minimax-prompt.txt)沿用粒子凝聚、35 度旋身、指尖光弧与最终姿态，明确末帧中的 Mia 定义身份。不会把带水印且造型漂移的 OpenArt 预览作为参考。
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

请在当前工作环境的交互终端运行。临时入口不随 Git 保存；换环境后用上方 Python 完整命令重新配置。密钥仍位于仓库外 `~/.config/mia/minimax.key`，不进入 iOS 或火山语音服务。

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

离线测试覆盖请求字段、鉴权、错误正文隐藏、不重试付费请求、查询、等待终止与超时、下载与文件保护、0600 Key、交互输入以及付费确认与状态保留。CI 不配置真实 Key，不创建付费任务。

```bash
/root/projects/Mia/.venv/bin/python -m unittest scripts.video_tests.test_mia_minimax_video -v
```

提交 `554c302` 的 [CI](https://github.com/bboytang/Mia/actions/runs/37202954070)已通过 14 项测试和离线请求准备。本地另有 98 项固件测试、23 项服务端测试通过（后者需允许绑定本地测试套接字）。

真实调用待用户在当前环境隐藏配置 Key，并确认单次预算。下载完成后检查实际分辨率、时长、帧率、音轨、水印、Mia 造型和动作，再验证首页衔接。当前无合格正式 `MiaLaunch.mp4`，不得标记启动动画完成。
