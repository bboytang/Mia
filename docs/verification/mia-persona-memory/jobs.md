# P16：统一完成事件及持久任务

状态：dee34f5的机制及受控GitHub验证通过，不部署。P17结构提取／来源增强与P18完整维护未完成；实际聊天Provider、真机及完整B03仍未验收。

## 机制与边界

复用P10的`mia_jobs`，不改schema账本或新建事实库。`TurnCompleted`仅携带可信Scope、Session／Turn／稳定源标识、单条512字符内真实用户来源及开始时的memory revision；不收助手／工具文本，NFKC秘密过滤在持久化前执行。源标识／Scope幂等，重复钩子返回同任务。SQLite提交成功才发`mia_memory_job: accepted/pending`，此时没有“已保存”的承诺；`mia_memory action=job_status`只返回本人任务的ID／状态／尝试数／错误类别，不返回来源或模型配置。

`completed_chat`只在外层处理一次，覆盖普通回复、direct_answer及工具最终返回／RECORD／递归续答。拒绝、容量限制、流式错误及中断不提交。原句末checkpoint对可信Mia变为纯历史裁剪；Mia断开时不再另起旧提取守护线程。非Mia原路径及旧provider兼容方法保留，但部署后的Mia只有完成事件通向持久Worker。适配器兼容方法的历史单测不冒充新Worker验收。

服务级单Worker在原app启动／关闭处拥有生命周期，队列128、全局后台并发1、Scope轮转及Scope内显式记忆优先；前台活动时不启动新的提取，已在途调用不强制抢占。SQLite待处理容量也为128，满载拒绝且明确未接收，不声称持久接收后再丢弃。基于D07的120秒完成目标，本步给任务固定120秒硬期限，单次提取30秒、总尝试2次、数据库重试1秒；过期成为可追溯failed，不将超时写成empty。该期限是开发实现选择，不是实际p95达标证据；全服务负载／资源仍待P23。

后台执行和提交前重新restore／require Scope，检查暂停与revision。为重启后无需设备重新提供凭据，必要身份接口`/config/mia-auth/worker-model`以既有服务认证及严格白名单快照核验并锁定绑定，只返回该智能体当前已选LLM配置；普通用户token、伪造owner、撤权／旧版本拒绝。不把Key或私有凭据存入任务，不改现有模型参数。新Provider实例仅用于后台提取，使用现有同一选型和实现，不增加回复入口。实际manager验证用上游占位配置，只检查恢复及隔离，不调用聊天API。

校验结果先持久化；数据库重试复用已校验结果、不重新提取。事实／checkpoint及终态在同一SQLite事务提交；有效空结果为empty，非法输出为invalid_output并有界重试。内存保留未能持久化的已校验结果用于同进程数据库重试；若进程在结果尚未持久化时崩溃，只能按持久尝试数重提，不能虚构exactly-once模型调用。恢复不重置尝试数，validated可直接提交。

删除／清空／暂停／编辑／重置在原事务取消未完成任务并清除其来源与提取结果；终态也清除来源，单事实正文仍在memories。保留任务标识／状态作为结果凭据，完整保留期限与清理继续P18／P21。原生模型调用使用独立单daemon lane：超时或关闭不会在原调用仍未返回时启动第二调用；迟到结果不能写DB。关闭总等待20秒，未完成任务保留以供恢复，不等待卡死原生线程。此处没有以新线程扩大并发。

## 验证入口

- `server/tests/test_companion_jobs.py`：持久接收／去重、满载、重开恢复／尝试数、validated恢复、数据库重试与回滚原子性、有效空与非法输出、Scope及前台公平、执行中删除／撤权、挂起原生调用与总关闭期限。
- `scripts/ci/verify_mia_reply.py`：原安装Connection／Dialogue／SDK／BGE，六条完成路径各恰好一个持久任务；合成空提取明确pending→empty；P15限制／删除／撤权继续回归。合成响应／策略／提取，非聊天或声学验收。
- `scripts/ci/verify_mia_scope_integration.py`：实际manager HTTPS／WSS，恢复当前LLM、服务token与普通用户token隔离、伪造Scope拒绝、恢复任务及删除／撤权取消。提取仍为fixture。

自动化仅GitHub运行；精确提交与结果见下方，不以受控机制验证替代真实行为。

## 最终验证与保存点

被测提交`dee34f5435bcfbe06b44be54b32c2b5321533319`，四workflow均completed／success：

- [服务38759159810](https://github.com/bboytang/Mia/actions/runs/38759159810)：176项全通过，其中19项P16方法，含SQLite重开／validated恢复、DB重试与原子回滚、默认128配置／缩小容量夹具满载、非法与空结果、Scope／前台公平、超时及总关闭、状态隔离、真实runtime start／resolve／stop和本轮优先级复位。[方法列表](jobs-service-results.json)。
- [实际BGE38759159851](https://github.com/bboytang/Mia/actions/runs/38759159851)：P12—P14回归和P15／P16九个协议场景通过。普通文字、多步并行工具、direct_answer、ASR识别文本、RECORD及工具直接回复六条各恰好一个pending任务，经合成空提取到empty；合成SDK请求11次、工具派发7次，删除不重放、未知容量和撤权回归通过。见[原报告](jobs-reply-results.json)。P14回归50次build p95 36.341ms、峰值RSS283.676MiB，不是聊天TTFT或任务负载p95。
- [身份38759159526](https://github.com/bboytang/Mia/actions/runs/38759159526)：全量173／173、23专项、实际HTTPS／WSS／Java→Python Worker模型恢复／普通用户token拒绝／伪造owner／删除与撤权、类范围及JAR通过。[身份原JSON](jobs-identity-results.json)保留。[manager38759159388](https://github.com/bboytang/Mia/actions/runs/38759159388)原150／150和独立基线4／4、字节对照通过。脱敏九项持续通过，未增加跳过项。

[分项证据及原文hash](jobs-ci-results.json)附P12—P14原报告的无损gzip。首轮46e9a2d的RECORD夹具失败及[原报告](jobs-first-reply-failure.json)／[范围](jobs-first-ci-results.json)保持原样；a48201d修正该不成立的TTS预期后四workflow通过，后续复核发现旧checkpoint移除后显式记忆优先级需在每轮开始复位，以dee34f5及新增回归为最终保存点。没有改变运行工具语义来迎合夹具。

没有真实聊天请求、本地自动测试／构建或部署；所有run结束，无在途操作。当前仍是P16机制与受控接线完成，非完整B03／八项行为验收。下一步P17：在同Worker上完善结构化提取、来源／价值／敏感状态及关联元数据校验与增量索引，验证数据库重试不重调模型。生产Provider容量／输出预留仍未解决，P18完整维护、P22真实模型／独立语料及P23全服务负载继续按计划。
