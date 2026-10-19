# P23 第一批定向修正 R1–R4

日期：2026-10-19。批准基线：`b7a4b0fc9f04d5b1232d41845ea1232a1e91c11d`；固定分支 `feature/mia-persona-memory-v1.2`。

## 范围与基线

用户在独立只读审计后批准本批，覆盖旧交接的“继续第三十六步”。审计报告已在对话交付，本文件保存本批依据与验证；不把尚未编码的建议当完成。远端和本地基线一致，无 tracked 改动，保留 `.private/`、`tools/`。ca03844六个既有CI均success，无重复派发。

审计已证实：R1混用case/SDK计时原点，总首句增量不变但阶段归因错；R2普通提取把数据库JSON字符串当模型数组示例；R3继承默认函数方法不能证明原生调用能力，固定openai实际请求未启用函数选择/strict schema；R4原生提案错误与字段校验错误的反馈路径不统一。模型模仿输入的因果、重复授权对实际延迟的占比仍属高度怀疑，不能写成已量化。

本批不执行36任务/正式72回复，不改模型/供应商/密钥、事实或任务schema、尝试次数计算、两次尝试/120秒期限；不部署、不进P24。只在最终代码SHA推送一次以取得必要同SHA回归，避免逐项提交重复CI；本地每项单独记录/提交。真实Provider诊断如无必要不调用。

## R1：计时与旧证据归因

已实现v3：所有 `*_ms` 时点统一相对case开始，保存case单调时钟起点及0ms，SDK起点、首次内容和TTS文本就绪分别记录。v2解析明确把SDK相对首内容转换到case原点，未知版本/逆序拒绝。

新增非零SDK偏移数学反例和实际SDK观察器假时钟测试，27项CI机制通过。对原第三十三步72回复/36配对另生成 `verification/mia-persona-memory/performance-auth-once-stage-corrected-v3.json`；原始gzip、旧归因和验收结论不覆盖。六组总p95逐项保持，10k查询0仍912.84ms/failure；最差配对935.49ms正确分配322.90/437.92/174.67ms。SDK区间包括远端/传输/消费/观察器，不称纯网络。源码diff由本项独立提交定位；GitHub最终SHA回归待批次代码完成。

## 后续顺序

R2统一最小只读模型输入投影 → R3显式Provider能力契约/实际参数验证 → R4错误分类、反馈及原失败输出重放 → 最终SHA必要回归/记录交接后停止。

R5前台持续活动导致后台饥饿、排队占用尝试/期限；R6重复授权/完整capture/配置读取；R7安全句边界与TTS首段边界。均保留为下一批待审批，不在本批顺手修改。

## R2：所有提取分支的只读输入投影

`project_context`对普通JSON/原生函数、自然纠错、成长和重要性分支统一只投影id/category/content及来源session_id/fingerprint/excerpt；删除无需模型消费的数据库序列化元数据/版本和额外字段，不把存储JSON字符串作为输出示例。服务器原始context与版本仍由tool_definition/validate_output/提交完整使用，模型输入与证据字典无共享可变对象；没有事实或任务schema变更。

新增四分支×两Provider路径反例，检查来源保留、字段最小化和模型局部修改不影响可信context。提案/提取/Worker定向75项在允许正常线程的本地环境通过（1.910秒）；受限沙箱线程首跑停滞已中断，不能把该次算通过。R1原总p95逐项复核误差小于1e-6ms，仅浮点舍入。R3/R4和最终同SHA回归仍待。

## R3：Provider能力契约

只将固定上游`87c6df77…`已复核OpenAI适配器原生绑定方法列为native_tools；类继承默认文本回退、未知覆盖和实例替换均不证明能力。未复核Provider使用现有response_no_stream单次JSON文本路径（仍需原校验），没有该路径则明确拒绝，不自动二次请求。当前glm-4-flash-250414/供应商/凭据不变。

能力矩阵：native tools在固定OpenAI实现与既有三SDK原文中已证实；函数选择/strict schema未由该适配器转发且无兼容证明，均不启用；普通JSON仅为文本回退，不声称供应商保证JSON模式。`verification/mia-persona-memory/performance-r3-provider-contract.json`记录固定源码hash与原39180767649三请求参数（tools存在、tool_choice/response_format/strict不存在）。无新真实请求。

