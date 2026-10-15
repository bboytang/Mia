# P19／P20 逐项验收（2026-10-15）

依据实施计划P19／P20与D06／D07；当前实际日期仍为UTC 2026-10-15。2026-10-15 用户明确要求：“跳过这个验收门槛，后续由我自己测试”。真实跨七自然日的采集、足量后实际对话及变更验收转交用户，不再作为P19／P20开发收尾的阻塞项，也不继续自动采集或提前audit。运行时五观察／三会话／跨七自然日的趋势资格保持；此决定不表示真实长期验收已通过，不删除历史失败或原始证据。实现、受控验证、真实模型样本、真实跨日证据分别列出。最新运行源码6b57337的227服务／BGE／身份／manager受控复验全部通过；人格提示e48f222实际四项通过，完整对话因泛夸在reflection被新增检查拒绝，后九阶段未执行，不能把旧13项结果移作本轮通过。旧报告不替新代码背书。

| 要求 | 当前直接证据 | 判断 |
| --- | --- | --- |
| P19 真实资格，关键词不等于事件 | continuity单测 pending／keyword／unknown／failed-turn；实际dialogue-current的seed及完成输出 | 旧提交已验证；新提示continuity／repeat实际通过，reflection风格未通过 |
| P19 回复前有限使用，完成才active | ContextBuilder捕获pending；实际continuity／reflection／boundary记录before与activated；真实完成钩子单测 | 机制及实际固定样本有证据 |
| P19 跨会话、重启、重复幂等 | 每phase新进程及同state.sqlite3；repeat不新增，BGE重开库／新session；补来源佐证仍同事件单测 | 机制及实际固定样本有证据 |
| P19 删除／纠正／撤权失效 | edit_delete_and_revoke、deleting_evidence、added_corroboration单测；实际deleted无已删召回，BGE删除来源检查 | 有证据；完整独立真实行为仍P22 |
| P19 无固定剧情或编造经历 | 实际反思／重复／边界原文；证据状态持久，核心不允许虚构经历 | 固定样本无经历编造；自然语气仍部分未通过 |
| P20 默认关闭，不采集／聚合 | 默认关闭单测与实际default-off提取空；未知来源旧记录不补造 | 机制及固定实际样本有证据 |
| P20 启用后的来源、时间、对象、置信度、类型及授权版本 | observation_uses_server_time、consent竞态单测；实际enabled-mood原输出与提交 | 有证据；未经启用不追认 |
| P20 30日窗口、90日清理；自述与推断分组 | window_and_retention、inference_not_pooled、single_reversal；BGE报告明确SIMULATED_UTC | 受控验证；不能据此说真实七日完成 |
| P20 五观察／三会话／跨七自然日 | 首日38785441525仅1观察／1会话／1自然日 | 运行时门槛保留；实际跨日验收已由用户接管，不阻塞开发收尾 |
| P20 相关趋势进入上下文 | related_context单测／BGE；实际insufficient原文不声称已有趋势 | 不足路径实际通过；足量真实路径待跨日 |
| P20 纠正、删除、清空、停用和重算 | correction_delete_recompute、disable、cross-owner、跨连接快照及保留期单测；BGE停用／manager授权与范围 | 受控验证；真实跨日库上的改变与实际回复待足量记录 |
| P20 单轮、他人、引用、表情、情绪重要性不冒充趋势 | quote／negation单测；实际quoted-mood空；默认关闭／enabled不足 | 固定样本通过，完整P22独立语料另验 |
| 用户：自然回答，善意陪伴无需免责声明 | persona-current安慰“我在，会陪着你的”；dialogue-current中仍有泛夸／回避选择／固定结尾 | 安慰要求通过；本轮固定样本仍泛夸，整体自然语气未通过 |

所有自动化在GitHub执行。原报告、hash和不同提交的run见continuity-ci-results.json。无本地自动测试／构建或部署；没有用CI小预算替代生产Provider容量证据。P19／P20实现及受控验证按原步骤范围收尾；用户已接管真实跨日验收，不能把该项记为已通过。整体自然语气及P22完整真实行为仍保留限制，不由步骤收尾代替。

本次契约审计修正：停用后原管理接口仍聚合，6b57337移除该例外。新服务用例覆盖足量后停用、原观察仍可看、无聚合、重启用可恢复；实际BGE同步补管理检查。此SHA四项workflow已全部成功，精确run见continuity-ci-results.json。

2026-10-15新增50a8bac的audit入口：真实来源制品经GH来源／hash复核，只读备份后进行足量门槛检查。实际提前验收run38791285449按预期failure：audit_gate=insufficient_real_calendar_evidence、requests=0、原始state.sqlite3 hash保持与首日报告一致；不能将workflow失败改称完整验收成功。足量后四次回复／纠正／删除／停用的正向路径尚未执行，仍待真实七日。语法workflow38791286696成功。
