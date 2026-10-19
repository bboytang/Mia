# 后台记忆管理与服务端地址

服务端管理地址来自 `sys_params.server.websocket`，同时供管理命令建立连接使用。启用直连 TLS 后必须配置 `wss://43.143.230.174:8000/xiaozhi/v1/`，不能只改页面文案。通过既有参数管理 API 更新，确保数据库和 Redis 缓存一致。

管理命令不属于私人设备会话。连接路由在私人设备绑定检查之前，只接收 TLS 上、服务端密钥正确的 `server/update_config` 与 `server/restart`，交由原有处理器执行；不授予私人身份、记忆或聊天权限。普通设备消息仍走原授权检查。

后台首页每个智能体新增“记忆管理”，通过既有登录鉴权和逐次所有权检查查看当前智能体的记忆。服务端每页最多 50 条，支持翻页；正文以文本显示。逐条删除必须确认，并沿用 `MemoryStore.delete_memory`：撤回来源、检索及相关衍生记录，更新上下文版本并取消旧任务。界面只在服务端确认后报告成功；结果未知时要求刷新。关闭弹窗或切换智能体会丢弃旧响应。

不修改用户角色、模型、设备授权或情绪开关。生产验收只读取真实记忆，删除在隔离测试数据库和浏览器模拟服务中验证，不拿用户记忆做删除测试。

上线与验证（2026-10-19）：代码提交 `f9423397de245a68234d0c3b7e5deacea1d9ba9e`，线上镜像 `mia-xiaozhi-server:memory-admin-f942339`、`mia-youmi-web:memory-admin-f942339`。沿用全部六份 Compose 配置，无新增数据备份，无数据库迁移。旧连接路由源码的 SHA-256 为 `a454966147c32057fc91327d11e86160bf422d383966d0adc4a6e3e996aae6f6`，与移除本次控制命令入口后的源码一致；JAR 仅替换一个管理接口类，其他条目逐一核对未变。30 个后端文件、442 个前端文件及 JAR 均与部署清单一致。

通过真实后台登录调用 `/admin/server/server-list`，读回 WSS 地址；调用 `/admin/server/emit-action` 执行 `update_config`，收到成功确认。通过当前智能体的管理接口读取 47 条真实记忆，内容不写入验收报告。部署前后 47 条记忆、47 个向量与来源等数据指纹相同，SQLite V6 完整性检查通过。角色、模型、声音及原有开关不变。未执行真实记忆删除或控制命令重启；删除与重启命令授权在隔离测试中验证。此次未更改固件，未重新进行实机音频验收。

同一提交的 GitHub Actions 验证：

- [后端协议与完整 Python 测试：393 项通过](https://github.com/bboytang/Mia/actions/runs/39263152891)。
- [Java 完整套件与授权验证：181 项通过](https://github.com/bboytang/Mia/actions/runs/39263152873)。
- [前端构建与四种浏览器：92 项通过](https://github.com/bboytang/Mia/actions/runs/39263152774)。
- [Manager 基线验证](https://github.com/bboytang/Mia/actions/runs/39263152856)。
- [真实语义向量与上下文验证](https://github.com/bboytang/Mia/actions/runs/39263152600)。

脱敏线上验收记录见 [verification/mia-console-memory-management](../../verification/mia-console-memory-management)。