能力选择/继承/未知覆盖/实例替换及两条提取路径14专项通过；连同提取/Worker77项定向回归通过。最终安装到固定上游后的原生路径仍由本批最后同SHA实际向量/SDK回归验证，不将测试替身当远端能力证明。R4待完成。

## R4：错误分类、反馈和冻结失败重放

已证实并修正：原生工具协议拒绝此前发生在Worker校验捕获之外，第二次尝试没有相应反馈。现在仅提取校验产生的parse、tool_contract、field_schema、source_semantic进入本任务第二次尝试；反馈包含服务器安全说明与有界、过滤秘密后的既有拒绝值，不包含原始Provider响应。Provider初始化/请求/清理失败为provider；原生排队超时为model_queue_timeout，队列满/取消分别为model_queue_full/cancelled，在途超时仍timeout，SQLite错误仍database。清理失败不覆盖已有主错误，未知异常仍model，不冒充供应商错误。

只细化既有`mia_jobs.error_category` TEXT字段中的值，未修改持久任务或事实schema、已有行、API结果结构。attempt=True的位置和含排队的计数语义不变，至多两次、120秒期限不变。排队阶段仅增加内存诊断标记，超时即设置原取消事件，原生槽仍到真正完成才释放。授权失效、删除/清空/编辑/重置取消和来源版本复核保持原样。

原56次拒绝逐份只读重放、前后hash及第三十五步离线判定完全一致；新报告`verification/mia-persona-memory/performance-r4-errors-offline.json`仅记录安全类别/hash：field_schema26、parse4、source_semantic2，另24份在空既有上下文下通过。这个24是ca03844已有的格式兼容结果，不是本批新增任务成功，不恢复历史10/26终态。第三十三步原72回复/36配对回归也验证六组总p95不变。

最终本地相关142项通过（4.896秒），覆盖普通JSON、原生函数、继承/能力选择、各错误类别、第二次有效反馈、无效来源、跨用户隔离、取消、删除一致性、队列/在途超时、人格/情绪及回复上下文；28项CI机制通过。Python3.10 AST、编译及diff检查另在提交前完成。真实Provider新增请求数为0；同SHA安装后的实际SDK/BGE回归待CI，不将离线模拟当远端稳定性证明。

反馈仍是内存中的任务局部诊断，重启不持久保留；排队仍消耗尝试。两者需要下一批单独设计与批准，不能在本批暗改schema或计数。

## 下一批建议与停止点

1. R5：已证实前台非零时Worker不启动后台、尝试在模型排队前递增。持续负载下期限饥饿属于高度怀疑，尚未量化。先提出有限前台优先/后台服务机会、有效尝试边界及恢复反馈持久化方案，说明120秒期限与旧任务兼容；批准后才实现，先做可控调度反例。
2. R6：已证实回复期间存在重复授权、配置读取和完整上下文capture；各项对p95的贡献证据不足。先用统一原点细分观测并核对授权失效/epoch/删除时序，只消除经证明等价的重复工作，禁止削弱实时隔离。
3. R7：已证实安全输出按完整句边界释放、TTS可按逗号分段；实际延迟贡献证据不足。先设计保持整段事实与授权检查的缓冲/分段方案并评估取消语义，不能直接提前放出未校验文本。

顺序为R5设计评审与可控调度 → R6/R7阶段证据 → 获批最小实现与聚焦回归 → 再申请固定模型、2CPU/2GiB/swap0、冻结完整公平性/首句验收。已有容量通过结论保留，正式首句912.84ms失败与正常成功p95缺失未解决；本批完成后停止，等待用户批准，不自动执行第三十六步或P24。

## 最终收证：第一批完成并停止

以下是最终状态，覆盖上文逐步记录中的“待CI”。批准基线到最终代码仅四个提交，一次代码推送，无手动dispatch或重跑。统一回归代码SHA：`b24ebf649d53a1435f27c204072fa1f3b7c6cdd2`。后续收证提交仅改文档/新增证据，不能把它冒充已经执行代码CI的SHA。

