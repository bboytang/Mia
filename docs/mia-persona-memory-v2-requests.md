# P23 第三批：V2 请求记账与后台服务机会

用户授权基线858551c2efaa24e76ea421bf3cb946e9c3d5119c；本地/远端一致，tracked干净，保留.private/、tools/及所有历史失败。已有CI均终结，未重复派发。

## 检查点1：状态与幂等迁移

已证实：新增schema-v4.sql，策略行明确标记version=2；缺行只代表V1，不以attempt值猜测。原事实表、原任务CHECK、前三版SQL/checksum不变。V2当前阶段、排队/取得槽/复核时点和独立请求账本均与任务关联；ordinal至多2、每次HTTP发送入口至多1。终态触发器在事实提交/取消原事务内清空反馈并记录terminal。当前提交仅显式policy_version=2才创建V2行，下一检查点接入执行后切换新任务默认值。

回滚：旧V3迁移器会因版本数/校验和拒绝V4，不能直接运行旧Worker。check_worker_rollback要求无活动V2且原生调用已结束/进程丢失已核实；它不证明操作系统进程已经停止。支持的代码回退必须保留V2迁移/读取能力、改为V1接纳并安全收敛V2；不自动DROP账本、不回退事实、不退款。离线进程退出确认后，恢复可将未完成请求记为process_lost，仍保留原尝试。不支持直接以旧二进制打开升级后的库。

定向验证：新旧接纳/幂等重复、终态反馈清理、回滚活动/未知原生拒绝、V3→V4事务故障回滚/重复升级及旧迁移拒绝。首跑测试发现导入的夹具TestCase被unittest额外收集（63项含29重复）；修正收集后另行记录，不把重复计为覆盖增长。安装器同步包含v4文件。精确提交以检查点提交为准，最终同SHA CI待全部代码冻结。

下一步：事务启动意图、实际SDK/HTTP入口及崩溃恢复；前台体验参数尚未落地。原容量通过、正式首句912.84ms失败、36任务10/26结论不变。

## 检查点2：事务请求预算与混合恢复

检查点1 SHA：36da356。新任务默认V2；原V1测试明确使用policy_version=1保留原断言。取得槽后由原生线程回到服务事件循环restore/require Scope，事务内复核deadline、取消、原始可信context及其来源/同意版本，再原子写intent和attempt；SDK和HTTP入口均再次复核。任何记账失败不进入SDK。每任务最多两行请求，排队不计次。真实OpenAI SDK2.8.1关闭自动重试，httpx关闭重定向并检查底层transport重试为0；发送hook阻止同次意图第二次HTTP入口。未知Provider预算契约拒绝，不伪装支持。

原生调用真正返回/关闭client才释放槽；超时只设置取消、不假释放。进程内活跃原生登记拒绝第二Worker恢复；进程丢失后未完成账本记process_lost，attempt不退款。校验反馈仅保存原有脱敏有界说明，不保存原始非法响应；重启能恢复第二次反馈。已校验提案/数据库重试不增加请求。

47项定向通过；此前278项companion回归通过（新增混合测试后最终数另记）。证据performance-v2-accounting-local.json区分真实SDK+MockTransport、mock HTTP和子进程退出，remote=0。两种子进程os._exit故障：intent后发送前1attempt/0HTTP；HTTP入口后响应前1attempt/1HTTP；恢复不退款，第二次后终态。两个503只产生2SDK/2HTTP，重定向不跟随。排队虚拟30秒0attempt。来源版本变化、删除/取消/过期/撤权/重绑均无新HTTP。

原失败日志全部另存performance-v2-*.log.gz：首版权限注入发生在最后授权复核之后、事务之前，0attempt断言错误地否认了该保守窗口；现在分别在授权前和intent后注入，前者0attempt、后者1attempt，二者均0SDK/HTTP；没有放宽SDK发送断言。另有SDK冷初始化使固定50ms超时早于预期HTTP入口，改用入口Event后确定性注入超时，保持在途槽不得释放的原断言。V3数量断言随新增迁移改为精确4，原V1服务夹具显式接纳V1。失败不冒充通过或丢弃。

调度机制单独下一提交；具体前台体验参数仍需对照。R6/R7运行优化未启用。

## 检查点3：已确认的后台机会

