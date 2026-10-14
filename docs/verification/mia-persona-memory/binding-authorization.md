# P08 必要绑定授权整改（阶段记录）

状态：最小绑定补丁已验证，四个真实用例、必要类范围和 JAR 构建通过；完整回归 153／154，唯一既有脱敏失败继续报告。P08 整体未完成，未部署。

代码 `75286114be811700edba9c4f21e3335e391590cd`，run [38613934248](https://github.com/bboytang/Mia/actions/runs/38613934248)。持久证据及构建 SHA 见 [结果](binding-authorization-results.json)；总 workflow 为 failure，不能称全量回归通过。实际生成的 Java diff 已检查，仅 DeviceService 改变，另外三类与现网基线字节一致。

对应固定运行复现 [38594888061](https://github.com/bboytang/Mia/actions/runs/38594888061) 的三项缺口：

| 缺口 | 最小改动 | 真实验收 |
| --- | --- | --- |
| A 激活设备指向 B Agent | 消费激活码前复用 `AgentService.checkAgentPermission` | A 拒绝、无码消费和写入；B 合法绑定并消费；保留原设备 ID |
| A 手工添加指向 B Agent | 写库前复用同一权限判断 | 匿名／A／过期 token 拒绝，B 合法添加；既有管理员权限保留 |
| A 解绑触发 B 通讯录删除 | 缓存和数据库副作用前检查设备归属 | A 拒绝、B 设备及双向通讯录保持；B 合法删除 |

只修改固定上游 `DeviceServiceImpl`，复用现有 Agent 授权及 Shiro 账号 token；三个修改方法使用现有 Spring 事务。引入的 AgentService 采用 lazy field 注入避免现有构造环；改为 RequiredArgsConstructor 保持原六个 final 参数，既有构造测试兼容。不修改账户模型、通信协议、设备标识或数据库 schema。

`server/companion/install_identity.py` 校验整份源码 preimage，打印可审核 diff，应用时独立备份并拒绝重复覆盖。仅对隔离固定源码执行；不能直接在现网已安装目录试运行。CI 先重建原 companion，再应用此补丁。

`MiaBindingAuthorizationTest` 使用真实 HTTP／Shiro／MySQL／Redis，合法身份由官方 token 服务签发；没有 mock 身份与授权。完整上游 Java 回归显式启用，已知上游脱敏测试失败仍使 workflow 保持 failure；另记录四个新行为用例、未改三类基线、目标 DeviceService 类改变及 JAR 构建结果，不能把构建或 class 差异代替行为通过。

尚未完成：一次性授权码、私有凭据签发／兑换、旧弱 token 的私有权限区分、持续 Scope／绑定版本／撤销、TLS 与 App 迁移及相应真实安全验收。匿名 OTA 旧签发缺口不能因这三项绑定修复被标解决。P08／P09 完整链验收前不开放整合后的私有记忆权限。