| 修正 | 根因与范围（已证实） | 精确提交 / 源码diff | 同SHA验证 |
| --- | --- | --- | --- |
| R1 | 高：case/SDK原点混用误导阶段归因；原首句总指标不变 | [dea0f7d73794c4c6e3cfcfc2bb62e8def9dedbb4](https://github.com/bboytang/Mia/commit/dea0f7d73794c4c6e3cfcfc2bb62e8def9dedbb4)，mia_reply_latency/mia_tts_timing及只读归因工具 | [28项观测机制](https://github.com/bboytang/Mia/actions/runs/39184651346) success；原72回复离线归因/总p95不变 |
| R2 | 高：普通分支数据库序列化元数据与模型数组形状冲突；所有分支统一最小来源投影 | [96faa87deb16ed90d4695018efda6aca85dec7e2](https://github.com/bboytang/Mia/commit/96faa87deb16ed90d4695018efda6aca85dec7e2)，extraction.project_context | [服务318项](https://github.com/bboytang/Mia/actions/runs/39184651325)、[安装/BGE/SDK](https://github.com/bboytang/Mia/actions/runs/39184651374) success |
| R3 | 中：默认继承文本回退被当原生工具能力；改成固定已复核适配器绑定方法契约 | [fa0c1e36147f2fd6821ff89b4f00fd8151e7c696](https://github.com/bboytang/Mia/commit/fa0c1e36147f2fd6821ff89b4f00fd8151e7c696)，proposal.provider_capabilities/extraction选择 | 同上318项与安装SDK回归；[提取语法](https://github.com/bboytang/Mia/actions/runs/39184651378) success；既有真实参数证据单独保留 |
| R4 | 高：原生协议失败不进入原反馈路径、不同错误共用类别；现在安全分类并给第二次有效反馈 | [b24ebf649d53a1435f27c204072fa1f3b7c6cdd2](https://github.com/bboytang/Mia/commit/b24ebf649d53a1435f27c204072fa1f3b7c6cdd2)，proposal/extraction/jobs/model_requests及情绪形状诊断 | 同上服务/安装SDK/28机制success；56原输出重放和哈希不变 |

其余必要回归：[身份授权173项](https://github.com/bboytang/Mia/actions/runs/39184651480)、[Java manager 150+4项](https://github.com/bboytang/Mia/actions/runs/39184651369)均success。上述六项均为同一代码SHA的push自动作业。共享性能和提取Provider工作流只有语法/机制步骤，真实模型及完整性能步骤均skipped。

日志、步骤终态、时间、原文/压缩哈希索引见[performance-r1-r4-ci-review.json](verification/mia-persona-memory/performance-r1-r4-ci-review.json)，同目录新增六份`performance-r1-r4-*-ci.log.gz`和五份`performance-r1-r4-vectors-*.json.gz`。五报告均passed且code_sha准确；真实BGE/SQLite/安装上游SDK在2CPU/2GiB、network=none的隔离容器执行。提取报告明确model_outputs=synthetic_controlled_fixture、chat_provider_calls=0：16次为MockTransport SDK往返，返回受控JSON文本；原生函数delta重组/错误反馈另由定向单元测试验证，不伪称本轮调用glm或证明完整真实提取稳定性。

## 兼容性、保留模块与证据边界

- 长期记忆：可信原始context、来源ID/原句/关联证据、Scope/版本/删除复核、敏感确认、错误事实拒绝、事实/向量原子提交和数据库重试复用均保留；无需重构或迁移。新模型输入的生产成功率改善仍证据不足。
- 人格/情绪：只细分三处形状诊断类别；核心人格、情绪授权、来源与关闭行为保持，现有相关回归通过；不把模拟七日趋势当用户七日验收。
- iOS/Mia硬件：未改Swift/C++、协议或固件。仓库iOS MiaMemoryTask不解码error_category；未发现对旧诊断值的枚举依赖。未执行本轮真机验证，不能据服务器CI宣称硬件或完整端到端体验已通过。
- 现有数据库/小智服务端：schema.sql与批准基线hash一致，未改迁移、索引、生产配置或manager实现。error_category沿用既有TEXT/API字段，旧行保留；外部未知消费者若枚举旧值仍需兼容核对。固定上游适配器升级后须复核能力白名单；当前不启用function选择/strict。
- 资源/调度：并发槽、队列上限、尝试位置和任务120秒保持；R5饥饿/排队尝试与重启反馈问题未解决。原已通过容量保持通过；本轮不新增容量/首句/完整公平性结论。

当前保留`.private/`、`tools/`，无未提交源码；原始失败证据无覆盖。P23整体未验收，P24未开始，未部署。至此停止，下一批仅建议，等待用户再次批准。