请求记账检查点SHA aa947e5。用户明确选择“4次前台让行＋等待10秒”。全局运行门闩采用该默认值；构造参数允许有界候选对照，无生产配置改动。两个条件同时满足后，后台队首可在下一空槽入场；已有前台不被抢占，每次至多一路后台，全局仍2、等待仍128。没有前台排队时允许直接后台入场；另一路不再被第二个后台占用。V2 Worker在foreground>0也可排队，旧V1仍被原入口规则阻断，不能只改变门闩宣称解决活性。

在有限请求完成且队列可服务的假设下，已老化的后台在至多4次前台授槽后获得下一机会；这不是固定墙钟上界。10秒前可让行更多前台；在途请求不返回时无槽可用，无法保证120秒完成，也不暂停该期限。头部取消/超时会删除ticket，不释放别人的槽。两个候选4/10、8/20均用真实线程/虚拟年龄验证，另有双前台Worker入口、V1/V2混合和第二后台不得占另一槽反例。

历史请求证据：performance-worker-fairness-complete-child.json.gz（SHA256 757a9f52afc6972499bb8bb598a3df74310473cfa64fd4265ad674ef4fdac6d5）66次原生调用p50 8816.77ms/p95 14324.85ms/max19400.63ms。不是新V2请求时长上界或正式前台延迟。参数选择前已告知用户后台占槽时前台仅余一路，可能影响10秒前台排队。

284项相关回归、30项聚焦检查通过。源码审查发现with_options克隆会丢失安装到SDK资源上的观察包装：旧本地账本HTTP正确，但额外SDK spy为0，不能当实际SDK次数证据。保留旧报告，改为仅将每次提取独占的原client.max_retries设0，保留原入口，新增1SDK/1HTTP、2SDK/2HTTP精确断言；更新证据performance-v2-scheduling-accounting.json取代其SDK spy解释，旧文件不覆盖。默认SDK HTTP类和显式transport retries=1拒绝反例另通过。

下一步只在隔离共享资源下固定两臂strict-control/four-ten（每臂16前台SDK＋1真实Worker，全部MockTransport，34 SDK/HTTP固定上限、远端0），测量前台排队影响；历史8.8168秒中位数只用作可控后台保持时长，不冒充GLM网络。同时测真实10k冷特征/5暖读，再执行原4Mock完整chat/Guard/TTS对照。无完整36任务或72回复。

## 检查点4：候选冻结与验证计划

调度SHA 0616e92。最终本地285项companion、39项CI机制通过；Python3.10 AST和diff检查通过。新CI驱动本地干跑完成：固定上游87c6df7真实Provider/SDK/MockTransport，34SDK=34HTTP/远端0，两任务均empty/attempt1。该干跑检索是夹具，不是实际BGE或2CPU资源证据；其虚拟任务clock不用于墙钟队列解释。受限服务组真实结果待唯一GitHub诊断。

R6新诊断：实际10k首先冷特征读，然后固定5暖读；记录缓存条数/字节、逐行特征构建聚合时长、扫描线程CPU与墙钟、真实BGE、manager/锁/SQLite等嵌套trace和完整结果hash。每行只累计计数/耗时，不写盘或创建span；整体观察窗口可能含空闲Worker维护，重叠span不相加当墙钟。读取结果必须完全一致；冷10000次特征构建、暖0次，否则诊断拒绝。此时encoder已初始化，不能称模型加载冷启动。没有启用权限/版本快路径或修改R7完整句校验。

冻结后一次push触发必要的服务/身份/manager/真实BGE/提取/观测CI，另仅dispatch一次远端cap0共享诊断。必要源码差异/失败修复会记录新SHA并只重验受影响内容，不重复同源码采样取绿。当前不具备宣布P23整体验收的条件：原首句912.84ms失败与完整36任务10/26仍原样保留。

## 冻结后独立复查：SDK开始必须来自SDK内部

旧候选a229268be63d4dd4bb59cbdf79ec306dc6cc8ca9六项自动CI均success（351服务、身份、manager、实际BGE五报告、提取语法、39观测），但复查发现sdk_started_at仍写在实际SDK调用前，存在把即将调用误说成已经开始的窗口。新增确定性SDK入口反例先在旧实现失败，原log为performance-v2-sdk-observation-before.log.gz；不能用已有绿色结果否认此缺陷。

