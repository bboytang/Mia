# P08／P09 实际TLS隔离验证

身份验证从HTTP隔离manager机制扩展到实际Spring Boot HTTPS及原生WSS。新增TLS用例默认关闭 insecure-test-http；使用独立合成用户／设备和现有智控台令牌真实生成／兑换，Python沿真实server-secret读取私有配置和Scope。

GitHub生成两天有效的隔离CA、带localhost／127.0.0.1 SAN的测试证书与PKCS12，仅在该runner的Java／Python测试信任加入公共测试CA。私钥留runner临时目录，不进入Git／制品／聊天。WSS客户端以明确测试CA和正常地址校验握手；未信任CA必须拒绝。旧语音HMAC用固定上游core.auth真实算法，缺独立私有凭据须提示授权，有效凭据取得Scope，真实manager撤销后同WSS连接的下一输出守卫必须拒绝。

语音固定源码补丁只增加可选原生TLS上下文：`MIA_TLS_CERT_FILE`／`MIA_TLS_KEY_FILE`同时存在才启用SSL；单项缺失或证书／密钥错误导致启动失败，不降级明文。未提供时保留现有普通WS，私有头仍必须TLS。保留原端口、协议、设备ID／语音HMAC，不新建网关、账户或代理信任体系。新增websocket_server完整preimage核验和独立备份。

此项是实际manager HTTPS、Scope与WSS传输边界验收，WSS harness不是真实ConnectionHandler的ASR／LLM／TTS运行，也不是iOS平台信任／授权码兑换整链或八项行为。生产可信证书、续期、OTA／manager／语音入口、内网通道和真机仍需发布前核实。公网域名或可信IP证书均可，未申请证书、开放端口或部署。

当前：代码／真实TLS用例待本提交GitHub验证，不能提前标通过。已完成的非TLS Scope [38626866860](https://github.com/bboytang/Mia/actions/runs/38626866860) 和JAR校验值已归档 `trusted-scope-results.json`。

首次TLS workflow [38629243576](https://github.com/bboytang/Mia/actions/runs/38629243576) 在定义校验阶段失败，jobs为空，没有执行或构建TLS用例；cde3395相同定义的38629858973亦未执行。原因是新路径误用runner.temp于job.env；按 [GitHub context范围](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)移到step.env，再通过GITHUB_ENV向后续真实测试传递路径。证书／私钥不作为环境内容，仅传文件路径。修正提交待GitHub实跑，不能把定义失败记成TLS行为失败或通过。
