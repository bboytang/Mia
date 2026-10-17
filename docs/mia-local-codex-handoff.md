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
4. 当前运行83e837a：服务288/实际BGE五报告/身份173/manager154全通过、本地20专项通过；模块39072833943和共同39072835426均failure（10k竞争435/779ms），必测RSS/共同2GiB与缓存完整性达标。50k探索延迟/RSS失败，不能称支持。所有六项终态已收齐，当前无在途任务，原文/hash见performance-stream-*。下一步同环境配对诊断ONNX 2/1线程与真实扫描竞争，核对向量/候选/排名一致性、CPU/RSS再决定新候选；不重跑同源码容量取绿。P23未验收/P24未开始。

已拉取当前分支即已包含交接和证据；`docs/handoff/`里的旧补充包仅为历史快照，不重复导入tracked.patch或覆盖本地文件。详细失败、模型比较和旧run留在工作记录/验证目录，不在本接续入口重复。

本地可执行检查优先本地，Linux/macOS专属验证按原计划使用适用环境；不使用Conda、WSL或本地Docker，不改生产配置/数据库，不读取复制密钥。身份隔离、唯一事实库和既有Worker约束见主交接。

第十四步运行候选`83e837a1eae2ce7b304561d204ac5255d57dbb4e`已推送：唯一模块容量39072833943、共同容量39072835426；服务39072828991、实际BGE39072828959、身份39072828973、manager39072828956四回归均在途。继续同一组句柄，暂不修改运行实现；本地20专项通过不是容量结论。P23未验收/P24未开始。

第十四步六终态现已收齐，以上第4项是当前接续状态；本文历史追加段落中的“在途”不构成当前任务。运行实现83e837a，下一候选尚未实现。

第十五步已新增仅CI使用的threads诊断模式：同父组ABBA四独立进程（2/1/1/2线程），真实向量/完整检索结果与阶段耗时分开核对，运行实现仍83e837a。语法/AST/Shell/YAML/diff通过，唯一GitHub句柄随后记录；当前正式容量仍failure，不晋升候选。
