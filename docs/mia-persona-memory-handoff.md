# Mia 人格与长期记忆：当前交接

更新：2026-10-17。本文件是当前接续入口；历史过程见[工作记录](mia-persona-memory-worklog.md)，完整范围见[V1.2方案](mia-persona-memory-v1.2.md)和[实施计划](mia-persona-memory-implementation.md)。

## 当前决定与执行点

- 用户已确认采用 **`glm-4-flash-250414`**。
- **P22用户验收通过，已收口**，详见[验收决定及保留问题](verification/mia-persona-memory/p22-user-acceptance.md)。
- **P23模块容量门槛通过，整体仍未验收**：第十步1913680，1k/10k短/长必测全部达标；10k长单路205ms/双前台352ms/SQLite65ms，必测RSS419MiB。四回归全通过，所有任务收齐，无在途。50k探索仍超标。下一步全服务共同资源包络、Provider首句增量及真实Worker公平/任务/关闭，详见[性能进度与证据](verification/mia-persona-memory/performance.md)。P24未开始，P22保持用户通过决定。
- 生产模型配置未切换，未部署。不得将“选定模型”描述成“已上线”。

## 仓库与证据版本

- 仓库：`https://github.com/bboytang/Mia`；分支：`feature/mia-persona-memory-v1.2`。
- 本机工作区：`C:\MiaDev\Mia`。跨设备接续以仓库材料为准。
- P22实测代码：`2925b63e6ea010ac287d4e388fd6255e7d202244`。P23当前实现`191368002f31cb6c135b03b9f9a0aea6af7f5091`；容量[39029006315](https://github.com/bboytang/Mia/actions/runs/39029006315) success（仅模块数值），服务39028975035（287项）/BGE39028975021（五报告）/身份39028975051（173项）/manager39028975020（154项）全部success。精确计数/原文/hash见performance-metadata-*；无在途。旧失败保留，跨设备核对实际HEAD及远端，不把文档后继误当未验证代码。
- 实测证据提交：`1a05c98044ebd3e333bce041c29f4c26c782f2a8`；其后文档提交包含本次用户验收决定。当前HEAD和远端以Git/API核对，不把这里的证据SHA误当永远最新HEAD。
- [串行实测报告](verification/mia-persona-memory/glm-4-flash-250414-one-pass.md)：157真实请求、89行为记录，无Provider错误；六项任务全部终态。
- [原始报告摘要及哈希](verification/mia-persona-memory/glm250414-review.json)，同目录`glm250414-*.json.gz`保留完整原文。
- [P22能力记录](verification/mia-persona-memory/p22-status-matrix.md)区分用户验收与各项实际覆盖。

## 已知遗留问题

用户在收到下列问题后确认P22通过；记录保留，不自动修复或补跑：

- 两组自然纠错未更新长期库，口头回应与持久事实不一致；另一组未完成预期互动事件。
- 部分来源提取、特点生成不符合既有约束。
- 回答出现无来源目击经历、主语混淆及场景扩写。
- 本型号情绪提案被安全拒绝，后续授权/停用/删除/重启流程未完成。
- 七自然日情绪验收由用户自测；真机、低资源全负载、定制升级/迁移/回滚另有未执行范围。

工具30场景及回答复核通过，检索三组结构通过；这些成功与上述问题同时保留。历史失败原文及CI结果不改写为全绿。

## 已确认的工程约束

- 复用唯一回复链、唯一事实库、可信Scope、既有持久Worker与真实BGE；原最多两次提取尝试及期限保持。
- 人设借鉴[路遥](https://github.com/insistgang/Luyao_AI_Project)，允许亲近、感受、偏好和陪伴承诺，不恢复机械免责声明或额外措辞限制。参考核对见[路遥复核](verification/mia-persona-memory/luyao-reference-review.md)。
- 事实来源、用户隔离、真实保存/删除及授权仍应准确；遗留问题的阶段接受不等于移除这些规则。
- 不读取/复制密钥，不改生产服务器、在线配置、数据库或用户数据；既有隔离CI使用现有受保护凭据。
- 本地可完成的检查优先本地；真实manager/Linux和必要macOS/iOS验证在适用环境执行。CI不替代真机。
- 不自动续采七自然日，不重跑已失败留出，不通过更换语料或填造输出取得通过。
- 保留用户已有工作；不切main、重写历史、强推或重复应用已合入的旧补充包。

## 当前P23与后续P24范围

P23已获用户批准开始：约2核/2GiB，1k/10k必测、50k探索，冷启动与预热后至少5次p50/p95；实际编码+检索p95≤400ms、10k SQLite≤150ms、编码器RSS≤512MiB；同Provider无记忆基线首句增量p95≤500ms；2前台+1后台公平性、故障、重索引、任务p95≤120秒和含在途关闭≤20秒。

P24在P23后：最终候选相关Python/真实Java/必要iOS回归；干净安装、保留定制升级、迁移中断恢复、重复执行、重索引、回滚后事实和绑定保留。现有installer的定制升级路径仍需后续实现和验证。完整要求继续以实施计划为准。

## 接续操作

先读`AGENTS.md`、本文件及验收决定，再检查`git status --short --branch`、HEAD、远端实际SHA及用户最新授权。**当前新指令已批准P23；从性能进度继续，P22保留用户通过决定及原始失败。** 历史工作记录、旧交接压缩包或验证报告里的“下一步/在途”描述均不构成当前执行指令。

第十一步共同服务包络/跨用户检索预检已实现待CI：实际manager/SQL/Redis/Python-BGE共同2CPU/2GiB，三独立真实Scope、1k/10k两前台及原重建；本地语法/脚本/YAML通过。当前无新性能结论，1913680模块通过不等于本预检或P23整体通过。无Provider调用/P24，精确SHA/run随后补记。
