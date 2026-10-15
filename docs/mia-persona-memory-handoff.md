# Mia 人格认知与长期记忆：接续入口

更新：2026-10-15。方案：[V1.2](mia-persona-memory-v1.2.md)。完整步骤：[实施计划](mia-persona-memory-implementation.md)。事实记录：[工作记录](mia-persona-memory-worklog.md)。

## 当前范围与状态

当前用户最新要求：**“继续下一步”。** 本段P15唯一回复入口及工具续答受控接线验证通过，下一步P16统一完成事件与持久任务生命周期。实际Provider容量与输出预留仍未核实，保持限制，不部署。此前要求为“开始计划吧，每完成一步就写交接和进度”；继续按 V1.2 和完整计划开发，并在每一步结束更新交接和工作记录。先前“仅修订计划”和“先保存”的暂停范围已由接续指令解除；生产发布仍按 P26／P27 的具体制品、验证与授权范围处理。

P00—P06已完成准备及模型初选：固定BGE base中文U8U8 ONNX／768维＋SQLite真向量精确检索；P07身份基线部分完成。P08／P09必要授权、manager→Python及隔离实际HTTPS/WSS共18身份用例／构建通过；App100单测／5UI及构建、智控台53单测／64浏览器及构建通过，证据已保存。原意图／逐工具派发／输入及管理隔离已通过f4a7f4c的GitHub验证；旧report／标题／摘要新增5项及原18项在3cb7b3c通过，构建通过，P10兼容迁移6项与104服务测试在426d8c4通过，23身份／TLS及构建同提交通过；已归档。实际App↔manager HTTPS/WSS、iPhone、持久任务、全服务并发／资源及八项行为仍未验，既有Java脱敏测试预期已在74794e0修正并通过完整回归（历史失败保留）；P11基础113服务、23身份及三个限定原Provider样本通过，完整人格仍待联动验收，未部署。

四项不可削减要求：核心机制完整、真正向量＋关联＋四维 RAG、必要身份链整改而非系统重构、八项真实行为验收。保持单回复链、单事实库、可信 Scope、统一上下文和轻量持久任务；长期情绪默认关闭。

## 本地保存情况

- 仓库：`bboytang/Mia`，本机目录仅供定位，不是跨设备依赖。
- 任务分支：`feature/mia-persona-memory-v1.2`，从已核实远程一致的 `feature/admin-responsive`／`a30a5081bfa3c08e7387b9f5d9be77bd957e8175` 创建。原分支保留。
- V1.1 历史基线：Mia `31aeb6fe60a3ed81fb935b16a844c7a447b7f1df`、路遥 `e23c3aa25d6451e3f35e71609864bb3a54ad49a0`、小智 v0.9.7。
- 四份文档首份保存提交 `d74b89acc0973502234724fba0e681b112985eeb` 已推送到任务分支，从独立目录检出相同 SHA 并逐文件比对一致。后续进度随任务提交保存。
- P03 的 D01 及实际上游／运行补丁已冻结，见[基线证据](verification/mia-persona-memory/baseline.md)。P07 首轮 Java 编译及四类字节对照通过；复核实际执行 150 测试，149 通过、1 既有脱敏测试失败，详见 [Java CI](verification/mia-persona-memory/manager-ci.md)。不能称完整测试通过。
- 仓库文档是完整任务入口，后续无需读取原对话。旧 `/tmp` 审计源码不是必须传递的材料，可以从固定来源重建。

## 下一步

当前步骤：**P16开发及首次GitHub验证准备**，见[持久任务说明](verification/mia-persona-memory/jobs.md)；P15接线模块及受控验证已通过，见[唯一回复接入说明](verification/mia-persona-memory/reply.md)。此前推送阻塞已在本轮正常审批后解除，未绕过审批。P14模块验证通过，见[上下文说明及结果](verification/mia-persona-memory/context.md)。P13模块与受控验证通过，见[四维检索说明](verification/mia-persona-memory/hybrid-retrieval.md)、[D04规格](verification/mia-persona-memory/retrieval-selection.json)。P11基础通过，完整Persona联动仍进行中；P12—P14整体仍待主链及真实manager＋BGE＋Provider联动验收。P08实际App／入口及真机未封板，未部署。

