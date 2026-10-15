# P15：唯一回复入口与工具续答

状态：实现及CI入口已准备，待精确提交的GitHub结果。未部署；真实Provider、Token校准、声学／真机和完整B08仍未验收。

## 本轮只读配置核实

2026-10-15沿既有严格主机校验SSH，先核实容器名称，再只读SQL投影已选LLM的四个非敏感字段。结果唯一：`ChatGLMLLM`、`glm-4-flash`、`max_tokens=""`、`context_window=NULL`。没有选择API Key、用户ID、提示或聊天数据，没有改数据库／服务。首次查询因shell引号错误未执行，修正后的只读查询成功。

固定上游OpenAI兼容Provider会把空输出配置转换为None，因此现网不满足D05的已配置输出预留。当前[官方GLM-4文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-4)主要说明带日期版本，尚不能把旧别名按名称映射到可靠容量。保持`context_limits_unverified`，不借CI夹具16384／1024推定生产参数；输出上限选择已询问用户，未收到选择前不新增默认值。未调用真实聊天Provider或修改现网。

## 接入约定

安装器仍以固定v0.9.7原文hash检验并生成可重现补丁，拒绝重复安装／覆盖生产。新增`reply.py`随安装包复制。原文字listen/detect和ASR识别文本共同到`startToChat`／`ConnectionHandler.chat`；可信Scope的intent_llm回复路径改经同一入口，复用原主Provider与工具处理器，不创建平行回复Client。原唤醒／退出控制保留。

预算仅来自服务端`MIA_CONTEXT_PROFILE_FILE`指向的审查制品，必须含`provider_module`、`base_url`、`model`、`context_window`和`capacity_source`。前3项须与当前实际Provider完全匹配；输出始终读取其现有`max_tokens`。缺字段／文件、端点或模型变化、None输出均明确限制，忽略客户端容量字段；不提供可误用的生产猜测profile。`MIA_EMBEDDING_DIR`为已核实离线资产目录，进程共享单encoder／每事实库单index；不在线下载、不用FTS回填。

从实际非temporary DTO读取用户／助手／工具，不调用会补虚构interrupted结果的Dialogue转换。显示历史保持既有DTO。首次不能证明旧历史快照时不携入模型；后续同快照保留有界完整旧轮次。样式单独捕获为数据，旧memory槽及固定核心不混入样式。工具续答只追加DTO中新增完整链、同轮工具定义重新预算，不改已有参数／结果，不限制合法多次模型调用；空字符串工具结果可合法记录，缺结果仍拒绝。

每次模型开始／流式delta交付前／流末及每次chat工具派发复查Scope、服务端预算与三项快照；对话替换或取消关闭原stream。上下文变化后重新检索，只带原始当前问题与当前固定人格／样式，不复用旧history、事实、特点或工具结果，且清除本轮工具定义，拒绝工具重放。变化发生在输出流中则停止旧流并明确要求重新发起，不能撤回已经播放的内容。原权限／逐工具执行器继续决定权限，新增上下文声明检查只是额外约束；独立直接控制仍沿既有授权执行器。

配置或工具链限制发送`mia_context`结构状态及经Persona检查的短文字／TTS，结束原通道；撤权仅走原授权提示、不继续私有输出。embedding／DB不可用时保持固定核心、当前问题及明确unavailable状态，不声称正常RAG；无法证明快照时清除旧历史。

## 验证入口与待验边界

- `server/tests/test_companion_reply.py`：预算绑定与客户端忽略、10步并行工具链、删除无重放、缺失／修改链、历史版本变化、源DTO不变、撤权先于DB、流式停止／关闭、逐工具复查、DB／资产故障及样式边界。单位向量、策略和Provider均为fixture。
- `scripts/ci/verify_mia_reply.py`：实际安装后的整段ConnectionHandler类、listen／文本processor／startToChat／intent／TTS序列化代码原样编译运行；仅省略无关启动导入与物理硬件初始化。实际Dialogue、BGE、SQLite、原Provider和OpenAI SDK，经本地WebSocket文字协议及合成SSE响应验证普通／多步并行工具／direct_answer／ASR识别文本／删除／缺配置／撤权。2CPU／2GiB、network-none，外部聊天请求0；策略与工具结果合成，不冒充真实manager／聊天／声学。
- 实际manager HTTPS/WSS身份job补reply.prepare本人事实／外人隔离、删除后安全重建／禁止工具、撤权先于文件／DB与工具派发；此job向量／容量profile仍为fixture。

上述自动测试及构建仅GitHub执行。本轮未执行本地软件测试。结果待run补录，不据实现存在标P15通过。P16完成事件／持久任务、P17提取索引维护、P19事件、P20趋势仍未实现；完整真实Provider语义、Token对照及B08随P22验收，不由受控接线替代。
