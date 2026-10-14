# P06 真实 embedding 候选实验

状态：首轮四个候选均未达到全部门槛，尚未确认选型。首轮实际结果见 [v1 报告](embedding-results-v1.json)，run `38585421342`。改正一般性检索与测量问题后，用新的 v2 留出样本验证；P04 的质量门槛保持。

v2 仍无合格候选，原报告保留。v3 修正 exporter 包装及参考生成时的 eval 状态，避免参考向量带 dropout；新增独立语料及留出。用户确认同主题缺属性允许相关召回、回答必须明确未知，故 v3 把相关不可回答与真正无关分别报告，实际回答尚未执行。

v3 置信度实验在校准集比较原始余弦底线和原查询第一候选相对第二候选的分差；最低原始余弦 0.25，分差不能使高情绪无关候选跳过语义检查。校准并列选择中间参数组合，不使用留出反馈挑参数。数值质量及资源门槛保持，报告继续以 eligible 判定，不预先认可该探索为生产实现。

v3 [38592420655](https://github.com/bboytang/Mia/actions/runs/38592420655) 四候选仍不合格，见 [v3 报告](embedding-results-v3.json)。base FP32 Recall／Top1 0.95833、空召回 1.0，但必测峰值 571.42 MiB；small INT8 Recall 1.0、Top1 0.95833、空召回 0.9375；small FP32 空召回 0.875。修正 dropout 后 FP32 参考最低余弦约 1.0，base INT8 仍为 0.37205，属于实际量化精度问题。

v4 不改变检索逻辑或质量门槛，新增独立 J／K 合成语料（仍为 20 记忆／112 查询，同 v3 划分），验证关闭 ONNX 内存 arena／pattern／预打包的资源影响；参考原始向量继续检查。INT8 改逐通道及 reduce-range：这是针对大精度损失的通用候选修正，依据 [ONNX Runtime 官方量化说明](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html) 的 U8S8 饱和与逐通道指引，是否解决须实测。预打包配置依据 [固定 ORT 1.23.2 源码](https://github.com/microsoft/onnxruntime/blob/v1.23.2/include/onnxruntime/core/session/onnxruntime_session_options_config_keys.h)。报告补 CPU 指令集／型号，不能假定 runner 与服务器指令集相同。

v4 [38593905607](https://github.com/bboytang/Mia/actions/runs/38593905607) 四候选仍不合格，见 [v4 报告](embedding-results-v4.json)。base INT8 正向／Top1 1.0、无关空召回 0.9375、参考最低余弦 0.93648；量化大幅改善但仍低于 0.95。base FP32 RSS 564.22 MiB 且空召回 0.875。small 两变体正向／Top1 0.95833、空召回 0.875；INT8 参考最低 0.99411。没有选型，后续应解决校准选择稳定性／推理加载及实际查询内存，不能靠继续增大容易样本或改旧失败得出通过。

v5 保留 v4 事实及校准输入，新增独立 48 正向／16 无关／8 相关不可回答留出查询，不重用 v4 留出选参数。校准并列解增加最小有符号决策间隔：在同等质量下，选择离正负校准样本拒绝边界最远的解，代替任意中间网格点。只使用校准结果计算，留出不参与。

在模型导出阶段使用固定 ORT 1.23.2 将 ONNX 保存为 ORT（仅 BASIC 图优化），比较模型载入内存；导出开销仍不计为推理结果。各源模型与派生模型有 SHA，真实原始向量一致性继续作为硬门槛。不以“格式更轻”声称内存已经合格，必须读取新的隔离报告。依据同版本 [保存格式配置](https://github.com/microsoft/onnxruntime/blob/v1.23.2/include/onnxruntime/core/session/onnxruntime_session_options_config_keys.h)。

v5 [38595630806](https://github.com/bboytang/Mia/actions/runs/38595630806) 仍无 eligible，见 [v5 报告](embedding-results-v5.json)。base 两变体正向／Top1 0.97917、无关空召回 1.0；FP32 ORT 必测 RSS 990.82 MiB，INT8 444.61 MiB 但最低参考余弦 0.93648。small 空召回仍 0.875。ORT 格式在本实验增大峰值，不能当已验证的省内存方案。

下一项仅比较通用量化表示候选 U8U8，使用同一已冻结 v5 数据／检索逻辑／校准规则；不调整质量门槛或使用留出反馈调检索。U8U8 为官方针对 U8S8 大精度损失建议的替代，保留新的 `model-uint8.onnx` 名称和元数据，不覆盖旧实验结果。运行使用 ONNX 而非未达预期的 ORT 表示；若仍失败，继续保持未选型。

## 候选及官方依据

- BAAI/bge-small-zh-v1.5，revision `7999e1d3359715c523056ef9478215996d62a620`，512 维。
- BAAI/bge-base-zh-v1.5，revision `f03589ceff5aac7111bd60cfc7d497ca17ecac65`，768 维。

模型发布者的 [small 模型说明](https://huggingface.co/BAAI/bge-small-zh-v1.5)及 [base 模型说明](https://huggingface.co/BAAI/bge-base-zh-v1.5)标明中文语义向量、MIT 许可、CLS 池化／归一化方式及查询前缀。两者只作为待测候选，不依据其榜单成绩声明 Mia 效果。动态 INT8 概念参考 [Hugging Face 官方量化说明](https://huggingface.co/docs/optimum-onnx/onnxruntime/usage_guides/quantization)，本实验直接使用 ONNX Runtime 量化，不引入 Optimum 运行依赖。

## 执行与报告

`mia-memory-embedding.yml` 在 GitHub 固定模型版本导出 ONNX FP32／INT8；导出运行在普通 runner，不计为目标资源性能。推理容器单独限制 2 CPU／2 GiB，禁网络，挂载的仓库和模型只读，不访问生产服务／模型密钥。

脚本：`scripts/ci/prepare_mia_embedding.py` 和 `scripts/ci/benchmark_mia_embedding.py`。模型 export 不执行 remote code，PyTorch 读取仅 weights。容器运行依赖固定版本 numpy／onnxruntime／tokenizers，不加载 PyTorch 或聊天 Provider。

报告记录固定模型／代码／数据集 SHA、导出模型校验值、推理镜像 ID／基础 image digest、包与 Python 版本、真实向量、校准／留出结果、四维分项、关联扩展、分项消融、全链路 p50／p95、SQLite 1k／10k／50k 与其他 Scope 同量压力、冷载入和 peak RSS。

阈值与语义最低分只由校准集选择，不使用留出查询。原权重 58／28／8／6 保留；实验语义分项使用真实归一化向量余弦值，相关性门槛单独校准。纯向量和四维结果分别记录；本脚本不提供生产认证、任务、事件或趋势实现。

首轮暴露的问题：扩展词来自候选自身，若再进入 L 词法分项会产生自证匹配；仅按扩展语义设置相关性底线会把当前居住信息等召回给不相同的属性问题。v2 保留原查询与扩展查询两个有界向量候选，L 只使用原用户输入，拒绝底线也使用原输入的真实语义值；不把扩展词当证据。两次 embedding 都计入延迟。

补充 PyTorch 原始权重与 ONNX 的八个通用输入向量余弦检查，FP32 最低 0.999、INT8 最低 0.95；INT8 仅量化常量权重 MatMul，避免无必要的注意力计算量化。报告区分必测 10k 范围峰值与可选 50k 容量探索峰值，不能让可选探索改变已冻结必测门槛。

**workflow success 只说明实验执行成功。是否满足初选门槛以报告 eligible 和具体指标为准；候选全不合格时 P06 仍未完成，不能降门槛或改用 FTS。** 本次小样本、重复向量容量实验与消融结果不代替最终真实聊天、长期观察及规模语义验收。

执行后将 run／报告、失败或未执行原因及选择依据写入工作记录和交接。报告制品临时 artifact 不是唯一持久证据，必要脱敏结果纳入此目录。模型权重不提交仓库，后续制品从固定来源与 exporter 重建。