当前Java补充验证：用户追问脱敏失败原因和修复后，`74794e02c786f6f01389bdbc3d96b30911af4c5c`仅修正固定上游测试后缀预期`3123`→`e123`及两CI补丁接入，不改运行代码。新[身份38755588258](https://github.com/bboytang/Mia/actions/runs/38755588258)173／173、脱敏9／9、23专项／TLS、类范围和JAR通过；[manager38755588374](https://github.com/bboytang/Mia/actions/runs/38755588374)150／150＋独立4／4与字节对照通过；[服务38755588299](https://github.com/bboytang/Mia/actions/runs/38755588299)157／157通过，三workflow均success。见[原因及修复](verification/mia-persona-memory/manager-ci.md)、[精确结果](verification/mia-persona-memory/redaction-ci-results.json)。历史失败原报告不改；此前“唯一既有失败”对旧run仍成立，对当前修正后的Java回归已解除。无本地自动测试／构建、部署或在途run，下一步仍P16。

P15接线验证提交：`5c6e81438fc3bb1e91e0f008c2bfc7f3f5fd3788`，服务[38754547193](https://github.com/bboytang/Mia/actions/runs/38754547193)157项通过；真实BGE接线[38754546905](https://github.com/bboytang/Mia/actions/runs/38754546905)通过P12—P14回归及P15的7场景，合成SDK请求9次、工具派发5次，文字／ASR识别文本／多步并行工具／direct_answer／删除不重放／缺容量／撤权通过。实际manager身份[38754547230](https://github.com/bboytang/Mia/actions/runs/38754547230)23专项、实际TLS与reply Scope／删除／撤权、类范围及JAR通过；Java全量173中172通过，manager基线[38754547323](https://github.com/bboytang/Mia/actions/runs/38754547323)154中153通过，均仅既有脱敏失败，两个workflow整体failure。Dockerfile变更自动触发的嵌入比较[38754546954](https://github.com/bboytang/Mia/actions/runs/38754546954)通过，未改变模型选择。原报告／hash及分项范围见[本轮CI](verification/mia-persona-memory/reply-ci-results.json)、[接线原报告](verification/mia-persona-memory/reply-results.json)、[身份原报告](verification/mia-persona-memory/reply-identity-results.json)。所有run已完成，无在途操作。实际聊天请求0、无本地自动测试／构建、未部署；真实Provider容量／输出、Token、声学／真机及完整B08仍未验收。

P14历史验证提交：`5e91409bbc9da69b0c7085837e7014ce24e3bc04`，服务[38732848387](https://github.com/bboytang/Mia/actions/runs/38732848387)145项通过；实际BGE [38732848548](https://github.com/bboytang/Mia/actions/runs/38732848548)的P12／P13回归及P14安装包／原Dialogue／上下文10工具场景通过，50次build p95 34.959ms、峰值RSS283.887MiB。ContextBundle固定CORE与数据层分离、当前问题／完整工具优先、20轮及字节估算预算、权限及三项快照复查；历史／源字典不变、删除重建、无效特点不入、未知容量明确拒绝。报告见[context-results.json](verification/mia-persona-memory/context-results.json)。容量profile和工具结果为CI夹具，未调用聊天Provider，不是实际窗口、精确Token或完整B08证据。

同提交身份[38732848576](https://github.com/bboytang/Mia/actions/runs/38732848576)23专项／实际TLS、ContextBuilder本人／外人隔离、删除和撤权、类范围及JAR通过；完整173中172通过／1既有脱敏失败，workflow整体failure。manager基线[38732848453](https://github.com/bboytang/Mia/actions/runs/38732848453)154中153通过、仅同一失败。见[本轮CI范围](verification/mia-persona-memory/context-ci-results.json)及[身份原报告](verification/mia-persona-memory/context-identity-results.json)。所有软件自动化仅GitHub，无本地测试或部署。

P13验证提交`664237ff1b15837fc1b752bf869e02d6281669fa`服务132、真实BGE／四维正负控制通过，独立P13-v1的32正向及16无关全正确。1万短文本缺元数据容量p95 237.778ms、RSS283.379MiB，不能外推长元数据或并发；见[原结果](verification/mia-persona-memory/hybrid-results-summary.json)。两个失败原报告保留，未改参数或质量留出。P14同job继续回归通过，见[新回归摘要](verification/mia-persona-memory/context-regression-summary.json)。

同提交身份[38727000802](https://github.com/bboytang/Mia/actions/runs/38727000802)专项／实际TLS、混合Scope、类范围和JAR通过；Java全量仍有既有脱敏失败，workflow整体failure，不能写全部CI通过。见[分项CI范围](verification/mia-persona-memory/hybrid-ci-results.json)和[身份报告](verification/mia-persona-memory/hybrid-identity-results.json)。运行包最初在5680f6f实现，此后只加验证和证据，包Git tree为2308843983e37bf1fc40acbb0e35172d0fa05243。

P12补充生命周期提交`d5edbd6a4b4b4bcef67a715ef97c4a42690fca64`服务125项通过，覆盖超时／迟到提交、编辑／删除／清空／暂停竞态、扫描后撤权、推理故障及重开／重建；见[vectors-lifecycle-results.json](verification/mia-persona-memory/vectors-lifecycle-results.json)。不重复这些已通过检查。

P11已验证源码 `232de0d2fc5250a42f9802a2bbd470e9866d5c18`：服务[38662376416](https://github.com/bboytang/Mia/actions/runs/38662376416)全部113通过；身份[38662376430](https://github.com/bboytang/Mia/actions/runs/38662376430)的23专项／实际TLS、JAR／类范围通过，完整173中172通过／1既有脱敏失败。固定原Provider流式[38662470670](https://github.com/bboytang/Mia/actions/runs/38662470670)三个基础样本经本轮Codex逐条语义检查通过。见[Persona机制与全部边界](verification/mia-persona-memory/persona.md)、服务／身份／Provider JSON；失败和自动假阳性也保留，不能据绿色workflow或三样本标完整B01／八项完成。

P11基础实装：固定核心与JSON角色数据、DB故障／空角色保留核心、输入已知攻击提前回应、共享TTS队列句级有界检查、字幕／助手历史检查、危险流停止及跳过后续工具。完整connection动态整链、统一上下文、证据特点／事件和表达一致性仍待P14／P15／P19／P21／P22。此前“人工复核”实际由Codex逐条阅读，无独立人工签字；正式评审保持待验。

P12历史保存点`b8ebb4853107f160dd443eadbc99fccc8d8412b0`的服务121、真实BGE／资源及身份23专项／JAR曾通过，Java全量保留唯一既有失败；报告及原SHA见[vectors.md](verification/mia-persona-memory/vectors.md)和[vectors-ci-results.json](verification/mia-persona-memory/vectors-ci-results.json)。当前实现和结果以以上P13新保存点为准，不能用旧SHA给新改动背书。

P12已实现SemanticEncoder／SemanticMemoryIndex、固定BGE base中文U8U8／768维、资产与内容版本、Scope先行SQLite余弦候选、失效／取消机制。4个跨措辞Top1命中、无关空召回、无FTS仍召回及生命周期样本通过；1万容量扫描p95 102.125ms、编码＋查询119.573ms、峰值RSS284.098MiB。容量向量复制真实种子，仅测成本；不等于完整语义语料验收。没有修改主回复链接入半成品检索，没有新事实库、Provider或服务。

恢复顺序：先核对分支／远程SHA／工作树及在途run，再读reply.md、reply-ci-results.json、D05和P16计划。P12—P15模块及已完成probe无需重做。继续P16统一且不重复的完成事件、持久任务、服务级有界Worker及恢复／关闭；P15实际聊天联动仍需先解决Provider容量与输出预留，不能据受控验证解除生产限制。ContextLimits必须来自审查过的服务端配置，不接受客户端字段。旧glm-4-flash别名容量和生产max_tokens本轮未核实，若None须维持限制，不用CI128替代或擅改费用配置。版本变化后须安全重建，不能盲目复用旧inputs_json或重复有副作用工具。完整真实manager＋BGE＋Provider、Token对照、实际提取、独立真实用户语料及八项行为继续后续验收，不因模块通过提前部署。

P13新增schema-v2保留原SQL和账本，元数据变化推进epoch、删来源清派生线索；v1→v2失败回滚及真实a30旧代码读写已验。严格P10—P12旧迁移器不识别v2账本，P24完整回滚制品仍待做，不得删schema绕过。实际提取及来源校验在P17／P18接入，当前fixture写入不代表提取器完成。

保存时本次38732848387／38732848548／38732848576／38732848453及历史run均已completed，无在途开发／部署操作。GitHub读取／推送／Actions已核实，生产SSH／iOS签名及模型Secrets未重新探测，不推定本环境已具备。报告／原文hash／无损gzip和复现workflow均在仓库，不依赖临时目录；专用Secrets留在GitHub，不复制到交接。此前审批服务用量限制已恢复正常审批，无绕过或凭据变更。

测试Secrets已配置且专用，连接与限定原Provider样本已通过，不复制密钥到新环境、不重复已完成probe。未实际App↔manager整链、生产TLS、iPhone、长期任务／情绪自然时间及全服务资源／八项行为；继续独立开发但这些条件不能被基础样本替代。先检查当前分支／SHA／工作树与在途run再接续。

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
| P07 | 进行中 | 身份基线与真实Provider单次连接通过（81e46ad／38659019412）；完整回归保留1既有失败，实际Mia Provider集成／容量与行为入口随后续模块完善 |
| P08 | 开发／隔离部分通过 | 18真实身份（含HTTPS/WSS）及构建、App100＋5和构建、智控台53＋64和构建通过；真实App↔manager与生产证书／入口／iPhone仍待验，整体未封板 |
| P09 | 基础通过，整体进行中 | 426d8c4的实际安装Scope／ToolManager／管理／旧会话及23身份／TLS通过；新增索引／事件／趋势／持久任务逐模块补Scope证据，整体与真实App／资源待验 |
| P10 | 完成：兼容基础 | 426d8c4／38656910711的6项真实SQLite迁移及104服务测试通过；同提交23身份／TLS、构建及类范围通过，完整回归保留1既有失败 |
| P11 | 基础通过，整体进行中 | 232de0d的113服务／23身份、实际安装检查及原Provider三个语义样本通过；整体人格随统一上下文／工具／事件及正式评审验收 |
| P12 | 基础及生命周期复核通过，整体待联动 | b8ebb48真实BGE及1千／1万资源通过；d5edbd6服务125通过，补超时／竞态／重开与重建；历史身份23专项／构建通过，完整Java保留1既有失败；完整语料／主链联动仍待后续 |
| P13 | 完成：检索模块及受控验证 | 664237f服务132、实际BGE及正向找回／底线拒绝通过；身份专项／构建通过，Java保留既有失败；D04固定供P14集成，完整真实行为待P22 |
| P14 | 完成：上下文模块及受控验证 | 5e91409服务145、实际BGE＋原Dialogue＋10工具场景、身份专项及构建通过；Java既有失败保留，真实Provider参数／接线及B08待P15／P22 |
| P15 | 完成：接线模块及受控验证 | 5c6e814的157服务、真实BGE／原SDK合成SSE七场景、23身份专项／实际TLS、类范围及JAR通过；Java既有失败保留，实际Provider容量／输出及完整B08待验，未部署 |
| P16 | 进行中 | 统一完成事件、复用mia_jobs的持久Worker与必要模型恢复接口已开发，待GitHub验证，不部署 |
| P17—P18 | 未开始 | 完整提取与维护未实施 |
| P19—P20 | 未开始 | 持续人格事件与授权趋势未实施 |
| P21—P26 | 未开始 | 必要管理、真实行为、性能、回归、真机及发布包待实施 |
| P27—P28 | 未开始 | 未发布，不能凭计划执行生产变更 |

当前补充：P10扩展schema及P13二版迁移、旧事实代码基础兼容已验证并归档。真向量与关联／四维模块通过不代表主回复链、Worker、事件、趋势或完整生命周期完成，整体真实行为按后续步骤验证。

## 八项能力状态

此表只记录本次 V1.2 目标，Mia 已有基础能力不因此判作不存在。

| 能力 | 代码 | 机制验证 | 真实行为 | 真机相关项 |
| --- | --- | --- | --- | --- |
| B01 人格对话引擎 | 进行中：P11基础通过 | 113服务及实际安装Scope通过 | 三个限定原Provider基础样本通过；完整多会话／事件／语义评审未验 | 未执行 |
| B02 长期记忆 RAG | P12真向量及P13混合模块通过，完整RAG未完成 | 664237f实际BGE／SQLite、132服务及身份专项通过，Java有1既有失败 | 未执行完整主链RAG | 未执行 |
| B03 异步记忆提取 | 未开始 | 未执行 | 未执行 | 未执行 |
| B04 四维检索 | P13模块通过 | S／L／A／E实际贡献、受控分项排名、真实BGE遗漏恢复和底线拒绝通过 | 独立合成中文留出通过；实际提取／Provider／真实用户语料待后续 | 未执行 |
| B05 持续人格事件 | 未开始 | 未执行 | 未执行 | 未执行 |
| B06 身份与记忆隔离 | 进行中：manager授权链 | 必要类范围／构建通过 | 23身份／实际TLS与Scope基础通过；完整未来消费者／实际App／八项行为未验收 | 未执行 |
| B07 长期情绪趋势 | 未开始 | 未执行 | 未执行 | 未执行 |
| B08 上下文管理 | P14模块通过，真实入口未接 | 145服务、10组工具、真实BGE上下文及真实manager边界通过 | 实际Provider／Token对照／主回复链与多次真实工具行为待P15／P22 | 未执行 |

## 待决与访问状态

D01—D10 已冻结开发契约及初选；D03见固定模型规格，D04经P13验证后按原参数冻结为[集成规格](verification/mia-persona-memory/retrieval-selection.json)，未按留出调参。用户已确认授权码、情绪保留及相关不可回答边界。生产完整RAG、私有安全链及长期趋势行为仍未验收，最终独立真实用户语料不合格时需保留新证据重评。

GitHub读取／推送、Actions和严格主机校验的只读SSH已验证；未改变凭据。仓库此前未配置测试秘密；用户现已配置三个专用Repository Secret，单次真实连接已通过，真机／签名条件仍须分别核实。新环境重新验证实际访问，不复制秘密进交接。

用户已配置真实聊天专用GitHub Actions Secret，三名称已核实，单次连接[38659019412](https://github.com/bboytang/Mia/actions/runs/38659019412)通过；[结果](verification/mia-persona-memory/live-provider-results.json)已保存，生产Key未读取／复用。新环境按仓库权限运行，不输出Secret值，不重复已完成probe。完整Mia Provider集成及容量／八项行为仍待后续验证。

2026-10-15只读核实当前聊天模型为智谱 `glm-4-flash`（ChatGLMLLM），API根地址 `https://open.bigmodel.cn/api/paas/v4/`；具体测试Secret映射已补入[Provider入口](verification/mia-persona-memory/live-provider.md)。此前火山地址仅为示例。未读取或复用生产Key，用户随后已配置专用Key并通过上述单次真实请求，完整行为仍未验。

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
