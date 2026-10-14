# P02 环境与访问核对

核对：2026-10-14；源码基线 `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`。仅记录实际读取结果，不含凭据。

## 开发环境

| 项目 | 实际结果 | 对后续工作的影响 |
| --- | --- | --- |
| Git | 2.43.0 | 可本地创建独立分支及定向提交 |
| Python | 3.12.3 | 本地仅阅读、编辑与差异检查；不本地执行软件测试 |
| gh | 2.45.0 | 受限 shell 认证失败；允许网络执行环境实际 API 可用，未重新登录 |
| Java／Maven | 未安装 | 使用 GitHub Java 21 构建与集成验证，不把本地缺失作为不验证理由 |
| Docker | CLI 29.1.3；受限 shell 无 daemon 权限 | 当前无需本地容器；后续实验在 GitHub 隔离环境执行 |
| Xcode／XcodeGen | 未安装 | iOS 使用现有 macOS Actions，真机另行验收 |
| Python 协议依赖 | 当前 shell 未安装 websockets／httpx／aiohttp | 不在本机安装来替代 GitHub 测试 |
| 云状态工具／策略快照 | 当前未提供 environment_status 工具，`/etc/codex/network-policy.json` 不存在 | 不推断密钥就绪或网络政策；按实际命令和许可范围核实 |

## 实际访问

- GitHub 仓库 `bboytang/Mia`：允许网络执行环境的 `git ls-remote` 和 repository API 成功，实际读取和推送权限存在；具体内容推送另受本次审批状态约束。
- Actions：已列出并核实 `mia-server.yml`、`ios.yml`、`mia-upstream-fixes.yml` 等既有 active 工作流；基础运行环境分别为 Python 3.12、macOS 15、Python 3.10。
- repository Actions secrets API：当前 `total_count=0`。这是仓库 secrets 结果，不代表 organization／environment secrets 或生产模型凭据不存在。真实 Provider 行为 job 的凭据来源仍需确定。
- 2026-10-14 用户选择专用测试凭据配置到 GitHub Actions Secret；不复用／转移生产模型密钥。测试 Secret 名称及入口待建立，尚未配置或调用真实聊天 Provider；不能因来源方案确认就标凭据可用。
- 服务器：原已配置 SSH 身份、BatchMode 和严格主机校验下 `root@43.143.230.174` 只读连接成功。未新增 key、未改 authorized_keys，未执行部署。
- 真机及签名：尚未验证可用；用户设备上的具体操作仍需设备证据。

## 运行环境

- 当前语音镜像：`mia-xiaozhi-server:responsive-20261014T134645Z-a30a508`。
- 当前管理镜像：`mia-xiaozhi-web:responsive-20261014T134645Z-a30a508`。
- CPU 2 核，物理内存 1941 MiB，swap 4095 MiB；这是只读快照，不表示峰值资源或新方案已经足够。
- 语音 Python 3.10.22；Java OpenJDK 21.0.12.1。
- 语音工作目录 `/opt/xiaozhi-esp32-server`；现有数据卷 `/opt/xiaozhi-server/data` 挂载到其 `data`；音乐精确匹配补丁是单文件挂载。
- 包版本、指定源码校验值和 SQLite 表字段见 [运行基线](runtime-baseline-20261014.json)。没有读取用户事实、令牌或模型密钥。

## 尚缺与处理

1. 真实模型／embedding 测试的受保护凭据来源：先评估不依赖远程密钥的本地开源 embedding 候选；真实聊天 Provider 仍需要安全接入，不以 mock 代替验收。
2. Java 身份集成 workflow：现有协议 workflow 尚不证明真实 Java 签发／绑定，需要 P07 按固定上游补充。
3. iOS 真机与签名：后续记录实际访问方式及测试版本，不影响服务器契约和代码准备。
4. 文档推送：自动审批最初要求明确目的地；用户已回复允许推送到该仓库和任务分支。首份计划提交已推送并独立检出验证，没有绕过拒绝执行其他上传方式。

这些缺项只影响相应后续步骤；网络可用、SSH 可用、workflow 可访问和凭据名称查询不等于已完成真实行为验收。
