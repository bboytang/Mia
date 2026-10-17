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
4. P23当前d2bfd7b：服务280/身份173/manager154/BGE五报告全通过，但容量38995549068已failure，10k长混合474ms/竞争1868ms仍超400ms；纯SQLite106ms/必测RSS412MiB达标，50k探索RSS580MiB超标。旧回归/容量已收完；当前第五步a749a82诊断38996682107在途，运行实现仍d2bfd7b，继续同一句柄，不重发。P23未验收/P24未开始。

已拉取当前分支即已包含交接和证据；`docs/handoff/`里的旧补充包仅为历史快照，不重复导入tracked.patch或覆盖本地文件。详细失败、模型比较和旧run留在工作记录/验证目录，不在本接续入口重复。

本地可执行检查优先本地，Linux/macOS专属验证按原计划使用适用环境；不使用Conda、WSL或本地Docker，不改生产配置/数据库，不读取复制密钥。身份隔离、唯一事实库和既有Worker约束见主交接。
