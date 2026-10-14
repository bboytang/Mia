# P06 真实 embedding 候选实验

状态：实验入口已编写，尚未运行／确认模型选型。使用 [P04 冻结指标](acceptance.md)和固定中文样本。

## 候选及官方依据

- BAAI/bge-small-zh-v1.5，revision `7999e1d3359715c523056ef9478215996d62a620`，512 维。
- BAAI/bge-base-zh-v1.5，revision `f03589ceff5aac7111bd60cfc7d497ca17ecac65`，768 维。

模型发布者的 [small 模型说明](https://huggingface.co/BAAI/bge-small-zh-v1.5)及 [base 模型说明](https://huggingface.co/BAAI/bge-base-zh-v1.5)标明中文语义向量、MIT 许可、CLS 池化／归一化方式及查询前缀。两者只作为待测候选，不依据其榜单成绩声明 Mia 效果。动态 INT8 概念参考 [Hugging Face 官方量化说明](https://huggingface.co/docs/optimum-onnx/onnxruntime/usage_guides/quantization)，本实验直接使用 ONNX Runtime 量化，不引入 Optimum 运行依赖。

## 执行与报告

`mia-memory-embedding.yml` 在 GitHub 固定模型版本导出 ONNX FP32／INT8；导出运行在普通 runner，不计为目标资源性能。推理容器单独限制 2 CPU／2 GiB，禁网络，挂载的仓库和模型只读，不访问生产服务／模型密钥。

脚本：`scripts/ci/prepare_mia_embedding.py` 和 `scripts/ci/benchmark_mia_embedding.py`。模型 export 不执行 remote code，PyTorch 读取仅 weights。容器运行依赖固定版本 numpy／onnxruntime／tokenizers，不加载 PyTorch 或聊天 Provider。

报告记录固定模型／代码／数据集 SHA、导出模型校验值、推理镜像 ID／基础 image digest、包与 Python 版本、真实向量、校准／留出结果、四维分项、关联扩展、分项消融、全链路 p50／p95、SQLite 1k／10k／50k 与其他 Scope 同量压力、冷载入和 peak RSS。

阈值与语义最低分只由校准集选择，不使用留出查询。原权重 58／28／8／6 保留；实验语义分项使用真实归一化向量余弦值，相关性门槛单独校准。纯向量和四维结果分别记录；本脚本不提供生产认证、任务、事件或趋势实现。

**workflow success 只说明实验执行成功。是否满足初选门槛以报告 eligible 和具体指标为准；候选全不合格时 P06 仍未完成，不能降门槛或改用 FTS。** 本次小样本、重复向量容量实验与消融结果不代替最终真实聊天、长期观察及规模语义验收。

执行后将 run／报告、失败或未执行原因及选择依据写入工作记录和交接。报告制品临时 artifact 不是唯一持久证据，必要脱敏结果纳入此目录。模型权重不提交仓库，后续制品从固定来源与 exporter 重建。
