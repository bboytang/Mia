# Mia 现有功能部署收口（2026-10-19）

用户在对照路遥视频后要求完成尚未部署部分，并明确选择：保留当前 GLM，只完成现有功能部署。此决定不包含切换模型、增加新的情绪 Agent 或语音供应商。

## 实际缺口

只读检查确认语音运行镜像为 `mia-xiaozhi-server:personal-aebec00`，已有的人格、上下文、自动记忆、成长、事件及情绪授权模块均在安装目录。不能把尚未达到的视频表现统称为“代码未部署”。

当前硬件与 iPhone 所属智能体的 `system_prompt` 为空，尚未配置 Mia 的专属人物背景与表达特点。本次只补齐这一配置，内容见 [角色配置](../server/deploy/mia-persona.zh-CN.txt)。既有 `CORE`、单 Provider 回复、记忆来源与权限、模型和音色保持原实现。配置不预置共同经历、恋爱关系或用户偏好。

检查时已有 47 条事实和 47 个向量；成长特点及互动事件均为 0。两项机制已安装，但不能靠造记录来宣称成长已经形成。用户长期情绪追踪保持原有授权状态；用户要求完成部署不等于同意开启该项采集。

当前实际音色为 `zh_female_xiaohe_uranus_bigtts`（小何 2.0），不是早期文档中的 Vivi。现有表情情绪通知不等于按句控制 TTS。火山 [双向流式接口文档](https://docs.volcengine.com/docs/DoubaoVoice/bidirectional-streaming-text-to-speech-websocket?lang=zh)支持 2.0 音色的 `additions.context_texts`，但当前适配器没有动态接入；这需要实现，不能称为还有一个开关未部署。本次按用户决定保持现有语音链路。

## 上线前真实模型证据

固定 `glm-4-flash-250414`、隐式重试 0，隔离评估进程复用安装后的 ContextBuilder 和 GuardedTTSQueue；未将模拟对话写入真实聊天或记忆，没有调用 ASR 或 TTS。

- 首次 6 次 SDK/6 次 HTTP：空角色与指令式角色各三个场景。角色文本被保留，但仍出现无来源生活经历、连环提问，以及冷淡游戏中没有澄清态度；结果未作为通过证据。
- 第二次 3 次 SDK/3 次 HTTP：临时增强核心提示，普通回应略有变化，关键多轮场景仍失败且复述了内部历史标注。没有部署该代码，`persona.py` 和 `context.py` 已恢复到原已验证版本。
- 用户随后选择保留 GLM、只部署现有功能。本次角色配置使用人物背景描述，不把前述提示改动或三个模拟场景说成已通过。

远端原始证据保留于 `mia-personal-prep/persona-completion-20261019/role-replay-v1.json` 及 `core-replay-v1.json`。部署与最终回归结果完成后追加本页；不能凭配置写入宣称复现路遥视频或拥有持续内在情绪。
