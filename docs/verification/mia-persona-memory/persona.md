# P11：分层人格与输出前检查

状态：首轮机制实现待GitHub验证；未部署，B01整体尚未验收。

固定核心由PersonaAgent拥有，角色经JSON编码为风格数据；复用原PromptManager更新，每次change_system_prompt重新组装且相同结果幂等。保留既有唯一memory slot，旧memory／personality材料继续按已授权Scope取得；完整RAG、ContextBundle、资格事件分别待P12—P15／P19，不能将它们视作已经完成。

核心在TTS启动前初始化，不依赖数据库；八类emoji意图也不再依赖MemoryStore成功。已知严重“绕过规则＋公开私有配置”输入在现有回复链返回有限回应，不请求第二模型。检测信号不作为权限证明，现有身份／工具Scope守卫继续生效，教育性讨论不自动拦截。

同一现有TTS队列外增加句级检查入口，普通文本、流式direct_answer及工具直接文本回复均经过它；完整句未到前不交给TTS消费者。只保留当前sentence，待检查片段最多1024字符，过长无分句文本替换后停止该段；旧sentence被丢弃。正文、字幕缓存与assistant历史检查已知不实意识／永久陪伴／排他依赖／公开密钥表述，不禁止诚实说明AI身份。不是通用语义证明，真实模型和完整行为必须独立验收。

保留原Queue、DTO、TTS消费者和文件音频播放，不改声学引擎、不宣称检查预录音频内容。保留官方tts/base.py修复，未扩大preimage文件集合；仅扩展已有connection／dialogue补丁。历史和字幕的全量检查不能替代队列输出前检查。多工具结构不改写，统一ContextBundle与输出历史的完整联动在P14／P15继续验证。

首轮验证：服务CI新增句级流式、跨delta不实表述、残余文本／LAST、超长边界、旧sentence、文件顺序、AI身份、角色更新、教育讨论、历史与数据库故障等机制用例。身份CI用真实manager Scope、实际安装包／DTO／Dialogue和合成TTS sink证明检查发生在消费者前；不是实际ASR／声学／iPhone测试。

下一步：先核对本提交精确SHA的服务和身份CI，失败先修复；再以专用Secret运行固定少量真实Provider流式场景。真实人格样本不替代跨会话记忆、完整事件、长期趋势或八项验收。
