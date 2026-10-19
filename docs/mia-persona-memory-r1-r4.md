# P23 第一批定向修正 R1–R4

日期：2026-10-19。批准基线：`b7a4b0fc9f04d5b1232d41845ea1232a1e91c11d`；固定分支 `feature/mia-persona-memory-v1.2`。

## 范围与基线

用户在独立只读审计后批准本批，覆盖旧交接的“继续第三十六步”。审计报告已在对话交付，本文件保存本批依据与验证；不把尚未编码的建议当完成。远端和本地基线一致，无 tracked 改动，保留 `.private/`、`tools/`。ca03844六个既有CI均success，无重复派发。

审计已证实：R1混用case/SDK计时原点，总首句增量不变但阶段归因错；R2普通提取把数据库JSON字符串当模型数组示例；R3继承默认函数方法不能证明原生调用能力，固定openai实际请求未启用函数选择/strict schema；R4原生提案错误与字段校验错误的反馈路径不统一。模型模仿输入的因果、重复授权对实际延迟的占比仍属高度怀疑，不能写成已量化。

本批不执行36任务/正式72回复，不改模型/供应商/密钥、事实或任务schema、尝试次数计算、两次尝试/120秒期限；不部署、不进P24。只在最终代码SHA推送一次以取得必要同SHA回归，避免逐项提交重复CI；本地每项单独记录/提交。真实Provider诊断如无必要不调用。

## R1：计时与旧证据归因

已实现v3：所有 `*_ms` 时点统一相对case开始，保存case单调时钟起点及0ms，SDK起点、首次内容和TTS文本就绪分别记录。v2解析明确把SDK相对首内容转换到case原点，未知版本/逆序拒绝。

新增非零SDK偏移数学反例和实际SDK观察器假时钟测试，27项CI机制通过。对原第三十三步72回复/36配对另生成 `verification/mia-persona-memory/performance-auth-once-stage-corrected-v3.json`；原始gzip、旧归因和验收结论不覆盖。六组总p95逐项保持，10k查询0仍912.84ms/failure；最差配对935.49ms正确分配322.90/437.92/174.67ms。SDK区间包括远端/传输/消费/观察器，不称纯网络。源码diff由本项独立提交定位；GitHub最终SHA回归待批次代码完成。

## 后续顺序

R2统一最小只读模型输入投影 → R3显式Provider能力契约/实际参数验证 → R4错误分类、反馈及原失败输出重放 → 最终SHA必要回归/记录交接后停止。

R5前台持续活动导致后台饥饿、排队占用尝试/期限；R6重复授权/完整capture/配置读取；R7安全句边界与TTS首段边界。均保留为下一批待审批，不在本批顺手修改。

## R2：所有提取分支的只读输入投影

`project_context`对普通JSON/原生函数、自然纠错、成长和重要性分支统一只投影id/category/content及来源session_id/fingerprint/excerpt；删除无需模型消费的数据库序列化元数据/版本和额外字段，不把存储JSON字符串作为输出示例。服务器原始context与版本仍由tool_definition/validate_output/提交完整使用，模型输入与证据字典无共享可变对象；没有事实或任务schema变更。

新增四分支×两Provider路径反例，检查来源保留、字段最小化和模型局部修改不影响可信context。提案/提取/Worker定向75项在允许正常线程的本地环境通过（1.910秒）；受限沙箱线程首跑停滞已中断，不能把该次算通过。R1原总p95逐项复核误差小于1e-6ms，仅浮点舍入。R3/R4和最终同SHA回归仍待。

## R3：Provider能力契约

只将固定上游`87c6df77…`已复核OpenAI适配器原生绑定方法列为native_tools；类继承默认文本回退、未知覆盖和实例替换均不证明能力。未复核Provider使用现有response_no_stream单次JSON文本路径（仍需原校验），没有该路径则明确拒绝，不自动二次请求。当前glm-4-flash-250414/供应商/凭据不变。

能力矩阵：native tools在固定OpenAI实现与既有三SDK原文中已证实；函数选择/strict schema未由该适配器转发且无兼容证明，均不启用；普通JSON仅为文本回退，不声称供应商保证JSON模式。`verification/mia-persona-memory/performance-r3-provider-contract.json`记录固定源码hash与原39180767649三请求参数（tools存在、tool_choice/response_format/strict不存在）。无新真实请求。

能力选择/继承/未知覆盖/实例替换及两条提取路径14专项通过；连同提取/Worker77项定向回归通过。最终安装到固定上游后的原生路径仍由本批最后同SHA实际向量/SDK回归验证，不将测试替身当远端能力证明。R4待完成。
