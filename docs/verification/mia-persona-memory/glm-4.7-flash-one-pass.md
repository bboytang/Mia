# glm-4.7-flash 单轮实测记录

日期：2026-10-17。用户授权实测一次并由用户决定是否结束P22。测试SHA：`d303f56e36c1b67afabb390b04b1c2f80763309e`。六项均只派发一次，运行中，不重复派发。

| 范围 | 唯一句柄 |
| --- | --- |
| 辅助提取 | https://github.com/bboytang/Mia/actions/runs/38987171428 |
| 自然纠错 | https://github.com/bboytang/Mia/actions/runs/38987175082 |
| 成长 | https://github.com/bboytang/Mia/actions/runs/38987178158 |
| 检索v1已知回归 | https://github.com/bboytang/Mia/actions/runs/38987180364 |
| 工具 | https://github.com/bboytang/Mia/actions/runs/38987182700 |
| 情绪 | https://github.com/bboytang/Mia/actions/runs/38987185248 |

固定原输入、enabled thinking、4096输出、16384测试上下文，既有超时/两尝试约束不变。无运行代码/人格提示/语料改动。四项模型选择契约本地通过；同SHA行为及辅助语法CI通过，真实结果待收。无v2/v3留出重跑，无生产操作。新候选结果不抹去历史失败；v1不是独立留出，不自动宣布P22结束。

首批终态：辅助提取首请求30.05秒超时，首case retry_wait，后九项未执行，不重跑。五行为任务均在Java第69行型号白名单断言停止，尚未调用模型；这是测试入口遗漏，不能归类模型失败。补齐Java同一精确ID后只定向重启这五项，旧失败证据保留，不改变语料/参数/通过条件。
