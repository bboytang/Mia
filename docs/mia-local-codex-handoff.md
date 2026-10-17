# Mia Windows 本地接续

更新：2026-10-17。当前唯一进度入口：[人格与记忆交接](mia-persona-memory-handoff.md)。

## 当前状态

用户已确认采用`glm-4-flash-250414`，**P22验收通过**。已知实测问题和未执行范围见[用户验收决定](verification/mia-persona-memory/p22-user-acceptance.md)。2026-10-17用户已批准开始P23，详见主交接及[性能进度](verification/mia-persona-memory/performance.md)，P24未开始；生产配置未因本次验收记录而切换。

## 本地工作区

- 仓库：`https://github.com/bboytang/Mia`。
- 分支：`feature/mia-persona-memory-v1.2`。
- 路径：`C:\MiaDev\Mia`。
- Python优先使用`C:\MiaDev\mia-venv\Scripts\python.exe`；GitHub CLI位于`C:\MiaDev\Tools\GitHubCLI\2.102.0\bin\gh.exe`。
- 跨设备时重新确认工具路径和访问权限，不复制密钥。

## 接续检查

1. 读取`AGENTS.md`、主交接、验收决定、实施计划及最近工作记录。
2. 核对当前分支、HEAD、未提交文件、远端实际SHA和未推送提交；保存已有工作，不reset/clean/强推。
3. P22实测代码为`2925b63e6ea010ac287d4e388fd6255e7d202244`；证据提交为`1a05c98044ebd3e333bce041c29f4c26c782f2a8`。后续文档提交记录用户通过决定，原始结果不变。
4. P23运行仍1913680，模块容量/四回归已通过；第十一步预检f2784d7的共同39070920385、服务39070920411、manager39070920170在途，语法39070912579 success。前两次解析/就绪脚本失败未进入完整测量，原文见performance-shared-first-*；先收当前组句柄。整体P23仍未验收/P24未开始，尚有首句基线/真实Worker公平任务故障/全服务在途关闭。

已拉取当前分支即已包含交接和证据；`docs/handoff/`里的旧补充包仅为历史快照，不重复导入tracked.patch或覆盖本地文件。详细失败、模型比较和旧run留在工作记录/验证目录，不在本接续入口重复。

本地可执行检查优先本地，Linux/macOS专属验证按原计划使用适用环境；不使用Conda、WSL或本地Docker，不改生产配置/数据库，不读取复制密钥。身份隔离、唯一事实库和既有Worker约束见主交接。

第十一步已收齐：f2784d7/39070920385有效数值failure，四实际进程共同2CPU/2GiB已验证、无OOM；1k/10k跨用户竞争455/2645ms，单路/SQLite/RSS达标。服务287/manager154通过，原文/hash见performance-shared-ready-*。无在途。下一步有界缓存192MiB（原512RSS/2GiB硬门槛不变）、落实测试ERROR日志及实际授权端点耗时；1k也超标，不单归因缓存。P23未验收/P24未开始。

第十二步候选已实现：预算192MiB（原512RSS/共同2GiB门槛不变）、测试ERROR logger、真实授权端点计时；本地19项/语法检查通过，待新SHA模块/共同包络/相关回归。以第十一步有效失败为基线，未预先宣称改善或达标，P23未验收/P24未开始。
