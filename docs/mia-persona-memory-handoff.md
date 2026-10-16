# Mia 人格认知与长期记忆：接续入口

更新：2026-10-16。方案：[V1.2](mia-persona-memory-v1.2.md)。完整步骤：[实施计划](mia-persona-memory-implementation.md)。事实记录：[工作记录](mia-persona-memory-worklog.md)。

## 当前范围与状态

最近状态覆盖下方旧在途记录：scope38970303359已success/36请求，27原回答与只读三owner各1事实复核通过；faults38970307413已failure/18请求，实际截断返回空、非空坏JSON门槛未证，真实SDK超时/两次上限/重复幂等/零事实已观察，但后续恢复未执行。scope/faults-glm53-flashx-*原始证据已保存。tools38970299198仍在途。当前CI控制流候选保留所有门槛，只让独立正常恢复/换PID检查继续执行，最终仍失败直到全部实际满足；6本地项通过，待精确SHA发布与CI。勿重复原失败同代码或在途工具任务。

当前在途精确句柄（均67001b5b、隔离FlashX、各单次已确认in_progress）：tools38970299198、scope38970303359、faults38970307413。先跟踪这些任务并读原回答/SQL/故障包络，不重复派发；同步推进完整app main/WebSocket/HTTP/GC与原Worker共同20秒截止及换PID恢复测试，现有chat-body夹具不能替代。独立v2未执行，P23/P24前置尚未满足。

最新终态：61eaa416的FlashX成长38968076242（39请求）与v1检索38968105383（41请求）均success，已读各27原回答并归档growth/retrieval-glm53-flashx-*。成长三组原模型特点/三后续会话/换PID/删除派生失效通过；v1为15/15结构、四信号真实参与，但原回答仍有自行车说成开车、重要性加强成长期习惯的问题，不能称完整语义通过。两个句柄不再等待或重发；下一项仍为全服务Linux在途关闭/恢复证据，v2保留。P22/P23/P24未完成；新型号仅隔离比较，未获生产采用授权。

2026-10-17用户补充：认可“你从没告诉过我”这类自然未知回答，保留表达，不作为失败或新增限制。临时no_match/unavailable措辞约束已撤回。FlashX自然纠错38968090570三组/21真实请求与15原回答复核通过，证据见verification/mia-persona-memory/natural-glm53-flashx-*；仅此有限用例，非完整P22或生产换模授权。

