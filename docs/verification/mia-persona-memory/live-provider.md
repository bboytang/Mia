# P07 专用真实聊天测试入口

用户于2026-10-14明确选择专用GitHub Actions测试Secret；不读取、转移或复用生产模型密钥。仅使用独立测试输入，不使用生产聊天、事实、音频或账号。

在 [GitHub Actions Secrets](https://github.com/bboytang/Mia/settings/secrets/actions) 配置三个repository Secret：

| 名称 | 内容 |
| --- | --- |
| `MIA_TEST_LLM_API_KEY` | 现有Mia聊天Provider的专用测试密钥；不要在聊天、代码、命令参数或交接中发送 |
| `MIA_TEST_LLM_BASE_URL` | 现有Provider的HTTPS API根地址，即base_url，不是完整chat/completions地址 |
| `MIA_TEST_LLM_MODEL` | 同Provider的测试模型名／endpoint ID，保留Mia既有Provider类型 |

`Verify Mia real chat provider` workflow只在手动dispatch执行真实请求；push／PR仅检查语法，不能记为真实模型通过。初始probe最多1次请求、128输出tokens、30秒、不重试，拒绝HTTP及重定向，不打印密钥、请求头、环境或错误响应body。只有配置齐全才发请求，缺配置明确记录未执行。制品记录代码SHA、配置散列、模型响应、usage与耗时。

这个probe验证真实连接与响应，不是Mia生产Provider集成、RAG、信息不足回答或八项能力验收。后续实际功能必须经真实manager身份、实际提取及向量、Mia单回复链、跨会话／重启和授权时间观察运行。不得用此短请求替代完整行为。

当前：入口刚编写，GitHub语法检查尚未执行；三个测试Secret尚未核实配置、probe未执行。配置内容仅通过GitHub安全界面填写，换Codex账号使用repository权限取得可运行入口，不复制秘密。
