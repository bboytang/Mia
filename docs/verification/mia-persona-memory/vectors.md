# P12：真正向量编码与SQLite召回

状态：首轮实现待GitHub验证；未部署，主回复链仍待P13完整混合检索后接入，不能称完整RAG通过。

## 固定编码器

复用P06确定的BGE base中文、HF revision f03589ceff5aac7111bd60cfc7d497ca17ecac65、768维、CLS归一化、官方查询前缀及U8U8模型。model-uint8.onnx硬校验SHA256 dc36bd336224eaa24f2c032d9b4864d4121b72c24bbcd371813e5348ceb02e9e；固定metadata和tokenizer manifest校验后才加载原生运行时。运行进程不联网下载、不用聊天API冒充embedding。单个tokenizer／ORT session复用，2／1线程、关闭arena／memory pattern／prepacking，512 token模型窗口，超过窗口按所选tokenizer截断而不修改原事实内容。

依赖独立requirements-vector.txt，未改既有Provider／账户／声学服务。缺资产、模型不兼容或推理错误均明确unavailable，固定Persona不因此消失。部署时只可使用固定producer recipe的受控资产目录，不能由客户端提供模型文件。

## 事实、索引与Scope

- 沿用P10同一SQLite：事实只在memories，向量是模型／variant SHA／revision／维度／内容版本标记的little-endian float32派生Blob。没有第二份事实正文。
- index／candidate／rebuild都接AuthenticatedScope和既有授权服务。按owner、固定mia Persona、confirmed和active先限制数据；跨owner ID与不存在ID统一拒绝，pending不编码／参与。
- 编码在DB事务之外；执行／提交／返回前复查Scope，提交事务核对事实内容版本与Scope内容epoch。已观察的撤权立即停止；提交后发现撤权清理自身派生向量，原事实不变。没有跨manager／SQLite的分布式事务，不宣称这种原子性。
- 编辑／删除由P10触发器使向量失效；重建每批最多32。缺任何有效索引、损坏或模型版本不符都报不可用，不偷偷查FTS、填最近事实或将未就绪说成空召回。
- 候选按Scope精确余弦计算，256行有界块、TopK堆，不全库先取再过滤；不改语音进程全局BLAS参数。最多2个在途编码，取消／超时不提前归还仍运行的推理槽，也不能将其结果继续提交。

P12仅语义候选，不冒充P13关联＋四维评分；P16／P23继续服务级前台优先、公平性、持久索引任务及全服务资源验收。新权限不因本阶段单测提前开放。

## 首轮验证

所有自动测试在GitHub：

1. 服务机制用明确的合成单位向量，验证SQLite、Scope、版本、损坏、缺索引、撤权、编辑／删除及取消槽，不能作中文语义效果证据。
2. 真实manager脚本调用实际安装的SemanticMemoryIndex，用合成向量只测认证边界、跨owner拒绝、有效候选及撤权先于DB访问。BGE在单独隔离job测。
3. `mia-memory-vectors.yml`仅构建已选base模型，复用原export脚本，写tokenizer manifest；实际安装companion后，在无网络、2CPU／2GiB、无Torch推理容器调用真正encoder和SQLite。校对8参考向量、4中文跨措辞Top1、无关空召回、FTS表临时不存在仍召回、真实编辑／删除失效。
4. 1千／1万容量fixture复制一个**真实种子向量**，只证明实际数据库扫描成本，不声称1万事实都经真实编码或中文准确率。门槛维持SQLite1万p95≤150ms、编码＋查询p95≤400ms、峰值RSS≤512MiB；长输入另外诊断，不能伪称其单样本为p95。

P06独立完整中文留出集、关联与四信号作用、真实回答、实际manager＋BGE＋主回复整链、TTFT／并发、缓存和全部八项能力仍须P13及后续验收。旧模型／数据集／权重门槛不因失败而修改。首轮未实跑前不标通过。
