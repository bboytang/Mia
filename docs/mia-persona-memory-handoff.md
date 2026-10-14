# Mia 人格认知与长期记忆：接续入口

更新：2026-10-14。方案：[V1.2](mia-persona-memory-v1.2.md)。完整步骤：[实施计划](mia-persona-memory-implementation.md)。事实记录：[工作记录](mia-persona-memory-worklog.md)。

## 当前范围与状态

当前用户要求：**“开始计划吧，每完成一步就写交接和进度”。** 已授权按 V1.2 和完整计划开始开发，并在每一步结束更新交接和工作记录。先前“仅修订计划”的限制已由本次开始执行指令解除；生产发布仍按 P26／P27 的具体制品、验证与授权范围处理。

P00—P06已完成准备及模型初选：固定BGE base中文U8U8 ONNX／768维＋SQLite真向量精确检索；P07身份基线部分完成。P08／P09必要授权、manager→Python及隔离实际HTTPS/WSS共18身份用例／构建通过；App100单测／5UI及构建、智控台53单测／64浏览器及构建通过，证据已保存。原意图／逐工具派发／输入及管理隔离已通过f4a7f4c的GitHub验证；旧report／标题／摘要必要链新增守卫待本提交CI。实际App↔manager HTTPS/WSS、iPhone、持久任务、全服务并发／资源及八项行为仍未验，完整Java回归保留唯一既有失败；未部署。

四项不可削减要求：核心机制完整、真正向量＋关联＋四维 RAG、必要身份链整改而非系统重构、八项真实行为验收。保持单回复链、单事实库、可信 Scope、统一上下文和轻量持久任务；长期情绪默认关闭。

## 本地保存情况

- 仓库：`bboytang/Mia`，本机目录仅供定位，不是跨设备依赖。
- 任务分支：`feature/mia-persona-memory-v1.2`，从已核实远程一致的 `feature/admin-responsive`／`a30a5081bfa3c08e7387b9f5d9be77bd957e8175` 创建。原分支保留。
- V1.1 历史基线：Mia `31aeb6fe60a3ed81fb935b16a844c7a447b7f1df`、路遥 `e23c3aa25d6451e3f35e71609864bb3a54ad49a0`、小智 v0.9.7。
- 四份文档首份保存提交 `d74b89acc0973502234724fba0e681b112985eeb` 已推送到任务分支，从独立目录检出相同 SHA 并逐文件比对一致。后续进度随任务提交保存。
- P03 的 D01 及实际上游／运行补丁已冻结，见[基线证据](verification/mia-persona-memory/baseline.md)。P07 首轮 Java 编译及四类字节对照通过；复核实际执行 150 测试，149 通过、1 既有脱敏测试失败，详见 [Java CI](verification/mia-persona-memory/manager-ci.md)。不能称完整测试通过。
- 仓库文档是完整任务入口，后续无需读取原对话。旧 `/tmp` 审计源码不是必须传递的材料，可以从固定来源重建。

## 下一步

当前步骤：**P09 可信 Scope 贯通**，P08 的客户端／入口与 P07 剩余真实 Provider 条件继续推进。用户已确认旧设备缺私有授权时提示“请用智控台授权码完成授权”，保留 ID／绑定，暂不加载个性化语音配置，授权后恢复；不增加公共语音回退。私有 Agent 配置及纠错词也必须验证私有凭据。[开发契约](verification/mia-persona-memory/contracts.md)已同步；实际 TLS 部署尚未执行。

下一步：核实旧聊天report／标题／摘要Scope守卫的本提交CI，特别是模型期间撤销／改绑不落库；见[必要链证据](verification/mia-persona-memory/private-chat-authorization.md)。f4a7f4c／38637255419的18身份及管理隔离已通过，完整168中167通过／1既有失败，构建及类范围通过，已归档scope-management-results.json。已通过的 [实际TLS](verification/mia-persona-memory/private-tls.md)、[App必要迁移](verification/mia-persona-memory/ios-private-authorization.md)、[智控台入口](verification/mia-persona-memory/console-private-authorization.md)证据可从仓库恢复，不依赖本机制品目录。随后P09剩余真实App整链／并发与P10 schema等按计划依赖推进，资源门槛不可省略。生产仍无公开TLS／证书配置变更，原生WSS支持已开发；代理方案若需要须独立审核。P06 [固定规格](verification/mia-persona-memory/embedding-selection.json)已冻结；[专用真实Provider入口](verification/mia-persona-memory/live-provider.md)语法通过、真实调用未执行，最新测试Secret名称仍为0。先查在途Actions，避免重复运行。

## 步骤状态

