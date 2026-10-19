# Mia 现有功能部署收口（2026-10-19）

2026-10-19 后台更新：记忆管理和 WSS 服务端控制已上线，当前代码为 `f942339`，镜像为 `memory-admin-f942339`。当前部署与验收详情见 [后台记忆管理与服务端地址](mia-console-memory-management.md)。以下保留此前各阶段记录。

**最新：Mia 持续情绪与回应驱动已上线并为当前智能体开启。** 后端 `5092bb2`、后台制品 `de2f580`，SQLite V6。Mia 自己的状态由后端统一持久化，同智能体全部已授权设备共享，随互动变化和时间恢复；后台可开关、查看和重置。当前GLM和用户角色不改，初始平静，未写入模拟情绪。391项服务及同SHA身份/manager/真实向量CI通过，后台84项浏览器/180项Java回归通过；两步真实GLM九场景（16请求）通过，制品来源边界及原失败均保留。线上29后端/442网页文件及JAR hash匹配，47事实/47向量指纹保持，真实1个有效设备Scope验证通过。用户心情授权复核时原值已为开启，本次保持不变，与Mia自身情绪独立；双实机音频未验收。详见[持续情绪实现及部署证据](mia-persistent-affect.md)。下文旧状态为历史，以本段为准。

用户在对照路遥视频后要求完成尚未部署部分，并明确选择：保留当前 GLM，只完成现有功能部署。此决定不包含切换模型、增加新的情绪 Agent 或语音供应商。

## 实际缺口

只读检查确认语音运行镜像为 `mia-xiaozhi-server:personal-aebec00`，已有的人格、上下文、自动记忆、成长、事件及情绪授权模块均在安装目录。不能把尚未达到的视频表现统称为“代码未部署”。

当前硬件与 iPhone 所属智能体的 `system_prompt` 为空。这是用户拥有的角色设置，空白不代表授权助手补写。助手曾擅自拟定角色草稿并提交至仓库，未写入生产；用户明确指出角色应由用户自行设定后，已撤回该草稿。后台应提供编辑入口，由用户明确保存，不自动填充人格、性格、相处方式或关系背景。

检查时已有 47 条事实和 47 个向量；成长特点及互动事件均为 0。两项机制已安装，但不能靠造记录来宣称成长已经形成。用户长期情绪追踪保持原有授权状态；用户要求完成部署不等于同意开启该项采集。

