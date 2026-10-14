# P08 私有授权链开发记录

状态：manager部分已通过真实验收及构建；P08整体、P09及实际TLS／App迁移仍未完成，未部署。

代码 `7798936eb9a6f578d02b43778f55247ec2a8eb9a`，[38618373002](https://github.com/bboytang/Mia/actions/runs/38618373002)：9私有＋1默认传输＋4绑定真实用例全部通过，JAR构建及必要class范围对照通过；完整164测试163通过、唯一既有脱敏失败，总workflow仍failure。持久证据和JAR校验值见 [结果](private-authorization-results.json)。实际生成diff已审核，只涉及必要DeviceService／DeviceDao／Shiro路由、追加迁移及两个授权payload。

用户已确认智控台一次性授权码方案。复用现有 Shiro 用户 token、Agent 权限、设备 ID／绑定及 MySQL；只新增一张私有授权表、一个服务与一个控制器，修改必要设备生命周期与两个精确匿名兑换／续期路由。不新增账号、身份提供商或通信服务。

- 登录所有者生成随机128bit授权码，10分钟；服务端仅存SHA256。重新生成替换旧码；当前绑定与权限未变时，已有私有凭据维持到新码成功兑换或显式撤销。
- 兑换在真实设备／授权行事务锁下原子消费，随机256bit私有凭据、30天；仅存散列，客户端绑定明确。五次失败按事务提交保留，拒绝异常由控制器在提交后返回，避免错误次数随异常回滚。
- 固定分钟窗口每真实来源20次、全局120次；Redis键90秒期限，来源散列，忽略未经信任的转发IP。全局先判断，限制新来源键数量；Redis失败不签发。
- 返回Scope由真实账号、Agent及绑定产生，包含operator／有效owner／Agent／固定mia Persona／设备／client／绑定和凭据版本／权限／到期。管理员操作者与数据owner可以不同；当前账号状态、权限和绑定每次验证复核。
- 私有续期需要当前有效凭据和权限，轮换后旧凭据失效；到期、撤销、解绑或重绑拒绝旧凭据及旧码。同设备重建保留身份版本计数。旧OTA token／MAC／请求owner不授予私有权限。
- 解绑在真实设备行锁下检查所有者，再处理副作用及授权撤销；创建／删除设备及按用户／Agent删除同步推进授权版本。表中没有长期记忆事实。

公网授权码／凭据接口默认要求HTTPS；只有隔离测试显式允许HTTP，dev profile本身不放宽。默认拒绝HTTP及不可信的 `X-Forwarded-Proto`。内部 `/config/mia-auth/verify` 复用现有server-secret链；其生产调用必须经已核实的内部通道或HTTPS。实际证书、受信任代理设置和App安全入口尚未部署或验收。

入口：`install_identity.py` 对DeviceService／DeviceDao／Shiro／Liquibase master完整preimage校验，新增payload在 `manager_identity/`，所有既有文件独立备份且拒绝覆盖。只在固定隔离源码生成及编译；迁移新增changeSet，不改旧changeSet或现有账号／设备表。

GitHub入口增加9个实际HTTP／Shiro／MySQL／Redis私有授权用例和1个默认传输用例：原子双客户端兑换、散列、错误次数／到期、Scope来源、不同设备／client、续期／撤销、原ID重绑、管理员与owner区别、当前状态／角色、转发头限流、默认HTTP拒绝；原4个绑定行为和全部上游回归继续执行。没有mock身份与授权，测试只使用合成账号／设备，期限负例使用真实数据库中过期的时间值。

尚待：P09语音／工具／后台任务的持续Scope检查、App Keychain迁移、智控台最小入口、实际TLS和完整跨用户行为。不能把本阶段manager接口当八项能力或完整运行安全已经通过。