最新表达要求（覆盖旧表达判定）：用户明确以上游[路遥仓库](https://github.com/insistgang/Luyao_AI_Project)为准，仔细核对、借鉴优点，不要自行限制Mia回答。已实际读取config／guardrails／persona／service／memory及相关测试，HEAD仍为e23c3aa；见[逐项对照](verification/mia-persona-memory/luyao-reference-review.md)。本轮撤掉强制AI声明、意识／拟人体验禁令及额外风格打分，采用亲近、稳定陪伴的人设方向；角色仍是Mia，不硬套阿雾和预置剧情。记忆来源／所属用户／操作结果、授权和权限仍按实际机制验证。此前因泛夸、拟人体验或具体措辞判失败的记录仅作旧要求历史，不能继续当新表达门槛。


最新用户决定：2026-10-15 用户明确要求：“跳过这个验收门槛，后续由我自己测试”。真实跨七自然日的采集、足量后实际对话及变更验收转交用户，不再作为P19／P20开发收尾的阻塞项，也不继续自动采集或提前audit。运行时五观察／三会话／跨七自然日的趋势资格保持；此决定不表示真实长期验收已通过，不删除历史失败或原始证据。

当前用户持续目标：**推进 P21—P24**。P18限定完成；P19／P20实现及受控验证已完成；跨真实自然日的实际验收按用户最新指令转交其后续自测，不再等待日期。整体自然风格仍有已记录限制，未宣称完整真实行为通过。用户追加要求回答自然、像人在聊天，并明确允许“我会一直陪着你”等善意安慰，不强制免责声明。P20真实记录仅第一天，保留为历史证据；用户跳过开发收尾中的跨日验收门槛，运行时趋势资格不变。任意中文纠错语义与完整真实行为仍待P22。实际Provider容量与输出预留仍未核实，保持限制，不部署。此前要求为“开始计划吧，每完成一步就写交接和进度”；继续按 V1.2 和完整计划开发，并在每一步结束更新交接和工作记录。先前“仅修订计划”和“先保存”的暂停范围已由接续指令解除；生产发布仍按 P26／P27 的具体制品、验证与授权范围处理。

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

### 2026-10-17 Windows 接续（当前）

- 当前已发布候选61eaa416c9cfe0ba5f323ca63e243cb41c11250b，含共享关闭628ad9df及显式比较入口；服务38967452279、BGE38967452451、身份38967452410、manager38967452530及两语法均success。全服务Linux关闭/音频实测仍未执行，不能用这些基础回归代替。
- 指定两型号各单次辅助已终态：Flash38967571902 failure/3真实请求/4项执行，前三通过，持续计划在原Worker30秒截止timeout（30033.23ms），无第三次提案/结束元数据；余6未执行，不称SDK HTTP超时。FlashX38967588609 success/7真实请求/10项全部通过，实际请求和响应型号匹配，原模型重要性0.8/肯定引文真实保存、否定null及医疗待确认正确。metadata-glm53-flash/flashx-*完整参数/usage/原文/哈希保留；两版提取/提案producer git blob确实未变。
- FlashX真实manager/BGE三整链各单次已确认in_progress：成长[38968076242](https://github.com/bboytang/Mia/actions/runs/38968076242)、自然纠错[38968090570](https://github.com/bboytang/Mia/actions/runs/38968090570)、v1检索[38968105383](https://github.com/bboytang/Mia/actions/runs/38968105383)，均SHA61eaa416，test_model=glm-5.3-flashx。后续仅跟踪同句柄并读原回答/模型字段/SQL，不重发。辅助unit向量/policy不冒充整链或P22；生产默认/Secrets不改，用户授权仅隔离比较，v2保留。
- 下一独立工作仍是全服务实际生命周期关闭/恢复测试：原app main、WebSocket/HTTP、GC及同一Worker共同20秒预算必须有Linux真实证据。现有受控测试不是全服务验收，不进入P23/P24完成声明。P22仍未完成。

- 比较入口最终104项相关本地检查通过（20.757秒），两个workflow YAML和脚本AST通过。SDK观测补实际response_model/finish_reason/usage，缺失保持缺失，yield原chunk不变、不采推理正文。下一步发布关闭628ad9df与比较入口提交，再对两新型号各单次辅助，逐一记录精确SHA句柄；尚无新型号结果。

- 用户已授权仅隔离CI比较，并明确指定glm-5.3-flash/glm-5.3-flashx。新入口用test_model显式选择，默认configured仍原测试模型；生产/Secrets不改，无自动fallback。官方仅支持开启思考，因此CI专用同Provider参数适配thinking=enabled、函数tool_stream=true，比较预算4096输出/16384保守上下文，原30秒HTTP/0 SDK retry/2 Worker attempts/语料与上限保持。实际请求参数和安全错误包络均记录；[授权与比较边界](verification/mia-persona-memory/model-comparison-authorization.md)。真实效果待执行，不等于生产采用授权。
- 关闭候选628ad9df3abf353af406ff51c13d56610fb61fb7已本地提交；新增比较入口尚待提交/发布。先发布精确候选，再对两个指定型号各一次辅助十项，按原报告决定后续完整整链；旧2a3baf73四项都已失败终态，原文已完整保存，不能重发旧任务。全服务Linux关闭实测/P22/P23/P24仍缺。

- 2a3baf73三行为均终态failure：自然纠错38963414931/18请求，三组两次仍旧内容或不支持的字面线索；成长38963428063/25请求，三组实际四来源均保存且到特点断言，但原模型未提供trait；检索38963440053/27请求，三组第四源原重要性非空但关系锚是新物件、不在旧目标，严格拒绝，15查询未执行。33条原回答已读，目击/独立活动组合仍在。natural/growth/retrieval-task-options-*完整归档；v2未消耗。
- 关闭候选接入原app finally/原Worker：先停止新任务接收，同时取消stdin/WS/HTTP并关闭GC与Worker，使用一个总20秒预算，保留取消传播及退出余量；未完成持久任务不删除，可原路径恢复，不等待不合作的native线程另一个期限。原stop_worker默认20保留，增加可传剩余预算；新增stop_service由原安装补丁调用，没有新服务/事实库。
- 四项新增受控关闭测试覆盖GC延迟/错误、正常在途完成、总截止取消后SQLite恢复、关闭调用本身取消。首次两失败暴露嵌套取消需要多轮调度；有界join后短预算仍不足，实际await链定位到wait_for/_cancel_and_wait已完成Future尚待调度，给短预算足够取消余量（生产20秒仍预留0.5秒）；另修复插入新测试时移位的一条原断言。最终48项Worker/安装接线通过（10.347秒），固定上游app原hash/补丁AST通过；与提取/维护等共103本地项通过（18.626秒，含3比较门控项）。这些不是全服务Linux/音频/20秒实测通过，后续仍需实际生命周期及P23。
- 用户已明确授权仅隔离CI比较，并指定glm-5.3-flash/glm-5.3-flashx；不等于生产采用或部署授权。比较入口候选及官方思考参数要求另记录；真实效果尚未验证，不把新型号说明当通过。P22/P23/P24仍未完成。

- 2a3baf73辅助38963455271已failure：3请求、4项实际执行，前三项（中性事实/医疗待确认/引用为空）通过，持续计划被模型标inferred并造对无关旧事实的shared_term关系，原validator拒绝后retry_wait；按原辅助入口unfinished门槛失败，余6项未执行。schema没有声明该relations字段但模型仍输出，不能声称schema强制有效。metadata-task-options-*完整保留。自然纠错38963414931、成长38963428063、检索38963440053最后再次确认in_progress；跟踪同句柄，不重复启动。该候选服务/BGE/身份/manager四基础均已success。

- 最新发布代码候选2a3baf73f24fc86f5a364a649b3e0dc312691ba7（Git数据API逐对象同SHA核对、非强制快进）。四项各单次创建并确认在途：自然纠错[38963414931](https://github.com/bboytang/Mia/actions/runs/38963414931)、成长[38963428063](https://github.com/bboytang/Mia/actions/runs/38963428063)、v1检索[38963440053](https://github.com/bboytang/Mia/actions/runs/38963440053)、辅助十项[38963455271](https://github.com/bboytang/Mia/actions/runs/38963455271)。基础服务38963357454和提取语法38963357628已success，manager38963357455/BGE38963357469/身份38963357450在途。下次只跟踪同handle，读取原文/实际SDK/SQL，不重发。
- 78b8965b四项均已失败终态并归档；以下旧“在途”仅历史。下一独立实现项是全服务共同关闭期限：先补实际生命周期验证，再按证据修复；不把Worker单项或模拟时钟当P23全服务验收。P22/P23/P24仍未完成，独立v2未消耗。

- 78b8965b四项已全终态failure，不重发：自然纠错38962029349/15请求，第一/三组更正输出inferred/旧内容/非共享anchor及关联，第二组首事实就造空目标更正；成长38962044977/15请求，三组第二事实均造更正/非法关系，未到第四源；检索38962060012/18请求，第一组第二源非法关联，第三组首源空目标更正，第二组第四源先真实0.9但非法关联、再漏重要性被新guard拒绝。20条实际前台原回答已读，长笛目击仍在；natural/growth/retrieval-function-contract-*完整原文/SDK/SQL/哈希保存，v2未消耗。
- 辅助38962075573只有2请求/2实际样本，首样本保存，医疗样本实际函数流只含空content/无tool事件且complete=true，Worker在retry_wait/invalid_output，入口按原有unfinished门槛失败；余8项未执行。metadata-function-contract-*保留，不能报十项整体9/10或SDK超时。
- 新候选依实际无目标更正输出，收窄提供给模型的schema：只有真实自然纠错任务声明reconciliation，且kind只允许explicit；旧完整分号协议仍先由原preflight处理。无可能字面共同锚或自然纠错任务不展示relations项目模板；字段缺省沿用原parser空关系，绝不删除/修补实际模型输出，若仍输出不支持字段原validator继续拒绝。原模型/Scope/事实库/Worker/两次上限不变。96本地相关项通过（18.868秒），真实待新SHA。
- 关闭证据仍缺。只读固定上游app.py发现当前安装补丁先stop_worker(timeout20)、再GC.stop、再服务任务wait3，尚无共同总期限；这是源码风险，不是实测超时，不能以现有空闲约0.13秒称全服务在途≤20秒。后续需实际生命周期测试和必要修复，不提前把P23判通过。P22/P23/P24仍未完成。

- 当前已发布HEAD：78b8965b522e4e41670c104fb7e00c935135c0c2，运行代码候选b84556a6bd17ebba5ed9db37c5edba52f085da49。Git HTTPS依然连接失败，但官方Git数据API正常；通过既有gh认证上传本地对象，两个提交的每个blob/tree/commit SHA均与本地严格一致后才force=false快进任务分支。未重建不同历史、未读出密钥。可复核远程Git commit API及分支引用。
- 四项各单次创建并确认在途：自然纠错[38962029349](https://github.com/bboytang/Mia/actions/runs/38962029349)、成长[38962044977](https://github.com/bboytang/Mia/actions/runs/38962044977)、v1检索[38962060012](https://github.com/bboytang/Mia/actions/runs/38962060012)、辅助十项[38962075573](https://github.com/bboytang/Mia/actions/runs/38962075573)。自动基础服务38961981041/BGE38961980914/身份38961980955/manager38961980942在途，提取语法38961980936已success。后续跟踪同句柄，不重发、不把观察超时当终止。b0aa3501五项全部终态且完整归档，独立v2仍未执行。
- P22仍缺成长/派生失效、自然纠错及回复来源语义、全服务在途关闭和最终回归；P23/P24未完成。本地96相关项已过只证明机制，不能提前称新模型效果通过。

#### 既往验证记录（倒序；旧在途描述以对应终态记录为准）

- 本地新代码候选b84556a6bd17ebba5ed9db37c5edba52f085da49已提交，尚未推送。推送schannel正常助手/浏览器UA均连接中断，OpenSSL后端报github.com:443连接失败；保持证书校验，未改历史/远程。最后API核实远程仍5c14778dd2a1d69de83a9ef737126cdb92cb619f。b0aa3501的五运行均已终态；没有新候选运行在途。下一次先核对本地/远程，正常push成功后才各单次启动自然纠错/成长/v1检索/辅助十项并记录精确SHA句柄，不以旧成功代替新提交验证。当前是连接失败而非审批拒绝；P22/P23/P24继续未完成。

- b0aa3501五项均终态，不重发。基础服务38959575280/BGE38959575255/身份38959575350/manager38959575190及两语法全success。faults38959647587 success/27请求，函数路径原始坏JSON/真实超时/重复/正常恢复/实际PID召回通过，空闲关闭约0.13秒，十二回答已读；faults-optional-*保存。
- v1检索38959633592 success/41请求，12真实事实和15结构检查全通过：S/L/A/E参与、肯定重要性实际入库、目标全召回、三无关空召回、三活动扩展。27原回答已读，仍把跑步与拉伸组合、声称记得拉伸后感受、从相机/录音笔习惯推重要性。retrieval-optional-*保留；硬门槛虚构来源仍未满足，不报完整B04语义或P22通过，不消耗独立v2。
- 自然纠错38959608746 failure/21请求，第1/2组机械生命周期通过，第0组两次仍拼接非字面anchor。13回答已读，目击长笛练习及口误说成实际变化仍在，pending投影不能独自解决语义；natural-optional-*保存。成长38959619823 failure/27请求，三组第四源都输出无依据importance=1而拒绝，trait未产生；实际SDK finish_reason=tool_calls、用量远小于768，没有截断证据，12回答已读，growth-optional-*保存。
- 辅助十项38959662648 failure/7请求/8通过：肯定意义原模型漏两字段，schema required没有被遵循，原后端仍提交null；否定句给无依据0.5及无关证据并带末尾孤立fence，invalid_output，不将拒绝归因于某个单独guard。metadata-optional-*完整保存，辅助unit向量/policy不替代整链。
- 当前新候选修复明确本人肯定重要性却漏值仍提交的缺口：三种旧/新/缺失字段先复现失败，改为原校验错误，既有Worker同job第二尝试可收到实际诊断，不填分、不追加尝试。函数路径不再沿用要求JSON/null的文本模板，改为一份一致函数契约；原文本Provider路径保留。成长仍需实际三个独立来源及共同原文锚，模型决定提案，后端不造特点。96相关本地项最终通过（16.274秒），真实效果待下一SHA。P22/P23/P24未完成。

- 最新已推送候选b0aa35013f385a4a407237ca6157bf8bae774311。五项各单次创建：自然纠错[38959608746](https://github.com/bboytang/Mia/actions/runs/38959608746)、成长[38959619823](https://github.com/bboytang/Mia/actions/runs/38959619823)、v1检索[38959633592](https://github.com/bboytang/Mia/actions/runs/38959633592)、faults[38959647587](https://github.com/bboytang/Mia/actions/runs/38959647587)、十项提取[38959662648](https://github.com/bboytang/Mia/actions/runs/38959662648)。基础服务38959575280/BGE38959575255/身份38959575350/manager38959575190最后在运行；两语法38959575258/38959575220已success。下一次只跟踪同handle，不重发。Git manager凭据助手HTTPS两次中断，改用已登录gh标准git-credential后正常推送，不读取/复制密钥或更改模型。

- c993c2df四项已全部终态：自然纠错38954791650 success/21请求，三组同ID替换、换PID召回、删除重启无复活；faults38954807774 success/27请求，真实非空坏JSON、SDK超时、重复提交、两次失败、后续正常保存与重启召回通过。关闭只是空闲关闭，不是完整在途关闭。natural-function-*、faults-complete-*保存原文和SQL。
- 成长38954797360 failure/27请求：第0/1组第四源原importance=1无依据被拒绝；第2组第四源第二次保存成功，到了真实trait存在断言但null。检索38954802420 failure/21请求：三组第三源原模型关联词不在新原句被拒绝，15查询未执行。growth-function-*、retrieval-function-*保存全部原文、输入、哈希和SQL。48条前台原回答已读，仍有把口误说成实际变化、无来源目击及独立活动组合；机械成功不等于完整语义通过，独立v2未消耗。
- 下一候选：具备既有函数接口的提取都使用同一次原Provider函数提案；可选字段改为基本类型，未表达重要性/不具备成长资格则schema不声明字段，不替模型填值。实际明确第一人称肯定重要性才要求相应字段；关系目标只排除不可能满足原两字字面共同锚的记录，原校验仍决定接纳。官方文档未明确承诺nullable/anyOf，不认定其不支持或是已证明根因。原SDK/模型/两次上限/Scope/Worker不变。
- 已复现并修复否定重要性证据裁剪漏洞（两种字段名共六负例先失败），补原提示已支持却漏掉的“重视”；双重否定/同句后续肯定仍可由原模型给证据。真实输入发现pending事件带已互动影响描述但assistant_evidence为空，改为仅状态投影；完成后同ID事件恢复实际引文，激活/失效不变。95项提取/Worker/安装接线通过（15.512秒），50项上下文/连续事件/回复通过（23.726秒）；真实候选尚待验证。CI新增实际finish_reason/usage观测及函数路径原始故障/输出记录，无输出改写。
- 下一项提交候选，单次对应SHA运行自然纠错/成长/v1检索/faults及辅助十项，跟踪自动基础回归。P22仍缺成长及失效、完整四维/v2、语义、全服务在途关闭及最终回归；P23/P24未完成。

- 最新已推送候选`c993c2df18e3fd3da66f062dffa0741bf4be4eeb`，四项各单次已确认in_progress：自然纠错[38954791650](https://github.com/bboytang/Mia/actions/runs/38954791650)、成长[38954797360](https://github.com/bboytang/Mia/actions/runs/38954797360)、v1检索[38954802420](https://github.com/bboytang/Mia/actions/runs/38954802420)、真实故障[38954807774](https://github.com/bboytang/Mia/actions/runs/38954807774)。继续同handle，不重发。先核对实际SDK是否提交schema/输出tool deltas及原参数、最终仍过原校验；任何实际效果未验证前不称修好。v2尚未执行，P22/P23/P24未完成。
- 当前新增候选复用原Provider.response_with_functions传递一项mia_memory_proposal结构提案（不是执行工具），仅自然纠错/重要性/有来源成长任务启用；原Worker、两次总尝试、来源/Scope/版本校验及事实库不变。参数从模型原始SDK delta拼接，无字段回填；歧义/混合/超长函数提案拒绝。schema约束合法类别/类型/已有ID及服务器实际拒绝值；无重要性字面来源时只允许null，符合原校验，不填数值。其他来源原提取及不支持函数的Provider仍单次原文本路径。CI保存实际tools输入、原始tool deltas与参数；安装包纳入proposal.py。91项相关本地回归通过，真实效果待精确SHA，不能提前称问题解决。
- 0c187fa2故障38952671390已failure/18请求：六次实际SDK超时（APITimeoutError→ReadTimeout），每用户两故障任务两尝试后failed、0事实、原事件重复submit同ID、前台在pending已送达。但max_tokens=1得到空Provider文本，未达到非空坏JSON门槛；正常恢复/重启/空闲关闭后半未执行。[原文/SQL](verification/mia-persona-memory/faults-first-review.json)。候选只将CI截断预算改为8，不制造错误响应、不降低非空坏JSON条件；实际模型/生产参数不变。
- 最新被测fb04e470三项均已终态failure：成长38951258078为27请求，第四源模型无依据importance=1被拒绝、trait仍null；自然纠错38951263722为19请求，第2组机械流程通过，其他组非字面anchor/keyword仍失败；检索38951269010为24请求，六条肯定重要性模型原值非空，但三条普通家传物件被模型sensitive=true待确认，所有查询未执行。[growth-task](verification/mia-persona-memory/growth-task-review.json)、[natural-diagnostic](verification/mia-persona-memory/natural-diagnostic-review.json)、[retrieval-task](verification/mia-persona-memory/retrieval-task-review.json)保存全部原文/SQL/哈希。独立v2未消耗，P22/P23/P24未完成。
- fb04e470四基础38951256082/38951256124/38951256083/38951256068及提取语法38951256060全success。下一项不能重复同源码取绿，需继续改善原模型结构提案，而不是放宽字面证据或替原模型填metadata/特点。
- 新faults入口只改CI验收：提取专用max_tokens=1观察原Provider真实截断文本、read_timeout=.001观察真实SDK超时，同一模型/密钥/原Worker/真实Scope；原回复仍768/30秒，故障参数不用于生产或普通任务。实际完成事件原对象重复submit验证幂等，两个故障任务两次后failed且无事实，后续普通任务/换PID召回和空闲关闭检查。原始响应不替换，不预设失败或成功状态。AST/冻结三组原句与已安装SDK显式timeout参数通过，真实结果待精确SHA；在途/全WebSocketServer/P23关闭仍未验收。
- 上轮176d332f/38950019670已终态failure/21请求；两组生命周期通过，一组仍非字面关键词拒绝。实际SDK确认第0/1组各一次校验诊断送达，退避缓存修复已实证，但不能称自然纠错整体通过。[完整原文](verification/mia-persona-memory/natural-backoff-review.json)。该SHA服务38950018322/BGE38950018277/身份38950018289/manager38950018281全success。
- Scope真实三组矩阵已通过并复核（38948211936，36真实请求）；成长38948865306仍trait:null，v1四维38946430905尚有一条重要性null及部分无依据事实组合；独立v2留出未消耗。完整P22/P23/P24保持未完成。
- 当前候选：同一提取器按实际任务选择聚焦重要性或成长任务，避开通用null例子；成长仅在真实三独立来源资格后审阅，原模型仍需输出实际主题/ID/引文/表达倾向，示例为无关观云格式，不是用户资料。自然纠错机制不改，第二尝试额外得到服务器实际拒绝的clue数据，清楚标为诊断而非新来源，不能由后端代填正确词。原模型/两次上限/事实库/Scope/原校验保持。
- 原回答事实组合与无来源目击仍未通过；上下文只澄清用户自述/实际双方互动/并列事实不证明关系，没有新增表达拦截、免责声明或伴侣角色限制。63项提取/Worker/维护及49项上下文/事件/回复本地回归通过；真实效果待新精确SHA。下一项提交后各单次自然纠错、成长、v1检索，读全部原文再决定后续，不消耗v2取绿。

### 接续历史（下列在途状态仅代表记录当时，当前以上节为准）

- 最新运行候选`176d332f27fdd3bce94640ff66db70ed81bf4dd9`已推送，退避缓存修复自然纠错[38950019670](https://github.com/bboytang/Mia/actions/runs/38950019670)已单次发起，待终态/实际SDK反馈送达与原回答复核。上方旧38948366421/38948865306/38948211936均已终态；不重复启动。下一项跟踪38950019670，继续重要性剩余一条/成长真实生成/完整后台故障及最终回归；P22未完成，P23/P24依原前置推进。
- Scope矩阵38948211936已success：三轮36真实请求/27独立WSS会话，三用户/Agent事实范围及同范围多设备共享、旧凭据三处拒绝与重绑新Scope召回通过；27原回答逐条已读，18召回只含本人事实。各库三个owner各一事实、完整性ok；[完整原文/SQL](verification/mia-persona-memory/scope-first-review.json)。仅验收所列B06矩阵，最终相关回归和App真机范围分别记录。
- 自然纠错38948366421已failure/21请求，两组机械生命周期通过、一组非字面关键词拒绝；实际SDK证明0次诊断送达，不能将改善归因于反馈。[原文及根因](verification/mia-persona-memory/natural-feedback-review.json)。已复现ready()不包含退避未到期任务、导致缓存过早清理；候选改按实际活动任务保留。加入三次退避轮询前失败，修复后62项本地通过；中间测试还错误假设两个任务先后，改按真实Scope核对反馈归属，不变更调度机制或门槛。
- 成长3dd11dcf/38948865306已failure/24请求：四原句均保存，已越过规范化比较，确实停在trait存在断言；实际输入证明成长说明与三个独立已存来源已送达，原模型仍null。后续未执行，[growth-review原文](verification/mia-persona-memory/growth-review-review.json)保留。下一步仍需改进同一提取任务的真实特点生成，不能预置或把null变成特点。
- 校验反馈候选`8f3a81d0d5b5cc7647c2b2469e3c616cc28846d7`已推送，自然纠错[38948366421](https://github.com/bboytang/Mia/actions/runs/38948366421)单次运行中；服务38948363595/BGE38948363545/身份38948363568/manager38948363624/提取语法38948363551均success。Scope38948211936仍in_progress，同handle跟踪。
- 下一成长候选在原一次提取中，仅当三个实际独立会话/原句达到结构资格时追加成长审阅；主题/有限表达倾向/实际证据id与引文仍须原模型生成并过原校验，数量合格不等于语义支持。无另建系统/第二次模型调用/预置特点，普通与自然纠错来源不改。62项本地回归通过，待精确SHA growth验证；原首轮失败及harness规范化修复保留。
- 新结果：f3fd25f7自然纠错38946424108为19真实请求（6/6/7），第三组同ID更正/换PID召回/删除后重启不复活通过；第一组非字面anchor、第二组非字面关键词被拒绝，整体失败，原回答仍有无来源目击。[natural-projected原文](verification/mia-persona-memory/natural-projected-review.json)。v1检索38946430905为39请求/14结构通过（15项执行），五个实际重要性非空，演奏热身仍null，且原回答有无依据事实组合，整体失败；[retrieval-categorical原文](verification/mia-persona-memory/retrieval-categorical-review.json)。独立v2未执行。
- Scope测试41181be5已推送，真实矩阵[38948211936](https://github.com/bboytang/Mia/actions/runs/38948211936)单次启动，待终态。前两次HTTPS push中断，首次其后dispatch因远程尚无scope选项422未创建run；第三次正常Git设置push成功后才启动上述run，不重复。
- 当前候选给原Worker同一任务的原第二次尝试传递真实服务器校验诊断；每次仍一次原Provider调用，两次总上限不变；不修改模型输出/原句/校验门槛。反馈仅进程内、有界、按job隔离，不持久化用户或模型正文；数据库validated重试与Scope恢复机制保持。细化字面anchor/clue错误原因，61项本地回归通过（含另Scope任务不收到该反馈、原提案不改、一事实与两次上限）。待精确SHA自然纠错验证，不能提前称修好。
- 新scope测试入口补同用户同Agent多设备共享、同用户其他Agent及其他用户隔离、第二设备解绑/重绑/新旧凭据；三轮均真实manager签发/模型/BGE/原Worker，不预置事实。AST/固定语料检查通过，待精确SHA Actions，不将入口存在称B06验收完成。
- 最新已推送运行候选`f3fd25f71478389e1db9e755039f3531072017b4`：自然纠错[38946424108](https://github.com/bboytang/Mia/actions/runs/38946424108)、v1检索[38946430905](https://github.com/bboytang/Mia/actions/runs/38946430905)已各单次启动，待终态/原文复核；不得重发。成长首轮已终态失败，harness规范化比较随此候选修正，尚未复跑；未改变运行时特点策略或声称特点生成成功。
- 本轮三run均已终态失败：自然纠错38944900792为18真实请求/三组拒绝错误提案；v1检索38944905941为39请求/13项结构通过（15项全部执行），两条fact类别肯定重要性仍null，完整B04不通过；成长38945297243为24请求/四源均已入库，但测试原逗号比较忽略既有NFKC而提前失败，原模型trait也均null，后续步骤未执行。完整原文/哈希/只读SQL分别见[natural-focused](verification/mia-persona-memory/natural-focused-review.json)、[retrieval-grounded](verification/mia-persona-memory/retrieval-grounded-review.json)、[growth-first](verification/mia-persona-memory/growth-first-review.json)。
- 当前下一候选：自然纠错只向原模型提供所属事实id/category/content（原校验上下文/版本不变），补与语料无关的完整合法格式示例，避免复制旧记录/序列化元数据；一般提取明确重要性独立于category，并让既有肯定示例使用fact。原模型输出不加工，不回填数值；60项本地回归通过。成长只修验收比较为既有normalize，暂不修改成长运行策略。独立v2尚未消耗，P22/P23/P24未完成。[完整覆盖缺项](verification/mia-persona-memory/p22-status-matrix.md)。以下在途记录已成为历史。
- `a4dfd5b9c5c2ff9a40ffe1155a10b15fe37b9c91` 聚焦纠错候选已推送。真实自然纠错[38944900792](https://github.com/bboytang/Mia/actions/runs/38944900792)与v1检索[38944905941](https://github.com/bboytang/Mia/actions/runs/38944905941)均已单次启动，最后确认in_progress；跟踪同handle，不重复发起。服务38944864392、身份38944864510、manager38944864650及两语法38944864445/38944865916 success，BGE38944864314仍in_progress。
- 新冻结成长v1：三用户各四个实际原句/独立会话，前三会话不能提前出现特点，第四次原模型根据已有三个来源提案；不预置特点/证据。新增growth入口复用原manager/Provider/BGE/Worker，并检查三个后续新会话、实际重启、删除全部支持来源后再次重启及特点/关联事件失效。只新增验收入口，不修改运行时成长策略；AST与语料一致性检查通过，真实结果待验证，不能称B01/B05完成。
- `334fab62` 的真实提取[38942549414](https://github.com/bboytang/Mia/actions/runs/38942549414)十项/七请求全部通过；模型原文肯定权重0.8和证据“特别的意义”实际入库，否定原句与null正常。[原始输入/输出及限定复核](verification/mia-persona-memory/metadata-grounded-review.json)。不能归因于某一提示句，也不是完整四维或独立留出通过。
- 同SHA自然纠错[38942543137](https://github.com/bboytang/Mia/actions/runs/38942543137)17请求仍三组失败：模型拆句/遗漏协调证明，第一组还造了非法category/relation/拼接证据；原校验器拒绝。第一/三组各两次是原Worker生产尝试，不是重新评估取绿；后半段重启/删除未完成。[原文与SQL状态](verification/mia-persona-memory/natural-proof-review.json)保留。
- 新聚焦候选仍在同一LLMMemoryExtractor内、一次原Provider调用；仅对真实已知上下文的自然更正选择更正任务，要求原模型完整输出证明，不后处理拼造事实。普通事实/重要性/趋势路径保持；原输入、原输出、两次总尝试及版本/唯一目标/不确定拒绝不变。验证报告记录实际extraction SDK messages。60项提取/维护/Worker本地回归通过，真实效果待精确SHA的自然纠错及v1四维整链。

- 新增接续：`12a487ce8c509a6c3d408e1807159da1aae8c21e` 的重要性边界真实提取38940390130仍9/10失败，七次真实输入与哈希证明开关说明已传入；不能认定模型忽略开关是根因。[原文与复核](verification/mia-persona-memory/metadata-consent-review.json)。服务38940388765、BGE38940389018、身份38940388749、manager38940388901、语法38940388897均success。
- 自然纠错v1三组语料已在 `ad4fae45` 冻结，未改运行时的首轮[38940763536](https://github.com/bboytang/Mia/actions/runs/38940763536)14请求、三组均未达到同ID更正：第一组预检误作转述，第二组模型拆句被丢弃，第三组作为新事实保存而旧事实仍当前。重启/删除后半段未执行；原回答还有无来源的目击练习细节。[完整失败/SQL摘要](verification/mia-persona-memory/natural-first-review.json)保留，不把自然亲近本身判失败。
- 自然纠错候选新增模型原提案 `form=natural`：实际旧/新值与共同主题须有字面来源、唯一所属目标、完整原句证据和原版本；拒绝他人目标、歧义、无明确纠正、不确定/真实时间变化及缺少分类。沿用原Worker/事务/向量/事件维护，不按相似度猜目标、不拼造标准用户命令。仅允许明确第一人称纠错前缀进入原模型预检。上下文补充旧更正说法不等于真实过去、用户自述不证明Mia目击；不新增AI免责声明或拟人风格限制。本地59项提取/维护/Worker、49项上下文/连续性/回复测试通过；真实效果待新SHA验证。

- 从干净的 `62d576d350ac9cd2e0522e1979890f2b9dc7e77b` 接续，GitHub CLI 已验证访问。用户最新要求本地能完成的自动检查优先本地，Linux/macOS整链仍在Actions；覆盖下文历史“只在GitHub测试”的安排。未读取或复制密钥。
- `139bc0f` 服务38899855195、BGE38899855056、身份38899855771、manager38899855014均success。真实提取38899986696已failure，十项/七请求/九通过；肯定意义原输出及SQLite重要性仍null。[原文与复核](verification/mia-persona-memory/metadata-importance-review.json)已无损归档。字段改名未修复真实质量。
- `62d576d` 行为38932388755仅syntax成功，composed skipped；后续单次运行的[恢复38937376427](https://github.com/bboytang/Mia/actions/runs/38937376427)已success。三用户共9真实请求：真实写锁失败、validated结果存活、原子进程被kill、不同PID恢复，提取/resolver不重复、各1事实/1向量/1committed+1empty、三库完整性通过。六条回答已读，三条新会话召回均回答本人事实；[原文/SQL摘要及限定复核](verification/mia-persona-memory/recovery-first-review.json)。只验收B03这个故障路径，不代表完整P22/P23。
- 上一运行候选 `6fe7e356c55e8db34404875b18f8d2d125e4c159` 已推送：只统一提取提示完整字段契约与逐来源重要性核对，原校验器、存储、模型和检索参数不变。本地45项提取/Worker修改前后通过；服务38938427388、BGE38938427379、身份38938427390、manager38938427261及语法38938427292均success。
- 单次真实提取[38938475733](https://github.com/bboytang/Mia/actions/runs/38938475733)已failure，十项/七请求/九通过；肯定意义仍由模型原样输出null。[完整失败证据及基础回归](verification/mia-persona-memory/metadata-contract-review.json)已归档，不把提示结构修订称真实质量修好。固定上游基类确实将system/user传给既有response生成器，源码检查未发现系统提示丢失；不能据此断言模型选择null的具体原因。
- 下一项：提交当前聚焦纠错候选，分别单次执行自然纠错与v1四维整链；重要性辅助已通过，完整检索质量仍待验证，独立v2尚未消耗。继续原计划完整身份/成长及其他故障矩阵；P22未整体验收，P23/P24未完成。334fab62既有run均已终态。无生产部署、自动日采或新表达限制。

### 先前候选与证据（历史，不作为当前在途状态）

**本地接续更新**：代码基线139bc0f，重要性模型字段兼容候选五项GitHub run待核实；5319646检索38899281656已failure。新增recovery测试候选、retrieval-signals-*失败证据及[本地接续指令](mia-local-codex-handoff.md)随本次交接提交保存；直接拉取包含本段的最新任务分支即可，无需重复应用zip差异包。下文5319646是在此之前的已验证运行基线。此前远程读取受自动审批额度限制，本次fetch已恢复；未验证候选仍不能视为通过。

当前运行候选 `5319646ff708ea11001a31d5ee309e11f4be2481`：提取提示已有真实来源／分类／否定保留示例，本次继续明确“活动→物品”的触发词和用户明确重视的含义；不加工原模型输出、不后填元数据、不改来源校验或冻结检索参数。GitHub语法38898906597、服务38898906830、BGE38898906791、身份38898906739、manager38898906676均已success。十场景真实提取38898964409已failure／7请求／10项9通过：活动触发词真实保存，肯定意义的权重仍null，详见metadata-signal-*。完整v1检索回归38899281656已确认in_progress（suite=retrieval、SHA5319646）；先跟踪这个同一run，不因观察超时重发，不将辅助九项通过称整体通过。

上一个运行候选c064b60的服务38898312570／BGE38898312443／身份38898312589／manager38898312562均success。真实提取[38898348531](https://github.com/bboytang/Mia/actions/runs/38898348531)仍failure，10项／7请求／8通过，所有任务达到committed或empty；器材实体与关键词已有，活动触发词却仅物品名，肯定意义的重要性仍null；否定重要性完整原句及null正常。详见[实际元数据](verification/mia-persona-memory/metadata-categories-review.json)。前两轮全量失败与示例类别失败均保留metadata-complete-*／metadata-examples-*，不能只报八项通过。

B08实际十场景矩阵在[38897863755](https://github.com/bboytang/Mia/actions/runs/38897863755)已success，d1ef337／运行模块b2d5a1c，三组各23共69真实请求。30结构及30预期语义结果通过，含21普通回复和9超限／删除／撤权处理；三库最终0事实、0事件，任务各1committed＋8empty。见[原文与人工复核](verification/mia-persona-memory/tools-d09-review.json)。原D09不要求模型同代必须多调用，此前agent额外断言已撤除，真实工具闭合／权限／当前问题／预算仍全检查；native并行实际覆盖仍无。旧21／30和24／30报告不改，相同输入是回归。后续提取提示更改仍须最终候选相关回归，不能据此报完整P22通过。

B04首次真实检索38891089842的39请求／12事实／15查询已全部保存：S／L／A实际贡献、候选无遗漏、相关回答正确，但E全null和指定活动关联无扩展导致失败，原证据retrieval-first-*。v1现在只作回归。新的独立v2（新活动／物品／重要性表达／问法）已在0dfa6a0冻结，`suite=retrieval_holdout`接入同一真实manager／BGE／Worker及评分检查；语法38898831820成功，真实v2尚未执行。当前完整v1回归38899281656在途；先读它的真实提取／SQL／评分与原回答，再决定独立v2执行，不用预置线索或改阈值获得通过。

明确更正三协议在7ef9a46／38890796048已完成三组流程及有限语义复核，见correction-speaker-*；在途删除c625c55／38894890125的三个真实可写结果删除后被原Worker取消、重启无复活，25真实请求，见inflight-prefix-*。茶组最后仍答自身偏好，仅机械在途机制通过；任意自然纠错及完整语义不能据此记通过。来源预检和命令前缀相关失败／修复见extraction-preflight-*、inflight-first-*及metadata-interrupted-*。

用户指定路遥HEAD于2026-10-16重新核实仍e23c3aa，九文件hash全部匹配，见[逐项对照](verification/mia-persona-memory/luyao-reference-review.md)。不新增拟人／亲近表达门槛。最终上线模型与共同往事澄清均未收到回答，继续现有glm-4-flash，不更换模型或Secrets、不默认选项已答。真实跨七自然日由用户自测，不自动续采，不部署。

P22仍需元数据／关联整链与独立留出、任意自然纠错、后台故障及身份矩阵、特点成长／派生失效等；P23资源／延迟／公平性和P24定制补丁升级／回滚未完成。P21已完成必要实现与GitHub验证，真机仍另验。完整失败历史见工作记录和各原始报告。

当前步骤：**P21已完成必要实现与GitHub验证；P22真实整链及路遥表达对齐进行中，P23—P24随后推进**，见[事件与授权趋势](verification/mia-persona-memory/continuity.md)，见[维护实现及边界](verification/mia-persona-memory/maintenance.md)，见[结构提取说明](verification/mia-persona-memory/extraction.md)，见[持久任务说明](verification/mia-persona-memory/jobs.md)；P15接线模块及受控验证已通过，见[唯一回复接入说明](verification/mia-persona-memory/reply.md)。此前推送阻塞已在本轮正常审批后解除，未绕过审批。P14模块验证通过，见[上下文说明及结果](verification/mia-persona-memory/context.md)。P13模块与受控验证通过，见[四维检索说明](verification/mia-persona-memory/hybrid-retrieval.md)、[D04规格](verification/mia-persona-memory/retrieval-selection.json)。P11基础通过，完整Persona联动仍进行中；P12—P14整体仍待主链及真实manager＋BGE＋Provider联动验收。P08实际App／入口及真机未封板，未部署。

跨日最终验收入口已补（仅验证脚本／workflow，`50a8bac0302ff2b2ab19d481ebbec6cc0943b48e`，运行代码仍6b57337）：足量daily制品后执行mode=audit、previous_run=<最后成功daily run>，仅对只读备份audit.sqlite3纠正／删除／停用，最多四次实际回复，原库hash不变。当前首日制品38785441525的提前audit验证[38791285449](https://github.com/bboytang/Mia/actions/runs/38791285449)按预期failure，audit_gate=insufficient_real_calendar_evidence、requests=0、原库未改；语法38791286696成功。这只是拒绝提前验收的证据，四回复正向路径仍待真实足量记录，不能标完整。daily新的real_calendar_threshold_met仅日期门槛，不直接表示real_longitudinal_complete。原计划下一实际日期续采daily，现已由用户接管，不再自动执行；整体自然语气仍有未通过样本，保留为真实行为／表达质量的后续验证项；本段为用户接管前的历史验收记录。

最新运行源码`6b57337147f4440488c6a37bda97c003a2cbca5e`：修正停用后管理接口仍聚合，所有趋势入口停用后返回disabled，原观察可看，重启用再计算。服务[38790445454](https://github.com/bboytang/Mia/actions/runs/38790445454)227项、实际BGE[38790445677](https://github.com/bboytang/Mia/actions/runs/38790445677)、身份[38790445440](https://github.com/bboytang/Mia/actions/runs/38790445440)173项／TLS／WSS／JAR及manager[38790445517](https://github.com/bboytang/Mia/actions/runs/38790445517)150＋独立4全部通过。人格提示e48f222移除可被照搬的安慰示例：四项实际基础38790043658通过，但真实对话38790040373在reflection仍泛夸，被新增检查拒绝，仅4次、后9项未执行；不重试取绿，不放宽规则。整体自然语气仍部分未完成。逐项要求／缺项见[验收审计](verification/mia-persona-memory/continuity-requirements.md)。跨日足量后的变更与对话入口已补，其实际验收由用户自行执行；不得将仅首日证据称真实长期验收通过。以下保存旧提交结果以供审计。

当前P19／P20运行源码`92d7476c97ea764c98f86db3a665352018551818`：服务[38789126978](https://github.com/bboytang/Mia/actions/runs/38789126978)226项、实际BGE[38789147018](https://github.com/bboytang/Mia/actions/runs/38789147018)、manager[38789127166](https://github.com/bboytang/Mia/actions/runs/38789127166)、基础实际模型[38789126301](https://github.com/bboytang/Mia/actions/runs/38789126301)四项通过；实际安慰“我在，会陪着你的。”符合本次用户要求。13项实际对话[38789151188](https://github.com/bboytang/Mia/actions/runs/38789151188)工作流绿，但泛夸／不直接作选择／无关问题复用安慰句仍偏模板，Codex未验收整体自然风格。身份旧断言两轮失败：仍把陪伴话当禁语；d9184ef仅改该验证夹具及工作记录，[复验38789512688](https://github.com/bboytang/Mia/actions/runs/38789512688)173项／23专项、真实TLS／WSS与JAR通过。精确SHA／范围及原始报告hash见[本轮CI](verification/mia-persona-memory/continuity-ci-results.json)与[语义复核](verification/mia-persona-memory/continuity-interim-review.json)。P19机制受控通过，不以自动风格关键词全面背书；P20当时尚缺真实日期证据；用户随后接管该项实际验收，历史结果不变。

P18历史验证提交：`d15a1dc1b567829f692286ba4d5140e2273c5cb1`。服务[38780330886](https://github.com/bboytang/Mia/actions/runs/38780330886)205项全通过（11项P18）；真实BGE[38780318027](https://github.com/bboytang/Mia/actions/runs/38780318027)三种协调、DB回滚复用、第二连接旧快照拒绝及P12—P17回归通过，共18次合成SDK请求、无真实聊天调用；身份[38780354674](https://github.com/bboytang/Mia/actions/runs/38780354674)173／173＋23专项、实际TLS／WSS本人纠正／外人拒绝、类范围与JAR通过；manager[38780332867](https://github.com/bboytang/Mia/actions/runs/38780332867)150＋独立4／字节对照通过，脱敏9项继续通过。见[机制和保守格式边界](verification/mia-persona-memory/maintenance.md)、[精确run和hash](verification/mia-persona-memory/maintenance-ci-results.json)。首轮NFKC标点缺陷、关联夹具错误及BGE把当前用户问题误当召回内容的断言失败均保留，未改运行语义迎合夹具。新来源只保留校验过的新句，避免已被替代正文残留。所有run已结束，未本地自动测试／构建、调用真实Provider或部署。P19／P20及完整真实行为继续后续。

P17历史验证提交：`6acfc73c69a9f4c5342783f5b580a53d6cf5b0e0`。服务[38770760106](https://github.com/bboytang/Mia/actions/runs/38770760106)194项全通过（18项P17）；真实BGE[38770760196](https://github.com/bboytang/Mia/actions/runs/38770760196)14提取场景及P12—P16回归通过；身份[38770760090](https://github.com/bboytang/Mia/actions/runs/38770760090)173／173＋23专项、实际TLS／WSS／提取隔离／JAR通过；manager[38770760124](https://github.com/bboytang/Mia/actions/runs/38770760124)150＋独立4通过，脱敏9项通过。真实Provider[38770771902](https://github.com/bboytang/Mia/actions/runs/38770771902)固定四样本原输出经Codex逐条复核通过。两轮真实失败（类别及旧事实来源混淆）均拒绝写入，提示已修正，开发共8次测试请求，全部原证据保留。见[结构提取及边界](verification/mia-persona-memory/extraction.md)、[精确结果和hash](verification/mia-persona-memory/extraction-ci-results.json)。所有run结束，无部署或本地自动化；该轮为固定样本验证，非独立留出或完整B03／八项验收。

P16历史验证提交：`dee34f5435bcfbe06b44be54b32c2b5321533319`，服务[38759159810](https://github.com/bboytang/Mia/actions/runs/38759159810)176项（19项新任务方法）、真实BGE[38759159851](https://github.com/bboytang/Mia/actions/runs/38759159851)的P12—P14回归及P15／P16九场景通过，六条完成路径各一个pending→empty任务；11次合成SDK请求、7次工具派发。身份[38759159526](https://github.com/bboytang/Mia/actions/runs/38759159526)173／173、23专项／实际TLS及Worker模型恢复／隔离、类范围和JAR通过；manager[38759159388](https://github.com/bboytang/Mia/actions/runs/38759159388)150／150＋独立4／4与字节对照通过，四workflow均success。原报告／hash／首轮RECORD夹具失败及中间通过保存点见[任务CI](verification/mia-persona-memory/jobs-ci-results.json)和[jobs.md](verification/mia-persona-memory/jobs.md)。所有run已结束，无在途操作；无本地自动测试／构建、真实聊天调用或部署，P17／P18及完整B03、全服务负载／真机仍待后续。

Java预期修复历史验证：用户追问脱敏失败原因和修复后，`74794e02c786f6f01389bdbc3d96b30911af4c5c`仅修正固定上游测试后缀预期`3123`→`e123`及两CI补丁接入，不改运行代码。新[身份38755588258](https://github.com/bboytang/Mia/actions/runs/38755588258)173／173、脱敏9／9、23专项／TLS、类范围和JAR通过；[manager38755588374](https://github.com/bboytang/Mia/actions/runs/38755588374)150／150＋独立4／4与字节对照通过；[服务38755588299](https://github.com/bboytang/Mia/actions/runs/38755588299)157／157通过，三workflow均success。见[原因及修复](verification/mia-persona-memory/manager-ci.md)、[精确结果](verification/mia-persona-memory/redaction-ci-results.json)。历史失败原报告不改；此前“唯一既有失败”对旧run仍成立，对当前修正后的Java回归已解除。该历史轮次无本地自动测试／构建、部署或在途run，后续P16结果见上。

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

恢复顺序：核对分支／远程SHA／工作树与在途run，阅读continuity.md及continuity-ci-results.json（若尚未生成，见工作记录）。最新运行源码6b57337及人格提示e48f222，四项受控验证全部结束且成功；真实对话仍泛夸，详见逐项审计。P19事件与P20趋势沿用唯一事实库／回复链／Worker，schema-v3保留旧迁移，生产容量限制不改。用户已接管实际跨日测试，不再自动续采；若用户自测需要原入口，首轮38785441525对应2026-10-15，可用mia-memory-continuity.yml的mode=daily、previous_run=38785441525衔接，之后每次引用上个成功daily run。workflow核验旧run与DB hash，同日不得重复采集。首日可移植合成库gzip及原报告已归档；不得改时钟、改写原证据或宣称已有七日。自然风格检查须阅读实际原文：407e825 dialogue工作流虽绿，不足趋势回复仍太像后台报告，已后续修正。亲近陪伴承诺按用户最新决定允许，技术在线事实仍诚实。完整manager＋BGE＋Provider、独立真实语料／八项行为与真机另验，未部署。

P13新增schema-v2保留原SQL和账本，元数据变化推进epoch、删来源清派生线索；v1→v2失败回滚及真实a30旧代码读写已验。严格P10—P12旧迁移器不识别v2账本，P24完整回滚制品仍待做，不得删schema绕过。P17／P18已接入结构提取和保守协调；完整真实用户语料及自然语言语义验收仍待P22，fixture不能替代。

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
| P16 | 完成：机制及受控接线 | dee34f5的176服务、原安装九场景／六完成任务、173 Java／23身份与实际TLS／Worker恢复、JAR及基线全部通过；真实模型／负载及完整B03待后续，不部署 |
| P17 | 完成：机制、受控及固定真实样本 | 6acfc73的194服务、14受控场景、实际身份及四固定Provider样本通过，完整B03待P22 |
| P18 | 完成：限定机制及受控验证 | d15a1dc的205服务、三种协调＋真实BGE／跨连接、173身份／实际TLS／JAR及manager回归全通过；保守格式，任意语义待P22，见maintenance.md |
| P19 | 完成：机制及受控验证 | 事件实际完成后激活、恢复／幂等／撤销，真实语气逐条复核；见continuity.md |
| P20 | 完成：实现及受控验证；真实跨日用户自测 | 默认关闭／授权版本／观察与管理／派生聚合已实现；仅有2026-10-15真实第一日；用户接管跨日验收，未记通过 |
| P21 | 完成：必要实现与GitHub验证 | 原管理页与兼容通过；87d2427的38821633956为102单测／6UI／两构建成功，真机另验 |
| P22 | 进行中，完整八项未验收 | 路遥对齐后来源与主体修正；三后续复验54请求仍有语义失败，明确更正三组流程／有限语义及在途删除25请求通过；实际B04元数据不足／辅助受阻，完整矩阵待补；跨日用户自测 |
| P23—P24 | 待推进 | 冻结资源／公平性及可重复升级／回滚、相关回归尚未实施 |
| P25—P26 | 未开始 | 真机及发布包待实施 |
| P27—P28 | 未开始 | 未发布，不能凭计划执行生产变更 |

当前补充：P10扩展schema及P13二版迁移、旧事实代码基础兼容已验证并归档。真向量与关联／四维模块通过不代表主回复链、Worker、事件、趋势或完整生命周期完成，整体真实行为按后续步骤验证。

## 八项能力状态

此表只记录本次 V1.2 目标，Mia 已有基础能力不因此判作不存在。

| 能力 | 代码 | 机制验证 | 真实行为 | 真机相关项 |
| --- | --- | --- | --- | --- |
| B01 人格对话引擎 | 进行中：P11基础通过 | 113服务及实际安装Scope通过 | 已多组真实身份／陪伴／更正对话，部分空记忆茶问题仍答自身喜好；完整人格／成长语义未验 | 未执行 |
| B02 长期记忆 RAG | P12真向量／P13混合及原回复链接线已实现，完整质量未验收 | 664237f实际BGE／SQLite、132服务及身份专项通过，Java有1既有失败 | 实际原提取／BGE／Provider跨PID更正召回及删除通过；独立完整质量待验 | 未执行 |
| B03 异步记忆提取 | P16—P18限定模块通过 | 205服务、14提取＋三种协调受控场景及持久Worker恢复／隔离通过 | 实际来源预检、明确更正、3次真实有效提案在途删除／取消／重启通过；完整故障／语料与负载待补 | 未执行 |
| B04 四维检索 | P13模块通过 | S／L／A／E实际贡献、受控分项排名、真实BGE遗漏恢复和底线拒绝通过 | 39实际请求／12事实／15查询已验，S／L／A有贡献，E全null、指定关联缺线索，实际B04未通过 | 未执行 |
| B05 持续人格事件 | P19实现 | 服务／实际BGE／manager受控路径通过 | 真实三active后续、明确更正／删除旧事件失效及PID重启已验，完整成长与自然语义待补 | 未执行 |
| B06 身份与记忆隔离 | 进行中：manager授权链 | 必要类范围／构建通过 | 23身份／实际TLS与Scope基础通过；完整未来消费者／实际App／八项行为未验收 | 未执行 |
| B07 长期情绪趋势 | P20实现 | 默认关闭／授权／聚合／管理受控路径通过 | 跨真实自然日验收用户接管，未标通过 | 未执行 |
| B08 上下文管理 | P14模块及P15／P16受控入口已接 | 176服务、真实BGE上下文／九协议场景及真实manager边界通过 | 已两轮各30真实工具场景，24／30最新结构通过；模型仍串行、实际容量未知，完整B08未验收 | 未执行 |

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

最新接续补充：当前精确源码、在途handle与第一项动作见上方“下一步”。38851330956已结束，原文保留behavior-third-*；B08工具真实38852561891已failure，复验38854020949已failure／96请求，见上方下一步；两轮三十原输出与失败均归档，不能把语法绿称行为通过。2026-10-16再次读取路遥main的config.py／guardrails.py，并通过GitHub API核对HEAD仍e23c3aa，与逐文件复核清单一致。没有新日采或部署。