| 步骤 | 状态 | 当前事实／恢复动作 |
| --- | --- | --- |
| P00 | 完成 | V1.2、计划、交接和工作记录已编写；仅文档 |
| P01 | 完成 | d74b89a 已推送，独立 checkout 与四文件比对通过 |
| P02 | 完成 | [环境与访问](verification/mia-persona-memory/environment.md)已核实；后续真实模型／真机缺项分别记录 |
| P03 | 完成 | [固定基线](verification/mia-persona-memory/baseline.md)及运行文件／Java class 校验值已保存 |
| P04 | 完成 | [验收 v1.1](verification/mia-persona-memory/acceptance.md)：数值不变，按用户确认区分无关与相关不可回答 |
| P05 | 完成 | [契约 v1](verification/mia-persona-memory/contracts.md)；授权码路径确认，TLS 实际发布与真实身份验收尚未执行 |
| P06 | 完成：初选 | [固定规格](verification/mia-persona-memory/embedding-selection.json)，U8U8 base 达初选门槛；生产集成和行为未验收 |
| P07 | 进行中 | 身份基线部分完成：编译／四类对照及4真实旧缺口复现通过；完整回归149/150，1既有失败；Provider等入口未完成 |
| P08 | 开发／隔离部分通过 | 18真实身份（含HTTPS/WSS）及构建、App100＋5和构建、智控台53＋64和构建通过；真实App↔manager与生产证书／入口／iPhone仍待验，整体未封板 |
| P09 | 基础通过，整体进行中 | fc00fce的原意图／输入／实际安装ToolManager及18真实身份／TLS通过；新增索引／事件／趋势／持久任务逐模块补Scope证据，整体与真实App／资源待验 |
| P10 | 开始 | 按依赖细化启动兼容schema，保留旧表形状／ID／owner／confirmed语义，后续用GitHub证明升级／中断／回滚写入 |

当前补充：管理请求Scope不匹配拒绝、跨范围ID删除、凭据过滤与实际SQLite隔离已在f4a7f4c通过GitHub。旧会话report／标题／摘要的Scope快照、执行复查及短事务提交保护已编写，5项真实manager／隔离DB验证待本提交CI；模型仅合成桩。schema尚未编辑，先完成此必要链。
| P11—P15 | 未开始 | 人格、完整 RAG、上下文与唯一入口未实施 |
| P16—P18 | 未开始 | 持久任务、完整提取与维护未实施 |
| P19—P20 | 未开始 | 持续人格事件与授权趋势未实施 |
| P21—P26 | 未开始 | 必要管理、真实行为、性能、回归、真机及发布包待实施 |
| P27—P28 | 未开始 | 未发布，不能凭计划执行生产变更 |

## 八项能力状态

此表只记录本次 V1.2 目标，Mia 已有基础能力不因此判作不存在。

| 能力 | 代码 | 机制验证 | 真实行为 | 真机相关项 |
| --- | --- | --- | --- | --- |
| B01 人格对话引擎 | 未开始 | 未执行 | 未执行 | 未执行 |
| B02 长期记忆 RAG | 未开始 | 未执行 | 未执行 | 未执行 |
| B03 异步记忆提取 | 未开始 | 未执行 | 未执行 | 未执行 |
| B04 四维检索 | 未开始 | 未执行 | 未执行 | 未执行 |
| B05 持续人格事件 | 未开始 | 未执行 | 未执行 | 未执行 |
| B06 身份与记忆隔离 | 进行中：manager授权链 | 必要类范围／构建通过 | manager14用例通过；语音／后台隔离未验收 | 未执行 |
| B07 长期情绪趋势 | 未开始 | 未执行 | 未执行 | 未执行 |
| B08 上下文管理 | 未开始 | 未执行 | 未执行 | 未执行 |

## 待决与访问状态

D01—D10 已冻结开发契约及初选；D03／D04 见固定模型规格，用户已确认授权码、情绪保留及相关不可回答边界。生产完整RAG、私有安全链及长期趋势行为仍未验收，初选参数在最终独立用户语料验收不合格时需有新证据重评。

GitHub读取／推送、Actions和严格主机校验的只读SSH已验证；未改变凭据。仓库／Environment此前核实没有测试秘密配置，用户现已选择专用测试Secret，实际配置及真机／签名仍未具备或未确认。新环境重新验证实际访问，不复制秘密进交接。

用户已确认真实聊天测试使用专用GitHub Actions Secret；入口已编写，实际配置和调用仍未核实／执行。三个配置名见Provider入口文档，保留生产模型密钥原位置；新环境只核实秘密配置名和可用状态，不输出秘密。

缺权限时：继续不依赖它的已授权工作；相应真实测试或远程动作记为未执行／阻塞。不得关闭认证、改用任意 owner、重新启用旧网关或输出密钥来绕过。

## 新会话可直接使用的接续说明

将以下文字与可访问的仓库版本一起交给新开发设备／环境／账号；它不能取代用户对当前工作范围的授权。

```text
请接续 Mia 人格认知与长期记忆 V1.2 项目。

先读 AGENTS.md，然后依次读取：
docs/mia-persona-memory-handoff.md
docs/mia-persona-memory-v1.2.md
docs/mia-persona-memory-implementation.md
docs/mia-persona-memory-worklog.md

先检查当前分支、SHA、工作树、文档保存情况及实际访问权限。
依据交接确认已完成步骤、证据和下一步，不依赖旧聊天或临时目录。
在我本次明确的工作范围内，执行第一项前置条件满足的未完成步骤。
不要因缺凭据降低实现标准，不要覆盖无关工作。
完整保留核心机制与八项真实验收，所有软件自动化测试和构建在 GitHub Actions。
每个工作段结束更新工作记录和交接，记录实际提交、run、结果和剩余项。
若当前范围仍只修订计划，不开始修改代码、调用模型或部署。
```

每次接续更新此文件的当前范围、基线、下一步和证据定位；历史事实只追加到工作记录，不让“当前下一步”长期保留过期信息。
