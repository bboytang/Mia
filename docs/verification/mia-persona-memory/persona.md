# P11：分层人格与输出前检查

状态：**基础机制与限定三个真实模型样本通过，完整人格能力仍待联动验收**。被测代码 `232de0d2fc5250a42f9802a2bbd470e9866d5c18`，未部署。

## 当前证据

| 范围 | 精确run／持久报告 | 结论 |
| --- | --- | --- |
| 服务机制 | [38662376416](https://github.com/bboytang/Mia/actions/runs/38662376416)／[服务报告](persona-service-results.json) | 全部113测试通过，含8项专门人格用例及数据库故障核心保留 |
| 真实身份／实际安装包 | [38662376430](https://github.com/bboytang/Mia/actions/runs/38662376430)／[身份报告](persona-identity-results.json) | 23身份／实际TLS、安装DTO／Dialogue／队列、JAR及类范围通过；完整Java173中172通过／1既有脱敏失败 |
| 固定原Provider流式＋人格队列 | [38662470670](https://github.com/bboytang/Mia/actions/runs/38662470670)／[原始响应与逐条语义检查](persona-provider-results.json) | 三个真实请求及语义检查通过：Mia与诚实AI身份、未知用户出生地、不保证永久存在／限定服务期间帮助 |

语义检查由本轮Codex逐条阅读原文完成，**没有独立人工签字或正式八项验收**。此前进度中的“人工复核”指手工阅读环节，应以此明确身份为准。响应中的额外段内emoji仍需P21完整文本／表情／TTS一致性验证，不能以句首标记通过代替全表达验收。

## 实现与边界

- PersonaAgent拥有固定核心；角色JSON编码为风格数据，复用原PromptManager更新，重复组装幂等。明确Mia名字、诚实AI身份、主体／属性证据与未知回答；旧memory／personality材料仍由同一已授权Scope取得，只有一个memory slot。
- 核心在TTS启动前主动加载，不依赖DB成功。None角色及未闭合memory标签不能消除核心或制造额外插槽；八类emoji语义不再依赖MemoryStore成功。
- 已知严重“绕过规则＋公开私有配置”输入在现有回复链提前结束，不调用第二模型。教育性讨论不自动拦截；检测信号不能作为权限证明，真实身份／工具Scope守卫保持。
- 同一原TTS queue前增加有界句级检查，普通文本／流式direct_answer／工具直接文本均使用原队列。完整句未到前不交给消费者；只缓存当前sentence，待检查残片上限1024字符（按1024字符块处理，瞬时拼接不超过2048），过长不分句文本替换并停止该段，旧sentence丢弃。
- 已知不实意识／永久承诺／排他依赖／公开密钥表述替换后关闭当前模型流并跳过其工具派发／递归续答，保留LAST；下一轮恢复。字幕及assistant历史另检查，不改用户文字或完整工具结构，不禁止诚实AI身份。输入／输出检查只是有界第一道机制，不是通用语义证明。
- 不新增Provider、账户、TTS、回复模型或音频服务；保留原Queue消费者／DTO／文件音频及官方tts/base.py修复。未宣称检查预录音频内容或实现低语／叹息等声学能力。

实际安装Scope测试只使用合成TTS sink；固定connection／dialogue补丁检查preimage和Python语法。完整Connection、direct_answer与多工具续答的动态整链、上下文／输出历史完全一致性继续在P14／P15验收，不以钩子存在冒充全部路径已验。

## 真实测试范围

独立workflow `mia-memory-persona.yml` 仅manual dispatch调用模型，push／PR只检查语法。复用固定上游原OpenAI兼容Provider和SDK2.8.1流式方法，经实际安装persona／DTO／句级队列；只替代启动logger及非权威key格式提示。专用测试Secret不读取／复制到仓库。

每轮最多3请求、各128输出Token、HTTP30秒／总120秒、零重试、不接受重定向。角色与单条现居地为合成fixture，三个独立Session不是跨会话记忆／事件持续性证明；未运行manager→Connection／ASR／声学整链。原始语义失败不能仅因替换成fallback而记通过。

## 保留的失败及修复

| 版本／run | 实际问题与处置 |
| --- | --- |
| 254451b／38661189334 | 集成夹具缺原连接config，Python／TLS两例失败；只补夹具，未降低产品检查。[失败报告](persona-identity-failed-254451b.json) |
| 1e0b75c／38661688808 | 首个真实请求缺Mia名字、emoji句尾，立即停止，后两例未执行；补中文明确核心，保留名字判据并增加既有句首格式检查。[失败报告](persona-provider-failed-v1.json) |
| 66cf0e5／38662021333 | 自动success但语义检查发现出生地答成AI自身且编造2023年，不予验收；修主体／属性边界及规则假阳性，保留真实失败反例回归，仍允许诚实AI披露。[自动结果及明确拒绝](persona-provider-rejected-v2.json) |
| 232de0d／38662470670 | 原始回答及检查后文本均通过三个基础场景的逐条语义检查，未放宽原场景含义；不代表正式B01或八项通过 |

## 接续

下一步P12真正向量的编码／版本／SQLite召回，依据P06固定规格；FTS旧实现仍不算完整RAG，关联与四维评分待P13。人格整体还需证据特点／有效事件、统一ContextBundle、合法工具续答及真实多会话联动，分别接P14／P15／P19／P22。

引述／故事／假设中的主体归属、长篇文本的输出检查、额外emoji一致性、Provider容量／Token预算、并发／首句增量及真机均保持待验。固定核心中的第一人称约束不能取代结构化来源与说话者判断，也不能把引述当用户事实。不能在这些条件未满足时发布或标B01完成。所有自动测试／构建在GitHub，未在本地或生产运行。
