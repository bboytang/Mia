# 官方与现网差异核对

核对时间：2026-10-14。官方最新稳定发布仍为 v0.9.7；本次固定主分支提交
`27399a2fb64b5910196f438a256ce0a9f868481f`，不跟随浮动 main 自动升级。
现网基础提交为 `87c6df77b0220ddbd8fc804f984f83f69f3225e5`，另有 Mia 定制。

| 范围 | 核对结果与处理 |
| --- | --- |
| manager-mobile | uni-app / Vue 3 / Vite 独立移动前端；本版本区间无变更。参考设备卡片、角色配置、聊天详情交互，保持原 Vue 2 / Element UI 统一后台，不部署第二套前端。移动端未覆盖桌面全部管理员路由。 |
| manager-api / 数据库 | 两个固定提交之间无源码变更、无新增数据库迁移。保留现网 JAR 与 Mia 认证扩展。 |
| manager-web | 官方新增弹窗生命周期及尺寸修复、筛选、召回表单回车修复、登录路由修复。合入 `server/admin_web/production-dialogs.patch`，响应式改造继续叠加其上。还需核验运行产物与桌面基线差异。 |
| HTTP 客户端 | 现网文件 SHA256 与 v0.9.7 一致，缺少请求级客户端关闭、重试复用和 shutdown 中断修复。 |
| FunASR / SenseVoice | 现网与 v0.9.7 一致，缺少 content 正文提取和中日文字间空格处理。 |
| TTS | 现网与 v0.9.7 一致，缺少引号内分句保护及 Edge TTS 新服务地址修复。 |
| requirements.txt | 现网文件 SHA256 已与本次官方提交一致，不重复改依赖。已只读核实运行包 `httpx 0.28.1` 与 `edge-tts 7.2.8`，与官方补丁依赖一致；其他包仍不能仅凭清单认定安装一致。 |
| Mia 定制 | 记忆、情绪、主人认证、音乐精确匹配均保留，不覆盖 connection.py、sendAudioHandle.py、dialogue.py、Java ConfigServiceImpl 或插件。 |
| CI / 基础镜像 | 官方 Dependabot、PyPI metadata 回退及基础镜像依赖调整属于构建维护，不作为缺失业务功能移植到现网。 |

`official.patch` 仅包含五个已核实缺失修复的文件，与上述官方提交逐字匹配。
`files.json` 包含移植前后 SHA256。对隔离源码目录执行：

```sh
python3 server/upstream_fixes/apply.py /path/to/source
python3 server/upstream_fixes/apply.py /path/to/source --apply
```

默认只检查。已有定制或已安装修复时拒绝覆盖；不重启服务、不访问数据库。
GitHub Actions 使用官方生命周期、ASR 和 TTS 回归用例，以及 FunASR 正文进入意图/STT/聊天、声纹首次称呼不变的回归用例，禁止真实 API 调用；Edge TTS 仅检查模块加载及地址，不声称验证微软线上发声。

部署需以发布前现网语音镜像为基础，只覆盖验证产物中的五个文件，保留环境、挂载与其他源码。先记录原镜像 ID、文件校验和及当前三份 Compose；核对 `httpx` 和 `edge_tts` 版本；隔离验证后再切换语音镜像。重建语音容器会中断当前设备连接，应在设备空闲时发布。回滚恢复本次原镜像及 Compose，不回滚数据库，不删除记忆。当前尚未部署这些补丁，仍需实际设备验证 ASR、TTS、打断和重连。

官方对照：[移动端源码](https://github.com/xinnan-tech/xiaozhi-esp32-server/tree/27399a2fb64b5910196f438a256ce0a9f868481f/main/manager-mobile)、[完整提交差异](https://github.com/xinnan-tech/xiaozhi-esp32-server/compare/87c6df77b0220ddbd8fc804f984f83f69f3225e5...27399a2fb64b5910196f438a256ce0a9f868481f)、[v0.9.7 发布](https://github.com/xinnan-tech/xiaozhi-esp32-server/releases/tag/v0.9.7)。