已修正：intent保留原先事务；发送前另做原权限/来源/取消/deadline复核，然后进入实际SDK。sdk_started_at从固定SDK2.8.1内部_build_request观察点记录，正值证明SDK已经进入请求构建；HTTP hook再复核并记录发送入口。若SDK在该观察点之前失败/崩溃，sdk_started_at为NULL代表未观测/未知，不等同实际SDK次数0，更不能猜远端收到。http_sends也是httpx发送边界的保守记录，不能冒充socket完整写出/远端收据；真实SDK spy与MockTransport分别独立计数。没有修改attempt预算/DDL/默认调度参数。

该补充286项相关回归通过。其首轮触发既有检索反例自身的并行SQLite写事务竞争：编码hook未拿store.lock，两原生编码线程会对同连接commit交叉。只为该故障注入写入补上既有存储锁，来源变化必须拒绝/删除来源清除线索的原断言原样保留；原失败performance-v2-sdk-observation-after.log.gz不覆盖。新文件/门闩/迁移也补齐身份、向量和提取workflow路径，保证今后单改账本仍有相关CI。

共享诊断39191989529仍收原句柄，不重复派发在途测试。由于请求开始观察点确有源码修正，需要新SHA的必要同SHA回归，不能把旧a229268的绿色归到新代码。

## 原候选共享收证（保留，不替代最终SHA）

a229268 / 39191989529 success：真实2CPU/2GiB/swap0、无OOM；34真实SDK/34 MockTransport入口、另4完整chat Mock SDK、远端0；两臂各一真实Worker任务empty/attempt1。strict-control等前台结束后开始，four-ten在foreground=2时获得空闲槽。该次后台入槽时gate.waiting_foreground=0，属于明确的空闲服务机会；**没有在共享资源中实测触发10秒/4次的饱和老化配额**，不能冒充该证明；配额来自确定性持续排队反例。受控前台最大槽等待0.024→1902.96ms，两固定臂各16样本，不是实际GLM前台p95或正式首句差。

10k冷特征1842.58ms，扫描线程CPU1709.47/墙钟1712.28ms；10000次特征构建聚合1490.11ms、缓存0→10000。五暖读319.53/383.11/286.21/306.12/280.73ms，构建0次，扫描CPU169.64–259.36ms，六完整响应hash相同。冷BGE两调用inclusive105.82ms（并行不能相加当墙钟）、manager2次48.02ms、Python SQLite锁0.069ms；不是SQLite锁竞争主导冷慢，首次静态特征构建/CPU为主要来源。暖begin版本扫描/快照分别有约12.9/8.2ms，尚不能在不完整写入失效证明时跳过。以上为该SHA单轮诊断，不改原正式暖态首句912.84ms失败。

Python整体峰值448.96MiB，共同父组峰值1555.73MiB，无OOM；实际编码器/性能容量旧通过保留。新SDK内部观察点19b503dd08926ae83e5a40d997517eed1d429046已推送，五自动回归和新SHA唯一cap0共享39192505563在途；原共享已终结后才派发，无同源码重复取绿。原始JSON/CI日志与全部artifact hash见performance-v2-shared-first-*，原marker解释以补充修正为准。

## 状态与验证口径

| 阶段 | 持久证据 | 语义 |
| --- | --- | --- |
| 接纳 | mia_jobs.created_at + mia_job_policy.version=2/phase | 与真实用户source同一事务接纳；缺策略行是V1 |
| 排队/取槽 | policy.waiting_at/slot_acquired_at，首次请求复制到ledger | 0 SDK intent时attempt不递增；取槽仍不等于获得调用权限 |
| 复核 | ledger.rechecked_at | 可信Scope恢复、当前授权/绑定、原始context/来源/同意版本、取消及deadline |
| 启动意图 | ledger.intent_at/ordinal + jobs.attempts同事务 | 至多2；提交成功后才允许进入SDK，崩溃不退款 |
| SDK进入 | sdk_started_at | SDK内部请求构建观察；NULL是未观测，不是假定0 |
| HTTP入口 | http_started_at/http_sends≤1 | 关闭SDK重试/transport重试/redirect，不能解释为远端收据 |
| 响应/原生结束 | response_completed_at/native_finished_at/outcome | 完整流EOF与调用真实结束分列；取消不假释放槽 |
| 校验/提交 | outcome + policy.phase、jobs.validated_result、原事务terminal | 校验仍基于原始可信context；已校验结果重试不重复模型 |
| 恢复/回滚 | process_lost、不变attempt、check_worker_rollback | 单服务进程恢复须确认旧进程退出；进程内活跃原生拒绝恢复；旧V3 Worker拒绝V4 |

