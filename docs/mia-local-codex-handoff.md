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
4. P23当前24d06b0：服务285/身份173/manager154/BGE五报告全通过；容量38997698723已failure，1k短/长全达标，10k单路混合341/387ms、SQLite84/95ms、必测RSS369MiB达标，但双前台竞争698/764ms超400ms。第七步诊断38998096508已success，HEAD07d43df的运行仍24d06b0。收完同一handle再据profile修改；详见主交接。P23未验收/P24未开始。

已拉取当前分支即已包含交接和证据；`docs/handoff/`里的旧补充包仅为历史快照，不重复导入tracked.patch或覆盖本地文件。详细失败、模型比较和旧run留在工作记录/验证目录，不在本接续入口重复。

本地可执行检查优先本地，Linux/macOS专属验证按原计划使用适用环境；不使用Conda、WSL或本地Docker，不改生产配置/数据库，不读取复制密钥。身份隔离、唯一事实库和既有Worker约束见主交接。

第七步诊断已收齐并归档performance-batch-diagnostic-*，无在途。热点为批量字符串转换/np.char.find；下一最小修改以原生term in query收集布尔值，保留bigram批处理及原语义，再做同SHA回归/容量。

第八步实现仅替换批量词项匹配为np.fromiter(term in query)，其余运行实现不变；本地标准库3项/语法/diff检查通过。GitHub完整等价/并发回归与新固定容量待提交后执行，不提前宣称改善或达标。

第八步候选df652890d41beb2f8a3d93c9eeb4be852fc5d0cd：容量39027799458、服务39027795017、BGE39027795008、身份39027795020、manager39027795011在途，均为同SHA；等待原句柄，不重复dispatch。

第八步已收完：df65289/容量39027799458 failure，10k单路338/379ms、SQLite112/110ms、RSS402MiB达标，双前台707/913ms超400。服务285/BGE五报告/身份173/manager154均success，原文/hash见performance-literal-*。当前无在途；下一步每批精确来源top-k再合并，补跨批同分全结果等价，保留所有行校验与权限语义。
