# P07 专用真实聊天测试入口

用户于2026-10-14明确选择专用GitHub Actions测试Secret；不读取、转移或复用生产模型密钥。仅使用独立测试输入，不使用生产聊天、事实、音频或账号。

在 [GitHub Actions Secrets](https://github.com/bboytang/Mia/settings/secrets/actions) 配置三个repository Secret：

| 名称 | 内容 |
| --- | --- |
| `MIA_TEST_LLM_API_KEY` | 现有Mia聊天Provider的专用测试密钥；不要在聊天、代码、命令参数或交接中发送 |
| `MIA_TEST_LLM_BASE_URL` | 现有Provider的HTTPS API根地址，即base_url，不是完整chat/completions地址 |
| `MIA_TEST_LLM_MODEL` | 同Provider的测试模型名／endpoint ID，保留Mia既有Provider类型 |

2026-10-15用户询问具体模型ID后，只读查询现网已配置Agent的LLM选择及对应模型的非敏感字段，当前唯一结果为 `ChatGLMLLM`／`glm-4-flash`，API根地址 `https://open.bigmodel.cn/api/paas/v4/`。因此本轮测试 `MIA_TEST_LLM_MODEL=glm-4-flash`、`MIA_TEST_LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/`，API Key须在智谱另建专用测试密钥；此前火山方舟地址仅作示例，不能用于这组配置。未读取或复制现有API Key，未改现网配置，未调用模型。后续若用户改变模型选择，应重新核实此非敏感映射。

`Verify Mia real chat provider` workflow只在手动dispatch执行真实请求；push／PR仅检查语法，不能记为真实模型通过。初始probe最多1次请求、128输出tokens、30秒、不重试，拒绝HTTP及重定向，不打印密钥、请求头、环境或错误响应body。只有配置齐全才发请求，缺配置明确记录未执行。制品记录代码SHA、配置散列、模型响应、usage与耗时。

这个probe验证真实连接与响应，不是Mia生产Provider集成、RAG、信息不足回答或八项能力验收。后续实际功能必须经真实manager身份、实际提取及向量、Mia单回复链、跨会话／重启和授权时间观察运行。不得用此短请求替代完整行为。

当前（2026-10-15）：用户确认已配置，已只核对三个Secret名称齐全；未读取其值。代码 `81e46ad94addcf95aa69dd67f7212e9fab6b1185` 的手动 [38659019412](https://github.com/bboytang/Mia/actions/runs/38659019412) 语法及live job整体success；仅发送约定的1次请求，实际host为open.bigmodel.cn、响应模型glm-4-flash、耗时1498.23934ms、输入27／输出11／合计38 Token。合成测试响应为“请说明已知条件或建议补充信息。”[脱敏结果](live-provider-results.json)已持久保存；不是实际记忆问答或八项能力验收。

历史语法基线 `1ba397c9866fb0134b4d82366b566e897ce0dd86`／[38621146139](https://github.com/bboytang/Mia/actions/runs/38621146139) 的live job按push跳过，不能追溯改记为真实调用。测试配置现已就绪，换Codex账号需相应repository权限，不复制秘密。后续按P11等实现与验收，不重新运行同一连接probe，也不擅自读生产Key；完整Provider集成及容量／真实行为仍须分别验证。
