# Youmi 后端

当前运行方式是在外部后端上安装 `companion/` 扩展，统一提供授权、长期记忆、性格、持续情绪和后台管理。客户端与已授权设备共用服务端状态。

| 目录或模块 | 内容 |
| --- | --- |
| `companion/` | 性格、情绪、记忆、检索、上下文与模型任务 |
| `companion/manager_identity/` | 管理服务的授权与配置接口 |
| `admin_web/` | 后台界面及源代码补丁 |
| `tests/` | 服务与扩展回归测试 |
| `upstream_fixes/` | 上游集成修正 |
| `deploy/` | 独立网关的安装模板 |
| `mock_youmi.py` | 本地协议夹具 |
| `youmi_gateway.py` | 独立网关实现 |

扩展安装入口：

```sh
python3 -m server.companion.install_youmi /path/to/backend --apply
python3 -m server.companion.install_identity /path/to/backend --apply
python3 server/admin_web/apply.py /path/to/backend --apply
```

回归检查：

```sh
python3 -m unittest discover -s server/tests -v
```

[当前部署](../docs/youmi/backend/persona-deployment.md) · [安装与授权](../docs/youmi/backend/companion-backend.md) · [独立网关历史记录](../docs/youmi/history/standalone-gateway.md)
