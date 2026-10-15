# P14：统一上下文与预算

状态：P14模块、机制及实际BGE／安装包／Dialogue验证通过。未接主回复链，未部署，完整B08及八项行为未验收；实际Provider容量及输出仍须核实，P15才修改唯一回复入口。依据D05、P11固定核心和P13固定检索契约。

## 已检查的实际接口

固定上游87c6df77b0220ddbd8fc804f984f83f69f3225e5的Dialogue SHA256为a4f7af45edd5f1e60a119eb698daba56047fb6c57dfe5c4bfcadbf28234a6602，OpenAI兼容Provider为5dfec38041d28436362b4a1b0f5946d1bdff7bb9afb3501c6417037a6bd3b006。旧部署副本带补丁，已另读固定来源原文核对；临时目录不是恢复依赖。CI按原installer重建实际安装包和Dialogue。

Provider使用model_name及max_tokens，后者缺失／转换失败时为None，不能把测试128当生产默认。ContextLimits.from_provider只读取现有字段，不改变模型或输出额度；还须由已审查服务端配置传入容量及来源，缺失明确context_limits_unverified，不按模型名猜测。

2026-10-15读取[智谱GLM-4官方说明](https://docs.bigmodel.cn/cn/guide/models/text/glm-4)，未建立旧glm-4-flash别名与具体容量的可靠映射，未读生产配置／密钥或调用聊天API。P14可独立验证模块，P15实际接入前仍须核实真实容量及输出预留；CI容量profile是合成契约夹具，不是生产证据。

## ContextBundle与边界

ContextBuilder.build接可信Scope、Turn ID、当前输入、旧历史、可选当前轮工具链、角色样式、当前工具定义、场景及已核实预算。返回frozen ContextBundle：Scope、三项数据／人格快照、人格hash、预算，以及不可变JSON字符串的源材料、实际模型请求和诊断。request／diagnostics每次返回新对象，Provider归一化不会污染同轮复用；无新持久历史／表／缓存或模型Client。

唯一system消息为固定CORE＋固定边界说明；角色、事实、特点及场景是独立user消息的JSON数据，不拼成system权限。当前问题单独保留，工具调用仍为assistant(tool_calls)→tool(result)原结构。已知严重输入提前阻止，工具授权仍由manager及现有执行器执行，Prompt不作权限证明。

历史参数只含先前轮次，不含旧system提示或当前问题。上游DTO经原Dialogue转换后由接入层选择传入；本步不改显示历史或上游补取消结果的行为。P15须明确区分已有取消结果与真实结果，ContextBuilder自身不虚构缺失工具结果。

旧历史按完整用户轮次分组，当前轮最多连同19个旧轮次。先验证工具结构与ID配对，再保留连续旧轮次后缀；孤立／重复／未完成结果或system／developer历史角色明确报错。固定核心、当前问题、当前完整工具链及完整工具定义为必保留项，超预算直接限制，不截断参数／结果或删工具定义。

## 预算与裁剪

输入上限min(8192, context_window - configured_response_tokens)，输出预留保持现有Provider配置。计数为完整JSON请求的UTF-8字节，加512固定、每消息32、每工具256结构余量，包含函数定义、参数、结果、model及max_tokens。诊断明确conservative_estimate_not_tokenizer，不是精确Token或usage测量；真实Provider模板／tokenizer误差和请求联动仍须P15／P22核验。

先保证核心、当前输入及当前工具结构，再按角色样式、P13相关事实、必要近期历史、有效特点、场景装入。预算不足完整省略可选项并记录ID／轮次；长样式可省略，固定核心始终保留。正常空召回仍空；无FTS／最近事实回填。不为凑预算改写数据库内容。

检索与JSON组装在线程执行，授权用现有async服务。必需结构不可能容纳时在原生embedding前拒绝；中文和emoji按实际字节预算。显示历史和源字典保持不变。

## 快照与故障

复用P13真实retrieve及revision／content_epoch；同事务读取owner人格version和有效特点，特点证据须仍属同Scope且active／confirmed，并继续满足三个会话匹配三个不同来源指纹。复用MemoryStore原有判定为共享纯函数，写入规则不变，来源删减后不再合格的旧特点不会装入上下文。返回前复查授权及快照。continue_turn不重做embedding或回复，只复用同Turn材料追加完整工具链并重新预算；前后复查版本／权限，编辑、删除、暂停、特点重置等要求context_changed重建，撤权明确拒绝。

embedding／SQLite故障时保留固定核心和当前输入，memory_status明确unavailable，不计作完整RAG。无法取得DB快照时清除旧历史及派生材料，不允许复用未知版本的工具续答。损坏／缺索引不冒充正常空召回。事件及趋势待P19／P20，诊断为pending／默认关闭，不假装已完成。

## 验证范围

- 服务用明确合成单位向量验证数据层／副本、字节预算、20轮上限、10组并行工具续答、非法工具、必需溢出、可选裁剪、未知容量／输出、Scope／版本竞态、DB故障、有效特点及严重输入。
- 实际安装包＋真实BGE／SQLite／原Dialogue在2CPU／2GiB／network-none验证事实入上下文、显示历史不变、10组工具链及每组五次build、请求预算、删除重建、跨Persona和未知容量拒绝。工具结果及容量profile是夹具，聊天Provider调用为0。
- 实际manager→安装包验证本人事实／外人不入、删除后拒复用、撤权先于关闭DB访问；该处向量合成，不是manager＋BGE＋Provider整链。

所有自动测试／安装／构建仅GitHub。实际入口／续答接线、Provider容量／配置、真实Token对照、八项行为及真机待后续，不因模块通过提前发布。

## 2026-10-15：首次同提交验证通过范围

被测源码`5e91409bbc9da69b0c7085837e7014ce24e3bc04`已推送；[服务38732848387](https://github.com/bboytang/Mia/actions/runs/38732848387)145项全部通过，含13个新上下文测试方法及其10组并行工具场景，原记忆／人格／Scope／迁移回归通过。共享特点匹配规则抽取后，原写入判定未改变；新读路径验证来源删减、状态失效后不继续使用旧特点。

[真实BGE 38732848548](https://github.com/bboytang/Mia/actions/runs/38732848548)整体success，同job的P12／P13回归及新P14安装包测试通过。[context-results.json](context-results.json)保存原样报告及完整样例模型请求：10组工具链、50次build的p50 34.372ms／p95 34.959ms，峰值RSS283.887MiB；第0组完整模型输入保守估算6925、预算8192，19个旧轮次和当前问题／工具／真实召回事实都保留。源Dialogue未变、删除必须重建且新build不含旧事实、其他Persona拒绝、未知容量拒绝均通过。这里只是10个机制场景，天气结果和容量均为夹具，聊天Provider调用为0，不能计作真实B08回答验收。

同提交[身份38732848576](https://github.com/bboytang/Mia/actions/runs/38732848576)23专项／实际HTTPS-WSS及ContextBuilder本人事实、外人不入、删除后拒复用、撤权先于DB访问通过，类范围及JAR构建通过；完整173中172通过、1既有SensitiveDataUtilsTest.maskMiddle_keeps_four_at_each_end_for_long_strings失败，0error／skip。workflow整体failure。[manager基线38732848453](https://github.com/bboytang/Mia/actions/runs/38732848453)154中153通过、仅同一既有失败，不称全项目绿色。

[分项CI与范围](context-ci-results.json)、[原身份报告](context-identity-results.json)、[P12回归](context-vectors-regression-results.json)及[P13回归摘要／原文hash](context-regression-summary.json)已持久保存；P13完整候选原文无损gzip另存，可解压复核。P13正负控制及独立中文质量继续通过，权重、阈值、底线和留出未改。

全部run已completed，无在途操作。P14模块门槛通过；下一步P15先从已授权非敏感配置／可靠文档核实实际Provider模型、窗口及max_tokens。若max_tokens仍为None，保持明确限制并解决配置决策，不使用CI128替代；接线须复用本轮Bundle、检查作用域／版本，变化后不能盲目带旧inputs_json重包或重复执行有副作用工具。完整Provider语义、真实Token校准、事件／趋势、全服务资源和真机均仍待后续。