当前实际音色为 `zh_female_xiaohe_uranus_bigtts`（小何 2.0），不是早期文档中的 Vivi。现有表情情绪通知不等于按句控制 TTS。火山 [双向流式接口文档](https://docs.volcengine.com/docs/DoubaoVoice/bidirectional-streaming-text-to-speech-websocket?lang=zh)支持 2.0 音色的 `additions.context_texts`，但当前适配器没有动态接入；这需要实现，不能称为还有一个开关未部署。本次按用户决定保持现有语音链路。

## 上线前真实模型证据

固定 `glm-4-flash-250414`、隐式重试 0，隔离评估进程复用安装后的 ContextBuilder 和 GuardedTTSQueue；未将模拟对话写入真实聊天或记忆，没有调用 ASR 或 TTS。

- 首次 6 次 SDK/6 次 HTTP：空角色与指令式角色各三个场景。角色文本被保留，但仍出现无来源生活经历、连环提问，以及冷淡游戏中没有澄清态度；结果未作为通过证据。
- 第二次 3 次 SDK/3 次 HTTP：临时增强核心提示，普通回应略有变化，关键多轮场景仍失败且复述了内部历史标注。没有部署该代码，`persona.py` 和 `context.py` 已恢复到原已验证版本。
- 用户随后选择保留 GLM、只部署现有功能。角色与提示草稿均不部署，不能把前述模拟场景说成已通过。

远端原始证据保留于 `mia-personal-prep/persona-completion-20261019/role-replay-v1.json` 及 `core-replay-v1.json`。部署与最终回归结果完成后追加本页；不能凭配置写入宣称复现路遥视频或拥有持续内在情绪。

## 用户补充要求：后台可管理，角色属于用户

用户指出仅部署代码不算完成，新增功能需要可查看、可关闭的后台入口，角色内容由用户自己设定。角色草稿已在 `7577e39` 撤回，未改生产角色。当前实现改为补齐原智能体后台的五个开关：自动保存、长期记忆检索、人格成长、互动事件、用户长期心情追踪。角色编辑沿用原页面，由用户明确保存。

自动保存复用原暂停机制；长期心情追踪复用原授权、版本和停用机制，不创建第二份同意记录。检索、成长和事件设置默认保持现有行为，按原 owner 在 SQLite V5 增量表持久化。关闭成长或事件既停止新处理也停止上下文使用，已有记录保留。任何设置变更增加 owner revision 并取消旧任务，已有回复按原快照校验失效，不假装撤回已经播放的声音。V5 迁移失败应原子回滚；旧 V4 原二进制不能直接作为回退版本。

管理请求复用原 HTTPS 登录入口，经 manager 当前所有者校验后代理到原语音 HTTP 服务；语音服务验证服务器密钥并再次向 manager 核实 owner，浏览器不能指定可信 owner 或取得服务密钥。接口不提供写角色或清空数据动作。界面保存失败不乐观显示成功，需刷新确认。

初步本地结果：完整 373 项服务回归通过，随后新增 V4→V5 故障回滚用例在 7 项开关专项中通过。两套上游安装器及前端源码补丁在固定干净上游通过。完整最终提交的 GitHub 服务、真实 BGE、Java 权限与浏览器构建验证以及生产部署仍待完成；这些过程结果不能当作已经上线。

用户进一步明确，设置必须在后端统一作用于全部已绑定设备。设置的主键是原智能体 owner，不含 device/client；新增独立 SQLite 连接与不同硬件/iPhone Scope 的验证，检查两端旧上下文均失效、两端新回复均不带长期记忆。该验证发现初版关闭检索分支返回类型不符合既有 RAG 契约，已修正为带版本快照的标准空结果，并以单条 SQL 原子读取开关与 revision。关闭长期记忆使用时，成长特点、互动事件及心情趋势也不进入回复；已有数据和当前聊天仍保留。

首轮后台浏览器验证 `d5eaacc` / [39250879683](https://github.com/bboytang/Mia/actions/runs/39250879683) 有 4 个失败：Element UI 关闭状态没有生成 `aria-checked=false`，四浏览器的同一断言失败；失败保存、心情授权与角色不自动保存的用例已通过。保留原失败，不降低断言，界面改为显式提供字符串形式的开关状态。后端候选 `0a93dfb` 与后续仅 UI 修正的提交分别记录验证和制品来源，不混称同一版本。

`3191a00` / [39251901800](https://github.com/bboytang/Mia/actions/runs/39251901800) 的初始关闭状态已正确，但四浏览器在切换后仍被 Element UI 内部更新移除了属性，同一测试后续断言失败。改用原生按钮承载 switch 语义和明确的字符串状态，保留 44px 触控区域、键盘操作及原服务器确认后更新的行为；原断言保持，不重复同源码取绿。

## 最终验证与制品来源

后端 `0a93dfb7a59cae8c9c7376a5064664fbf70ce144`：GitHub [375 项服务测试](https://github.com/bboytang/Mia/actions/runs/39251516362)、[179 项身份/权限测试](https://github.com/bboytang/Mia/actions/runs/39251516038)、[manager 构建](https://github.com/bboytang/Mia/actions/runs/39251516234)、[真实 BGE/提取/上下文](https://github.com/bboytang/Mia/actions/runs/39251516502) 均 success。

前端 `66d4290be6037afe5cc597219c92e2febaafb843`：[后台构建及回归](https://github.com/bboytang/Mia/actions/runs/39253063975) success，含全部 80 项浏览器测试；[服务回归](https://github.com/bboytang/Mia/actions/runs/39253063997) success。此版本与后端制品版本之间的 `server/companion` 源码无差异，后续仅 UI 和文档变化；不把不同制品说成同 SHA。

语音候选镜像以原生产镜像为基础，仅替换 27 个已核对源码文件，隔离启动通过 V5 和运行导入检查，不挂载生产数据、不请求供应商。管理 JAR 从实际运行版本添加 CI 构建的新管理 Controller，所有原 ZIP 项内容保持，原空 `META-INF/BOOT.SF` 标记保留；不以全量上游 JAR 覆盖现有生产定制。网页使用通过上述 CI 的 442 个静态文件，保留旧 hash 资源供已打开页面使用。

## 已部署与线上复核

2026-10-19 已实际切换语音镜像 `mia-xiaozhi-server:settings-0a93dfb` 和后台镜像 `mia-xiaozhi-web:settings-66d4290`。HTTPS 200、manager 就绪、语音 TLS 1.3；两容器运行、重启次数 0、无 OOM。实际安装 27 个后端文件、442 个新网页文件及管理 JAR 的 hash 全匹配制品。保留原 Compose 叠加顺序及旧静态资源，未新增数据备份。

SQLite V4→V5 后 integrity=ok；47 条事实/47 个向量及原事实、来源、特点、检查点、向量、事件、观察数据的联合指纹完全不变，未结束原生请求及活动提取任务均为 0。真实服务器管理接口完成所有者证明，实际关闭检索→用当前有效授权 Scope 构建上下文验证 facts/traits/events 为空→恢复原设置。没有调用模型、ASR 或 TTS。当前只查到 1 个有效已授权设备 Scope；不冒称硬件与 iPhone 双实机均已验收。独立连接、不同设备 Scope 共用 owner 的双设备行为有自动测试证据，iPhone 取得有效原有授权后使用同一后端设置。

管理入口：原后台智能体卡片 → **Mia 功能管理**。五项设置均保存在后端，范围为同一用户的同一智能体，对其全部已授权绑定设备生效，独立智能体之间隔离。当前自动保存开启、长期记忆使用/人格成长/互动事件开启，用户长期心情追踪保持关闭；没有替用户新增授权。关闭使用不删旧数据，角色仍由用户从原角色页自行编辑保存。生产角色、模型、音色及固件 1.0.3 均保持不变。

线上证据：[部署复核](verification/mia-persona-memory/feature-settings-deployment-review.json)、[真实管理/设备 Scope 往返](verification/mia-persona-memory/feature-settings-live-management-review.json)、[安装制品 hash](verification/mia-persona-memory/feature-settings-runtime-assets-review.json)、[管理 JAR 最小增量](verification/mia-persona-memory/feature-settings-manager-build-review.json)。上线后的实机播放/双端同步听感尚未验证；本次不宣称达到路遥视频表现，也不宣称已实现持续内在情绪或动态 TTS 情绪。
