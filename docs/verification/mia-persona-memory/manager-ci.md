# P07 Java 基线与隔离身份复现

固定上游 `87c6df77b0220ddbd8fc804f984f83f69f3225e5`、Java 21、既有 Mia companion 补丁；不访问生产数据库、设备或用户。

- `74d89641f9516f00e3e83520f3972599f837bd76`：[38590737953](https://github.com/bboytang/Mia/actions/runs/38590737953) 编译及四类字节对照通过，但上游默认跳过测试；不是 Java 测试通过。
- `a7028e9ec05f34a13487db4876af59b4d60f7810`：[38592420502](https://github.com/bboytang/Mia/actions/runs/38592420502) 使用临时 MySQL 8.4／Redis 8，显式启用全部上游测试；150 项实际执行，149 通过、1 失败、0 跳过、0 error。
- 唯一失败 `SensitiveDataUtilsTest.maskMiddle_keeps_four_at_each_end_for_long_strings`：输入 `verylongapikeyvalue123` 的末四字符为 `e123`，现有测试却断言 `3123`。它与本次必要身份链修改无关，保留并报告，不修改上游测试或生产脱敏逻辑。该 run 总体为 failure。

后续 CI 保持完整回归可见，不用忽略失败参数或跳过该测试制造全绿。身份复现与字节检查在完整回归失败时仍独立执行，最终 workflow 仍保留失败状态。

新增 `server/companion/manager_tests/MiaIdentityBaselineTest.java` 由 CI 复制到隔离上游 test 目录：实际 Spring 随机 HTTP 端口、Shiro 验证、官方用户 token 签发、真实 MySQL／Redis，没有 mock 身份服务。仅使用合成 A／B、固定测试 MAC 前缀和临时服务参数。

首版复现的断言故意证明旧缺口存在：匿名 OTA 可为伪造 client 签旧 token；A 可手工添加／激活设备指向 B 的 Agent；A 解绑 B 设备时设备仍在但 B 通讯录被删除。**复现测试通过意味着旧缺口得到运行证实，绝不意味着安全通过。** 尚未运行新增复现，生产整改 P08／P09 未开始。后续修复验收需另列拒绝伪造／跨用户及合法路径的真实测试。

换环境只需从任务提交运行 `Verify Mia manager baseline` Actions。脚本、固定源码、临时服务和测试入口均在仓库，不依赖旧 `/tmp`、生产密钥或原 Codex 账号。制品包含 Surefire 与 class-comparison；必要结论同步此目录和交接。

首轮新增复现 `d8690e3aee1a34b953020d8cc194693f03fdd646`，[38593101882](https://github.com/bboytang/Mia/actions/runs/38593101882)：4 个复現用例在 Spring 启动阶段 error，没有执行到缺口断言。test resources 覆盖主 application，未激活 dev 导致未确定数据源 driver；改用既有 dev profile 并显式测试 context-path。四类对照仍通过，完整上游回归仍仅同一既有失败；修正后须复核，不能称身份运行复现已成功。

`c7770a4106d9a5351e29fbc87ccc67e68f145df8`，[38593905608](https://github.com/bboytang/Mia/actions/runs/38593905608)：真实 HTTP／Shiro 已启动。A 向 B Agent 手动添加、A 解绑导致 B 通讯录删除两个旧缺口运行复现通过。激活 fixture 使用不可变 Map 触发现有 Redis serializer 缺 type id；OTA fixture 只写 Redis 而签名从 MySQL 读取，参考密钥不一致。两项为测试数据设置问题，改成与既有代码相同的 HashMap、官方参数更新服务同时写库和缓存；待复核。未因此修改生产 Redis 或账户／通信能力。
