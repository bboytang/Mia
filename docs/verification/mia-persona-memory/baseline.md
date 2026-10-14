# P03 固定基线与补丁保留清单

核对日期：2026-10-14。D01：任务分支 `feature/mia-persona-memory-v1.2`，源码基础 `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`；首份计划保存提交 `d74b89acc0973502234724fba0e681b112985eeb`。后续代码与验证使用任务分支，不重置其他分支。

## 固定上游与运行组合

P09只读补充复核：实际语音容器为 `xiaozhi-esp32-server`，管理为 `xiaozhi-esp32-server-web`，镜像标签仍与下列基线一致；一次简称 `xiaozhi-server` 查询未找到容器，不据此判断现网变更。运行 `core/websocket_server.py` SHA256为 `e46fc6a0d1b268953cd6fdcf9cb10aaf89b17f8612d611c33201a6303eb31505`，与新增必要原生TLS补丁preimage一致。只读取容器元数据与此源码哈希，未读秘密／用户事实或修改服务。

- 上游基础：`xinnan-tech/xiaozhi-esp32-server`，`87c6df77b0220ddbd8fc804f984f83f69f3225e5`（v0.9.7）。
- 已移植的官方修复来源：`27399a2fb64b5910196f438a256ce0a9f868481f`。五文件列表及前／后校验值由 `server/upstream_fixes/files.json` 管理。
- 路遥仅为行为与缺陷参考：`insistgang/Luyao_AI_Project`，`e23c3aa25d6451e3f35e71609864bb3a54ad49a0`；不复制未获复用授权的业务代码或预置剧情。
- 实际语音镜像 ID：`sha256:6b0837039f255a0b80afdb603445d4e8fce44556fa2146d0bb6d71503e169534`，标签 `mia-xiaozhi-server:responsive-20261014T134645Z-a30a508`。
- 实际管理镜像 ID：`sha256:dfa6885dbb9122cbf91a3988c74d5edb9e2c00b4fad97a913ce0c2a0647bebe9`，标签 `mia-xiaozhi-web:responsive-20261014T134645Z-a30a508`。

运行文件、包及表字段：[Python／SQLite 基线](runtime-baseline-20261014.json)。管理服务指定类：[Java 二进制基线](manager-baseline-20261014.json)。全部是只读采集；未读取用户事实／密钥，未修改运行服务。

## 已实际比对的内容

1. `mia_companion/__init__.py`、`memory.py`、`xiaozhi_adapter.py` 的运行 SHA256 与任务源码基础的三个对应文件完全一致。
2. 五项官方 Python 修复的运行 SHA256 与 `files.json` 的 `after` 完全一致，不能把它们当作尚未上线而重做。
3. `play_music.py` 的运行 SHA256 为 `6fe21451135ceb3cad6131a99e60a9cb1eee042bab4b3006cab954ee62b4ead5`，现有只读单文件挂载继续保留。
4. 当前 SQLite 是原 owners／memories／sources／traits／checkpoints 结构，尚没有本次任务的向量、持久任务、持续事件或授权情绪表。
5. 管理 JAR 中 ShiroConfig、OTAController、DeviceServiceImpl、ConfigServiceImpl 的 class 校验值已冻结。当前仅冻结二进制；与新增真实 Java 构建逐字节比较留在 P07，不将旧审计结论视为本轮重新构建结果。

## 重建和升级规则

从固定上游 checkout 重建 Mia companion 钩子，保留现有自然记忆适配器，再组合现有官方五文件修复、音乐挂载及管理前端补丁。补丁入口均在仓库，不依赖本机 `/tmp`。

现有 `server/companion/install_xiaozhi.py` 只接受干净上游四文件，已经安装时拒绝覆盖。**不得直接对现网运行 `--apply`，不得恢复成干净上游来凑 hash。** P10／P24 需要显式升级路径及完整补丁组合验证；没有迁移／回滚证据前不发布。

管理员权限和身份链判断仍需 P05／P08 的真实 Java 集成验证。现有 owner 过滤及模拟 Bearer 测试不证明签发安全。HTTPS／WSS 实际入口尚待核实，App 代码默认仍为 HTTP／WS；不声称 TLS 已安全落实。

## 精确基线已有 GitHub 证据

以下均为源码基础 `a30a5081bfa3c08e7387b9f5d9be77bd957e8175`，只证明已有基线，不证明 V1.2 新功能。

- [服务端回归](https://github.com/bboytang/Mia/actions/runs/38573040834)：success。
- [官方修复验证](https://github.com/bboytang/Mia/actions/runs/38573040806)：success。
- [管理后台构建与测试](https://github.com/bboytang/Mia/actions/runs/38573041129)：success。
- [本次启动的服务端基线](https://github.com/bboytang/Mia/actions/runs/38582489146)：success；查询已有结果和 dispatch 在同一命令中，导致一次无必要重复。发现后尝试取消时已完成；以后先读取已有证据，再决定是否运行。

本次没有修改 iOS，不重复运行不受影响的原生构建；必要客户端变更后使用对应新 SHA 验证。未在开发机或生产服务器执行自动化软件测试／构建。
