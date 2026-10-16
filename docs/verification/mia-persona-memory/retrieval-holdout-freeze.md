# P22 独立检索v2单次隔离评估冻结

冻结时本地/远程基线：`e8bd4c92064bf88ad231b94f7be21b03d3c928dd`。实际dispatch被测SHA在工作记录和run中登记。
语料：`server/tests/fixtures/persona_memory_retrieval_p22_v2.json`，Git blob `4a64401fc047d1ba2a35aaca15d24c8df3476b2e`，与原0dfa6a0冻结对象相同；仅核对对象，未改语料。
指定型号：glm-5.3-flashx；授权范围仍为隔离CI比较，非生产采用。沿用原4096输出/16384短上下文、30秒HTTP、0 SDK重试、Worker两次总尝试及20请求/轮上限。

## 入选依据与边界

61eaa416的v1真实15项结构、四信号、活动扩展、无关为空及重要性实际值已观察；自然纠错、特点成长、工具和Scope有限三组证据已保存。额外原回答的交通方式/习惯泛化等局限继续保留，本冻结不把v1改写成零语义错误或P22完成。
本基线server/companion相对v1实测只改变Java测试fixture接纳shutdown入口；全部运行Python模块未变。以下固定blob用于核对，不能从元数据推断测试通过。

| 运行文件 | Git blob |
| --- | --- |
| `extraction.py` | `76939653cc530f749414e5092668bde7ecda341c` |
| `proposal.py` | `0607ec2cb7397ed6f56aa9449872682ee9c6e0ec` |
| `retrieval.py` | `619de18500f489e0ec6557537203d033d7ac0a9d` |
| `semantic.py` | `cadb6fd602e739c487e90dc6c278128cdb1d602d` |
| `context.py` | `3299c99fb7fd33c4fd95226e7a9c469152fd84ca` |
| `persona.py` | `bd5ff18c543f0122d9abde81f579ee539471df2f` |
| `jobs.py` | `7712f7a254d5385ebd729d79d3845ce9ad53c6b5` |
| `memory.py` | `8f4252ddaee44f2b454437d84a5660af309c1f23` |
| `authorization.py` | `68987cb556de640eea1925ce990b790009d7248f` |
| `xiaozhi_adapter.py` | `966392d46f8c1b1fa0dc072970fe632a2bcdb267` |
| `reply.py` | `1a5b5beff0b7d5cbe6c02e4f649192892c1212ed` |
| `embedding.py` | `2a22ad236eb78e3f5a87b289e28f9c5db842ffde` |

## 执行规则

suite=retrieval_holdout仅执行一次，使用真实manager/Provider/BGE/SQLite和三个隔离合成用户。结果、失败、未执行及所有原回答分别复核；成功job不代替语义/硬门槛核对。
不使用本次留出结果调参或反复运行相同留出取绿；若后续代码修改确实需新独立验收，另行冻结新留出版本并保留本次失败，不能改写v2。与shutdown专用v2无关。
关闭验证可独立并行；P22全部前置尚未满足，P23/P24不提前记完成，真实七自然日继续由用户自测。
