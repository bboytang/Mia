# P22 新独立检索 v3：执行前冻结

冻结于首次 v3 请求前。运行候选为 `01f387f690bbdb4dbaa1ef7d64c7c694b7781a0c`；本次只新增测试数据、原 harness 的 v3 路由和 Java suite 白名单，不修改运行 Python 模块、检索 driver、权重或门槛。

语料 `server/tests/fixtures/persona_memory_retrieval_p22_v3.json`：Git blob `b73834ddb71a389d4183b5d828e39e8b5044c776`，规范 LF SHA256 `eb18a8c61e017fde02eb23f1fa5c7c921659a5ad99a62b61d2995d83673719d9`。Windows 工作树 CRLF 不作为不同数据，执行时核对 Git blob 内容。v1 只作校准；v2/38977613787 原失败及未执行问题保留，不重跑。

三个全新隔离合成用户分别谈编织、篆刻、烘焙，各四条实际发言、五个新问题。原 driver 验证四维信号、活动扩展、目标和无关重要事实排除；原回答另逐条复核来源归属、是否补造用户事实或已发生互动。语料只提供用户输入及预期来源，不提供模型回答、importance 数值、数据库记录或伪造版本。

| 固定运行文件 | Git blob |
| --- | --- |
| extraction.py | `39348e36f1402e8b0dd861d3f73e6a4784670ce5` |
| proposal.py | `5ee648fc4f8c1209238c778fe506770197377c2d` |
| context.py | `3299c99fb7fd33c4fd95226e7a9c469152fd84ca` |
| retrieval.py | `619de18500f489e0ec6557537203d033d7ac0a9d` |
| memory.py | `8f4252ddaee44f2b454437d84a5660af309c1f23` |
| jobs.py | `7712f7a254d5385ebd729d79d3845ce9ad53c6b5` |
| scripts/ci/mia_behavior_retrieval.py | `62da472a307421c8e83b511e67d65211344b2b2f` |

选择依据：4b81c927 的一般成长资格及 schema 长度改动来自既有 v1 成长证据，校准检索 38980235375 三组 39 请求、15 结构检查已通过；新 01f387f6 仅补既有持久资格反馈。v2 的原回答语义失败仍未被证明消除，本次冻结不作已解决结论，不根据 v2 具体答案添加措辞限制。自然未知、亲近、感受和陪伴承诺仍允许。

执行入口 `suite=retrieval_holdout_v3`，仅单次隔离 `glm-5.3-flashx` 比较。沿用 4096 输出/16384 上下文、30 秒 HTTP、0 SDK 重试、Worker 两次总尝试和每轮20请求上限；实际 Java/Provider/BGE/SQLite，未改生产配置或密钥。先核对成长修复 38982225986 的终态，再执行此新版本。实际 run/headSha/原报告另记；任何失败、未执行、原文和哈希均保存，不能把结构 success 当语义通过，也不能对该留出调参再跑取绿。P22/P23/P24 尚未完成。
