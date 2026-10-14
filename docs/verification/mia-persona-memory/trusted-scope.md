# P09 可信 Scope 贯通

实现入口：`server/companion/authorization.py`，安装入口仍为固定 preimage 的 `install_xiaozhi.py`／`install_identity.py`。没有第二套身份权威。

Scope 仅从 manager 的真实私有凭据核验和配置门禁取得，强校验 owner／用户／Agent／固定 mia／设备／client／operator／版本／权限／期限的一致性。任务持久快照无明文凭据，恢复时须经 server-secret check-scope 重新验证；客户端 owner／JSON 快照不作证明。

manager RPC 复用原客户端和 server-secret，每次最多一个请求、总3秒、无6次重试链；连接初次核验与配置读取整体也限定3秒，身份等待4秒以内，不再因原1秒等待丢失合法hello。当前允许HTTPS和字面loopback；生产内部HTTP通道未审核，暂不放行。私有连接头只接受服务端可证实的原生TLS，消费后从连接headers移除；不信任任意 X-Forwarded-Proto。若最终TLS在反向代理终止，必须先核实代理／源地址／监听隔离，再实现必要的可信入口，不能在发布时绕过此限制。

manager既有WebMvcConfig将Java Long序列化为十进制字符串以保留精度，Python仅从已核验响应接受规范十进制整数或整数，并按Long范围严格归一化；旧绑定初始版本0有效，用户／operator／已签发凭据版本必须正值。bool／浮点／非规范字符串／负版本／溢出不被截断转换。App同样接受实际签发返回的字符串 expires_in，不修改既有全局序列化器。

旧设备缺授权时，标记独立的 authorization_required，发送 `mia_authorization/required` 提示，保留 hello 和设备ID／绑定，不初始化个性化模型或上报私有对话，不使用公共语音回退。等待身份结果期间不误报为重新绑定。App 尚需识别该事件并实现授权码兑换／Keychain／WSS迁移。

已有单回复链入口（包括递归工具续答）、实际工具执行、TTS文本发送和实际音频包发送重新核验Scope；私有记忆查询／管理响应及后台写入前复查。授权失效时停止输出和工具，不把私有查询失败改为空字符串后继续用旧私有材料生成。初始化失败不回退到原设备ID记忆模块；人格固定提示与存储初始化成功解耦，但完整PersonaAgent行为仍属于P11，当前不宣称实现。

后台仍为旧checkpoint机制，尚非P16持久任务；现有FTS原型仍非P12／P13完整RAG。当前核验不证明跨manager／SQLite事务的所有并发竞态或全服务撤销，也没有测量每包权限复查对音频和TTFT的影响；这些是P09剩余并发验收及P23门槛，不可省略。

验证入口：身份Actions启动实际Java／MySQL／Redis；新增Java用例在真实manager端口运行Python客户端，验证配置／可信快照／generation／output／tool守卫与实际撤销。合成工具只核验授权边界，不冒充真实LLM或真实私有工具能力。服务Actions保留全部回归，加入结构负例、配置不一致、明文头拒绝、输出中止与后台提取中撤销机制测试；mock政策测试与真实manager集成明确区分。当前补丁尚待GitHub执行；真实WSS、App／iPhone、P16和八项行为未验收。