同机同库只有原有单应用Worker受支持；进程内registry不冒充跨进程分布式锁。恢复/回滚必须先停止旧应用，不能同时启动两个独立应用解释同一活动任务。回滚检查也不自动证明OS进程消失。保留V2-aware迁移/读取能力、以JobStore(policy_version=1)关闭新V2接纳并收敛活动任务，是支持的兼容回退；旧二进制直接读V4/自动DROP ledger不支持。真实生产升级/回滚操作未执行。

| 用户要求的定向反例 | 已证实验证 |
| --- | --- |
| 排队30秒 | V2虚拟30.001s，0attempt/0实际SDK spy/0 Mock HTTP |
| 取槽记账事务失败 | SQLite authorizer拒绝INSERT，事务回滚，0attempt/0 SDK/0 HTTP |
| intent后发送前崩溃 | 实际子进程os._exit；保守1attempt、无SDK/HTTP观察，恢复不退款 |
| HTTP入口后响应前崩溃 | 实际SDK+MockTransport子进程退出，1attempt/1HTTP观察，process_lost后最多第二次 |
| 两次/底层预算 | 两503=2真实SDK/2 Mock HTTP，终态provider失败；redirect不跟随，transport retry非0拒绝 |
| 先后到达/持续有界前台 | 真实线程FIFO、4/10与8/20虚拟年龄、滚动队列及容量128反例；非抢占 |
| 双前台/后台 | V2 Worker foreground=2能够入队，旧V1不偷换语义；受限资源两实际模型lane对照 |
| 超时/取消/删除/撤权/重绑 | 原V1机制保留，V2前置/intent后及来源版本变化反例均无越权HTTP；不假释放在途槽 |
| Worker恢复 | 队列不退款，活跃native拒绝假恢复，持久反馈可恢复；validated DB重试复用结果 |
| 混合版本 | 旧V1和新V2同Worker执行，分别计数，旧行无SDK账本且不被回填 |
| 升级/重复/回滚 | V3→V4真实SQLite故障事务回滚/重复幂等、旧事实源兼容；活动V2/未知native拒绝回滚 |
| 2CPU/2GiB/swap0 | 真实共享父组运行manager/MySQL/Redis/Python/BGE与控制模型并发；不冒充真实Provider排队或正式36/72 |

## 兼容与剩余阻塞（最终收证前判断）

已证实：原SQLite唯一事实表、BGE/Scope/来源真实性/删除/隐私校验保持；没有改变提案_schema=1、事实字段、R1计时原点或R2最小模型投影。R3固定Provider原生tools/未知strict不启用仍然有效，R4错误类别/脱敏反馈延续且V2增加重启保存。新任务attempt=0的确定性有效空结果是V2定义，不伪称SDK已执行。iOS job_status已有state和字段保持，内部新阶段不发送成新枚举；源码兼容已检查，iOS/硬件/实际音频未做新增真机验证。

已证实：当前没有R6/R7运行优化。冷CPU特征构建已有量化，不能拿它替代原暖态首句912.84ms失败根因；暖态每delta串行manager复核存在，但删减/快照未证明所有写入与授权失效等价。R7逗号早释放仍不等价，Guard/TTS/iOS/固件代码未改。编码/检索旧容量通过继续有效，不因本次独立冷读/控制lane重新判失败。

证据不足：新V2在真实GLM上的完整36任务有效率、公平正常成功p95、两前台完整chat竞争与新代码真实在途全组关闭；本批不执行这些正式验收。历史fe48aaa在途关闭通过保留，但不冒充本批新V2全链路在途证据。后台机会只保证有限服务事件假设下的机会，不保证无限饱和仍120秒成功。新Schema回滚必须用V2-aware版本，SDK内部观察依赖固定2.8.1，升级需重验。

明确判断：**目前不建议启动第三十六步正式验收。** V2记账/机会机制可以完成本批验收，但正式暖态首句超限尚未解决，真实GLM新结构化有效率仍缺充分证据；先评审暖态安全等价改进与固定上限真实模型验证计划，再由用户决定完整36任务。两次/120秒、600ms/500ms、250ms/150ms、500ms/400ms和安全约束均不降低。不会自动部署、变更生产数据库/配置、进入P24或下一轮测试。

## 19b503d收证（后续混合版本反例补充）

本节覆盖前文全部“待CI/在途/下一步”过程文字。最终已验证代码：**19b503dd08926ae83e5a40d997517eed1d429046**。之后的收证提交只增加文档/证据，不能冒充已跑CI的代码SHA。没有在途测试；没有部署/生产配置或数据变更/P24，没有完整36任务/72回复。新增真实远端Provider请求总数**0**。两个不同源码候选分别跑固定零远端诊断，全部保留，未重采同源码选较好结果。

### 精确提交及源码diff

| 检查点 | 提交/差异 | 行为与根因 |
| --- | --- | --- |
| V2状态/迁移 | [36da356cac1ab66755656926f4cde261d49d46f3](https://github.com/bboytang/Mia/commit/36da356cac1ab66755656926f4cde261d49d46f3) | 独立策略/请求表，旧V1不回填；新迁移幂等、回滚拒绝条件 |
| SDK事务预算 | [aa947e5bc5ee88c809a86296b59ab874c52fda82](https://github.com/bboytang/Mia/commit/aa947e5bc5ee88c809a86296b59ab874c52fda82) | 旧排队扣attempt改为仅新V2事务intent；两次/120秒不变，反馈/结果恢复 |
| 后台机会 | [0616e92330a8a6033df00e701cb2a587a60e7be8](https://github.com/bboytang/Mia/commit/0616e92330a8a6033df00e701cb2a587a60e7be8) | Worker阻断与队列配套；用户确认4次/10秒，1后台/2全局/128队列；保留原SDK观察器 |
| 固定观测 | [a229268be63d4dd4bb59cbdf79ec306dc6cc8ca9](https://github.com/bboytang/Mia/commit/a229268be63d4dd4bb59cbdf79ec306dc6cc8ca9) | 冷10k/5暖、固定两臂34Mock SDK与原4chat；旧候选六CI/共享success保留 |
| 复查修正 | [19b503dd08926ae83e5a40d997517eed1d429046](https://github.com/bboytang/Mia/commit/19b503dd08926ae83e5a40d997517eed1d429046) | 新反例证实SDK开始预写不真实，移至SDK内部构建；补夹具SQLite锁且断言不变 |

完整[基线→最终代码diff](https://github.com/bboytang/Mia/compare/858551c2efaa24e76ea421bf3cb946e9c3d5119c...19b503dd08926ae83e5a40d997517eed1d429046)。运行变动仅任务、请求契约、调度、迁移/安装文件清单；没有改reply/context/semantic/retrieval/persona/authorization/memory事实实现、iOS或固件。旧三版SQL字节/hash均复核不变。

### 最终同SHA六项CI（均success）

| 验证 | 结果/链接 |
| --- | --- |
| 服务与V2/迁移/安全/协议 | [352项](https://github.com/bboytang/Mia/actions/runs/39192469096)，含实际子进程崩溃、SDK/HTTP预算及新旧任务；本地companion286项 |
| 身份/Scope/绑定 | [173 Java项及实际Scope集成](https://github.com/bboytang/Mia/actions/runs/39192469044) |
| manager兼容 | [150原Java回归＋4真实基线](https://github.com/bboytang/Mia/actions/runs/39192469064) |
| 真实BGE与安装后提取 | [五份报告全部passed](https://github.com/bboytang/Mia/actions/runs/39192469046)：164检索、10上下文、9回复、14结构提取及向量验证；结构提取RSS305.45MiB |
| 提取契约语法 | [通过](https://github.com/bboytang/Mia/actions/runs/39192469043)，没有dispatch远端模型 |
| 共享资源/观测机制 | [39192505563](https://github.com/bboytang/Mia/actions/runs/39192505563)，39机制＋唯一19b503d cap0固定两臂/四chat |

原始最终CI日志为performance-v2-final-*-ci.log.gz，五BGE报告performance-v2-final-*-results.json.gz，V2服务账本performance-v2-final-mechanisms.json.gz；共享全部artifact hash及原始child/parent/cold-warm另存performance-v2-shared-final-*。总复核报告[performance-v2-final-review.json](verification/mia-persona-memory/performance-v2-final-review.json)保留精确SHA、全部六链接、资源和只读SQLite对照。原a229268六CI/共享、首轮机制失败和SDK marker反例失败均保留，未覆盖第三十三步/第三十四步证据。

### 最终真实资源与调度证据（已证实）

实际共同父组cpu.max=200000/100000、memory.max=2147483648、swap.max=0；MySQL/Redis/Java manager/Python应用/控制器同组。共同峰值**1465.63MiB**、Python整体峰值**436.87MiB**，memory.events全部0。没有把应用RSS冒充隔离encoder增量。应用退出0.470秒，全组空闲退出2.187秒；这不是新V2在途退出验收。

34调度真实SDK＝34 MockTransport入口（每臂16前台＋1后台），另4完整chat Mock SDK；远端0。每臂一真实Worker任务，attempt=1/intent1/SDK观察1/HTTP1。后台four-ten在foreground=2且waiting_foreground=0时获得空闲机会，持续满队老化配额仍由确定性反例单独证明。两臂受控前台最大排队0.035→1918.26ms，是一次固定控制场景，不是线上GLM前台p95或正式600ms首句增量。

ledger显示后台实际槽排队strict约0.51ms、four-ten约1805.90ms；strict的主要等待发生在Worker入口、不能拿这个0.51ms冒充接纳后无等待。只读SQLite原任务created_at→updated_at（秒级精度）分别**27秒/11秒**。驱动observed_terminal_seconds为27.12/22.11秒，后者因等前台全部结束才轮询，**不是后台真正终态耗时**；不拿观察器晚读当调度变慢。6任务全部empty、attempt为1/1/0/0/0/0，source_payload清空、feedback清空，2请求账本；11032夹具事实、integrity=ok、外键无误，读取前后DBhash相同。

### 最终R6/R7归因（已证实与证据边界）

10k首次冷特征读取**1711.60ms**；10000次静态特征构建聚合**1353.79ms**，扫描线程CPU/墙钟**1567.76/1570.53ms**，缓存0→10000。五暖读**263.91/337.27/263.25/260.12/259.18ms**，构建0次、扫描CPU156.64–232.36ms；六完整结果hash一致。冷两BGE调用inclusive90.74ms（并行，不能当墙钟相加），manager2次46.51ms、Python锁0.215ms。已证实首读主要是静态特征CPU，非已测SQLite锁等待；不是模型装载冷启动。

暖读begin两次约10.96ms、snapshot约6.17ms；完整受控chat两个开trace样本在首句前各有21次manager请求（241.35/250.71ms）、15次reply.validate（nested186.38/196.67ms，不能相加）。暖态串行manager复核确有成本；它对原正式912.84ms增量的确切份额仍证据不足，没有安全等价快路径就不删检查。R7完整句校验、原19组件/旧句取消继续通过，无提前释放。四受控ABBA首句633.51/499.81/506.55/587.27ms全部保存；观察on/off只有4次且有资源/顺序混杂，不能因on更快宣称观察器零开销或负开销，也不能当正式p95。

已证实：R5的记账/入口饥饿机制问题有修复及定向证据。高度怀疑：暖态串行授权是剩余正式首句系统性成本之一，但不能删除安全边界。证据不足：真实GLM新V2完整任务稳定性、实际饱和老化配额与新V2在途全组关闭、音频/iOS/硬件实测。**第三批到此停止，不启动第三十六步。** 后续建议维持本节前述评审顺序，待用户审核批准。

## 最终混合版本边界补充

旧V1任务保持计数不意味着豁免安全复核。新增“V1已排队→撤权→取得槽”反例在19b503d失败：attempt仍1、提交被拒，但实际SDK spy已经1，不能接受。原始performance-v2-legacy-preflight-before.log.gz保留。现对V1普通JSON/原生工具路径也在SDK前调用既有Scope/context/取消/deadline复核；不写V2请求账本、不退款或改变V1排队计次。V2事务/SDK内部观察/HTTP预算路径保持；287相关回归通过。新反例现在legacy attempt1/SDK0/HTTP0，终态cancelled。

该补充需要最终源码的必要服务/身份/manager/真实BGE/安装后结构提取及迁移同SHA回归。共享资源已在19b503d完成，request_accounting/model_requests/schema字节未改变，V2分支只保留同一构造调用；提取新增before_sdk分支对V2为None、不产生新I/O。依照用户不重复无意义性能测试要求，不再派第三次共享试验；**性能测量明确标19b503d，不冒充最终SHA实测**。剩余5项必要CI收齐后停止，所有旧19b503d六CI/原始数值/失败仍保留。

补充剩余性能边界（已证实实现，负载影响证据不足）：Worker保存显式事实仍须经SemanticMemoryIndex._background_ready等待前台检索空档后做真实BGE编码；本批两共享控制提案都是有效empty，没有新增事实编码/提交竞争，不能冒充长期记忆正常保存p95。持续检索占满时，这个原有等待也可能耗尽120秒；不能因模型槽公平而宣称整个保存链无条件公平。BGE调度未改，实际负载影响应在后续获批真实提案/正式公平性范围验证，不能删除该保护或延长期限。

## 最终停止点（覆盖以上全部历史接续文字）

**第三批完成并停止，等待用户审核。最终运行代码9861e9724643139fb9ee63a8992597df20a94567。** 末次修正[9861e97源码diff](https://github.com/bboytang/Mia/commit/9861e9724643139fb9ee63a8992597df20a94567)补V1取槽后安全复核，不重定义旧attempt。最终287本地companion通过，以下五项必要**同9861e97 SHA** CI全部success：

| 最终验证 | 精确CI链接 |
| --- | --- |
| 服务/持久任务/迁移/协议/安全，353项 | [39193636385](https://github.com/bboytang/Mia/actions/runs/39193636385) |
| 身份/Scope/绑定，173 Java及实际集成 | [39193636412](https://github.com/bboytang/Mia/actions/runs/39193636412) |
| manager，150原回归＋4基线 | [39193636420](https://github.com/bboytang/Mia/actions/runs/39193636420) |
| 真实BGE/安装后提取/回复/上下文/检索，五报告passed | [39193636304](https://github.com/bboytang/Mia/actions/runs/39193636304) |
| 结构提取契约语法 | [39193636438](https://github.com/bboytang/Mia/actions/runs/39193636438) |

共享资源和39观测机制仍明确来自**19b503d/[39192505563](https://github.com/bboytang/Mia/actions/runs/39192505563)**，不是9861e97重测。最终请求记账/门闩/schema、BGE/检索/上下文/授权/Guard等11文件与该测量SHA字节相同，hash及仅V1安全补充diff见[最终复核](verification/mia-persona-memory/performance-v2-complete-review.json)。V2只保留同一次accounting构造、before_sdk分支为None，不额外产生I/O；没有第三次共享采样。保留该测量的1711.60ms冷特征/259–337ms五暖、21次manager241–251ms、34调度SDK/MockHTTP＋4chatMock、远端0、2CPU/2GiB/swap0共同1465.63MiB/应用436.87MiB、空闲关闭2.187秒等证据；不声称最终SHA另有新性能数值。

最新原始日志/机制/五BGE报告为performance-v2-complete-*，旧performance-v2-final-*专指19b503d，保留不覆盖。V1反例最终CI显示cancelled/attempt1/真实SDK spy0/MockHTTP0/无V2 ledger；其他V2各项保持。所有代码与文档已提交固定分支，.private/与tools/保留，无在途任务。

**不具备直接启动第三十六步正式验收的充分条件。** 当前已解决V2可审计预算、旧/新任务SDK前复核、Worker入口及受控模型后台机会；未解决/未证实的正式暖态首句超限、真实GLM提案稳定性/完整正常成功p95、非空事实BGE提交竞争、新V2真实在途全组关闭和真机音频仍在。保持所有冻结指标、安全规则、两次/120秒、SQLite/BGE/GLM不变；不部署、不改生产、不进入P24或自动启动完整36/72。下一步仅待用户审核本报告和后续验证/性能方案。
