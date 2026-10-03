# Mia / XiaoZhi 项目交接记录

> 审计日期：2026-10-03（Asia/Shanghai）。本文件只依据此仓库的代码、文档、Git 历史和本次本地验证；不依据已失效的旧聊天记录。`bboytang/Mia` 的 GitHub 仓库、Git 历史与本文件共同记录项目状态。本次审计的**起点**为 `main` / `origin/main` / `HEAD` 同指 `d395220a83fb7a16ea5dc761c08a4816177cc880`，起点工作区干净。本文件提交后，实际最新 HEAD 应以 `git rev-parse HEAD` 为准。

## 项目目标与当前阶段

本仓库是 XiaoZhi ESP-IDF C/C++ 语音助手固件，而不是 AI 服务端。设备采集和播放音频，通过 WebSocket 或 MQTT 控制加 UDP 音频连接外部服务，并用设备端 MCP 暴露硬件控制能力；项目面向多种 ESP32 芯片及板型。项目版本为 `2.5.1`。[README](README.md)、[顶层 CMake](CMakeLists.txt)、[WebSocket 协议](docs/websocket.md)、[MQTT/UDP 协议](docs/mqtt-udp.md)

当前处于 **ESP-IDF 6 已成为主线后的兼容性和板级收尾阶段**。最近工作集中在 IDF 6.1 构建覆盖、板型适配、单麦默认音频输入和 P4 以太网迁移。这个阶段判断来自提交顺序，不代表所有板型已通过最新编译或实机验证，也无法仅凭 Git 作者判断哪一项由上一位 Codex 完成。本次任务只恢复上下文；下一阶段开发须等待用户确认。

## Git 历史与最近开发方向

| 提交 | 可确认的推进 |
| --- | --- |
| `3e78cd7`、`0f6c435`（2026-07-17） | v2.4.0 迁移到 IDF 6.0.1，随后加固音频、BluFi、MQTT、依赖和构建流程。 |
| `4a5d446`、`ca7221a`（2026-09-10） | 停止支持 IDF 5.x；清单下限设为 6.0.1，CI 统一采用 6.1，并处理 P4 Rev1 音频依赖。当时的 `docs/esp-idf-6-migration.md` 在 `4a5d446` 被删除。 |
| `a44ce7c`（2026-09-30） | Box Lite、T-CameraPlus-S3、S31 Korvo 的输入声明改为单麦默认，留下明确的实机验证要求。[音频审计](docs/audio-codec-input-audit.md) |
| `1185605`、`abc177c`、`ed5cd7b`（2026-09-30） | 增加 Guition 板型、版本升至 2.5.1、CI 改为代表性变体加直接变更板型。 |
| `af55a78`（2026-10-02） | FoloToy AI Passport 增加分阶段空闲功耗策略。 |
| **`d395220`（2026-10-02）** | 最新基线：迁移 IP101 PHY 和 RMII GPIO 到 IDF 6 接口，详见下节。 |

更早和同期还有新板型、e-paper 公共组件、Ogg、OTA、显示、摄像头与协议修复；这是持续合并多方贡献的固件项目，不能把历史提交全部归因于上一位 Codex。恢复任务时应先看 `git log --oneline --decorate -30`、目标文件的 `git log -- <path>` 与当前源码。

## 当前架构

| 层 | 位置与职责 |
| --- | --- |
| 入口与运行状态 | [main/main.cc](main/main.cc) 初始化 NVS 并启动 `Application`；[main/application.*](main/application.cc) 管理网络、激活、OTA、音频、协议与主事件循环；[状态机](main/device_state_machine.cc) 约束状态转换。回调的应用状态变更须调度到主任务。 |
| 板级抽象 | [Board 接口](main/boards/common/board.h) 用单一 `DECLARE_BOARD(...)` 工厂创建当前板；音频和网络是核心接口，屏幕、相机、LED、背光、电池等可选。Wi-Fi、以太网、RNDIS、ML307、NT26 和双网络能力在 [boards/common](main/boards/common) 复用，具体引脚和外设初始化留在 [boards](main/boards)。 |
| 音频 | [AudioService](main/audio/audio_service.h) 用采集、播放、Opus 任务与固定容量队列组织数据流；S3/P4/S31 走 AFE，其余主要走轻量引擎。[音频设计](main/audio/README.md) 说明唤醒、VAD、AEC、输入通道语义及内存策略。 |
| 协议与服务 | [Protocol](main/protocols/protocol.h) 是共享消息契约；[WebSocket](main/protocols/websocket_protocol.cc) 和 [MQTT/UDP](main/protocols/mqtt_protocol.cc) 实现传输；[MCP Server](main/mcp_server.cc) 提供设备状态、音量以及条件可用的显示、相机等工具。 |
| UI 与资产 | [display](main/display)、[led](main/led)、[assets](main/assets.cc) 实现无屏/OLED/LVGL/表情、灯光和资源装载；[notify](main/notify) 及应用层实现通知音频与字幕。 |
| 构建选择 | 每个板型的 `config.json` → [scripts/build.py](scripts/build.py) → [Kconfig](main/Kconfig.projbuild) → [main/CMakeLists.txt](main/CMakeLists.txt) → 唯一板源及 `config.h`。板型名称参与 OTA 身份，不能为了另一硬件改变现有引脚或身份；新增硬件遵循[自定义板型指南](docs/custom-board.md)。 |

## 已实现的功能

- 多种网络：Wi-Fi、板载以太网、USB RNDIS、ML307/NT26 Cat.1，以及部分板型的 Wi-Fi/4G 切换；热点或 BluFi 配网。[README](README.md)、[通用板层](main/boards/common)、[BluFi 文档](docs/blufi.md)
- ESP-SR 离线唤醒词、Opus 双向音频、流式和实时对话所需传输，以及支持硬件上的设备端 AEC；单麦是默认输入策略。[音频设计](main/audio/README.md)、[音频审计](docs/audio-codec-input-audit.md)
- WebSocket 与 MQTT/UDP 两种通信方式、OTA/激活、设备端 MCP、可选摄像头视觉、OLED/LCD/表情 UI、通知、供电与电量管理。[README](README.md)、[MCP 文档](docs/mcp-protocol.md)、[通知文档](docs/notify.md)
- 多语言界面、可选唤醒词/字体/表情资源和多目标构建；README 声称支持 39 种界面语言。芯片覆盖 ESP32、C3、C5、C6、S3、P4；代码和构建也覆盖 S31。[README](README.md)、[main/CMakeLists.txt](main/CMakeLists.txt)

以上表示功能在源码中存在，**不等于每个板型和外设都经过物理验证**。2026-10-03 按 IDF 6.1 规则读取构建配置，得到 **150 个有发布变体的板目录、183 个默认变体**；另有一个 CI 专用 Ethernet 选项。IDF 6.0.2 规则得到 146 个目录、179 个变体。此数字是配置枚举结果，不是成功编译数。[构建脚本](scripts/build.py)、[代表性 CI 清单](scripts/ci/representative-variants.json)

## ESP-IDF 6 迁移与 HEAD `d395220` 的实际状态

1. [依赖清单](main/idf_component.yml) 的 `idf` 下限为 **6.0.1**，[README](README.md) 推荐 **6.1**，IDF 5.x 已不受支持；[CI](.github/workflows/build.yml) 使用 `espressif/idf:v6.1`。S31 变体通过 `idf_version` 限制到 6.1 及以上。ESP-SR 固定为 2.4.7，主线已处理 PSA Crypto、IDF 组件拆分与 P4 Rev1/Rev3 的不少迁移问题。少量板型有更高的实际 SDK 要求，例如 [ESP-Mosaico 文档](main/boards/espressif/esp-mosaico/README.md) 要求特定 IDF master 提交，虽其 `config.json` 仅声明 `>=6.1`。
2. HEAD 把 `espressif/ip101 ^1.1.0` 按 `esp32p4` 目标加入[清单](main/idf_component.yml)，在启用 Ethernet/IP101 时把组件加入 [CMake 私有依赖](main/CMakeLists.txt)，并在 [EthernetBoard](main/boards/common/ethernet_board.cc) 中包含独立 PHY 头、用 IDF 6 需要的整数 RMII clock GPIO 值。Kconfig 目前只在 [Waveshare P4 NANO](main/Kconfig.projbuild) 暴露 Ethernet，板实现按网络选项选择 `EthernetBoard` 或 `WifiBoard`。
3. **静态接线已确认，当前编译和实机状态未确认。** 本机无已激活 `IDF_PATH`/`idf.py`，没有对 HEAD 运行固件构建。以 HEAD 变更文件模拟现行 IDF 6.1 CI 选择，得到 18 项，其中 P4 NANO Rev1 的 Ethernet 路径被选中；P4X NANO Ethernet 和 NANO 默认 Wi-Fi 不在这次选择内。GitHub 当次实际作业结果未在本次审计中读取。PHY 链路、DHCP、音频和显示需要目标板实测。[CI 选择清单](scripts/ci/representative-variants.json)、[CI 工作流](.github/workflows/build.yml)
4. 历史证据需按日期解释：在 `4a5d446` 删除前的 `docs/esp-idf-6-migration.md` 记载过 **157 个旧矩阵变体在 IDF 6.0.1 上通过 GitHub Actions**；那是 2026-07 的旧矩阵，不证明当前 183 个默认变体、HEAD 以太网修改或硬件行为。可用 `git show 4a5d446^:docs/esp-idf-6-migration.md` 读取原记录。
5. 迁移仍有功能缺口：[ESP VoCat 电容滑条/按键](main/boards/espressif/esp-vocat/esp_vocat.cc) 在 IDF 6 下被条件编译关闭，对应[组件规则](main/idf_component.yml)和[CMake 规则](main/CMakeLists.txt)也仅放行 IDF 5；这不影响它的显示触控路径。仓库仍有个别 IDF 5 时代的板级说明和条件分支，应以当前根 README、组件清单和板型实际要求为准。

## 构建、测试、CI 与开发环境

- 开发需 Git、Python 3、网络可达的 ESP-IDF 依赖源，并 `source /path/to/esp-idf/export.sh` 激活 IDF；优先用 **v6.1**，`idf.py --version` 核对环境。顶层 [CMake](CMakeLists.txt) 使用 IDF 的最小组件构建，`main/CMakeLists.txt` 选板源和资产，[sdkconfig.defaults](sdkconfig.defaults) 及各芯片默认文件、[分区表](partitions/v2/README.md) 决定目标配置。依赖通过 IDF Component Manager 解析；[dependencies.lock 被忽略](.gitignore)，清单有版本范围及 `*`，联网重新解析可能得到不同依赖组合。ESP-HI 的部分素材也会在构建期下载。[组件清单](main/idf_component.yml)
- 板型枚举：`python3 scripts/build.py --list-boards`；未激活 IDF 时脚本按 6.0.2 回退列举，因此不能据此判断 6.1 全矩阵。单变体规范构建：`python3 scripts/build.py <board-directory> --name <variant-name>`，需要 Ethernet 时传对应 `--build-options-json`。构建脚本会更改 `sdkconfig` 和 `build/`，切换芯片或变体后不能把旧构建目录当成新目标的证据。[构建脚本](scripts/build.py)
- [唯一的 GitHub Actions 工作流](.github/workflows/build.yml) 在 push/PR 时先跑 `scripts/tests`，共享变更构建 18 个代表性选项并加入直接修改的板型；手动运行覆盖完整配置矩阵并额外纳入 Ethernet 选项。每项会合并固件并上传 `merged-binary.bin`。这只是构建验证，不含实体设备测试。独立的 [Docker firmware-builder 测试](docker/firmware-builder/test_firmware_builder.py) 尚未纳入该工作流。
- **本次本地验证：** `scripts/tests` 98/98 通过；`docker/firmware-builder` 10/10 通过。此主机只有 `python3`，没有 `python`；原样运行前者时 6 个 `WorkflowDiffTests` 因工作流 shell 调用 `python` 而以 127 报错。用 `/tmp` 临时提供指向 `/usr/bin/python3` 的 `python` 命令后，98 项通过；没有修改仓库代码。测试中的“多变体需指定名称”、资产超限、LILYGO 未带版本名的歧义日志是预期测试输出，不是这次测试失败。本机未构建固件、未刷机、未作硬件测试。

## 未完成工作、已知问题与风险

| 项目 | 依据与现状 | 建议验证或处理 |
| --- | --- | --- |
| 最新 Ethernet 迁移 | HEAD 静态改动已接上 IP101；无本次固件编译、网络链路或 P4 两代硅片实测。 | 优先编译 P4 NANO Rev1/P4X 的 Ethernet 与默认 Wi-Fi；对实际板验证链路、DHCP、重连、音频及显示。 |
| 单麦与软件参考 | [2026-09 音频审计](docs/audio-codec-input-audit.md) 记载 Box Lite 与 T-CameraPlus-S3 当时被依赖配置阻断，S31 Korvo 当时完成过特定 6.1 beta 构建；Box Lite 软件参考时序/并发、两款 LILYGO 的参考来源未实机确认。这是历史快照，不是本次重测。 | 重新编译受影响板型，验证采集、播放、唤醒/VAD、打断、重连及适用的 AEC 模式，再决定是否改代码。 |
| ESP VoCat IDF 6 降级 | 电容滑条/按键路径仍被版本条件关闭。 | 等兼容依赖并在真实硬件上验证后恢复。 |
| 明确占位实现 | [ML307 节能级别](main/boards/common/ml307_board.cc) 仍是 TODO/no-op；[Zectrix 睡眠管理兼容层](main/boards/zectrix/zectrix-s3-epaper-4.2/sleep_manager_compat.h) 也是 no-op；Korvo 的部分播放按键回调仍输出 TODO。 | 有相关板型需求和硬件时分别立项。 |
| 文档与矩阵漂移 | [README](README.md) 仍写 138 板目录/171 变体、芯片清单漏 S31；[自定义板型指南](docs/custom-board.md) 的字体/表情示例仍用旧名称，与[当前 CMake](main/CMakeLists.txt) 不一致。两个 Alientek `config.json` 有空 `builds`，不计入上述有效变体。 | 在单独文档阶段更新计数和例子；新增板应参考现有可构建板块。 |
| 构建可复现性 | `dependencies.lock` 不进 Git，部分依赖是版本区间或通配符；组件注册表和构建期资源下载是外部条件。 | 记录实际 IDF/组件解析版本与 CI run；需要严格复现时再设计锁定方案。 |
| 硬件覆盖 | Git 历史有旧矩阵构建通过记录，当前无完整 183 变体成功记录和实机测试总表。 | 先拿到当前完整矩阵结果，再按芯片/网络/音频/显示/相机代表板做 smoke test。 |

文档入口：根 [README](README.md)、[中文 README](README_zh.md)、[日文 README](README_ja.md)；`docs/` 中的[板型指南](docs/custom-board.md)、[代码风格](docs/code_style.md)、[WebSocket](docs/websocket.md)、[MQTT/UDP](docs/mqtt-udp.md)、[MCP 交互](docs/mcp-protocol.md)、[MCP 用法](docs/mcp-usage.md)、[BluFi](docs/blufi.md)、[glyph push](docs/glyph-push.md)、[通知](docs/notify.md)、[音频输入审计](docs/audio-codec-input-audit.md)；`docs/v0`、`docs/v1` 主要是板型图片。相关操作细节还在[音频设计](main/audio/README.md)、[分区说明](partitions/v2/README.md)、[Docker 构建器](docker/firmware-builder/README.md)以及 `scripts/` 下的资产工具 README。部分协议文档自述需与当前源码交叉核对。

## 推荐下一步与恢复操作

1. **先取得用户对本交接和下一阶段优先级的确认。** 建议首选 HEAD 的 P4 NANO Ethernet：准备 IDF 6.1 和两代目标板，编译 Ethernet/默认 Wi-Fi 路径并实测，记录具体硬件修订、组件版本与结果。此处是建议，尚未开始开发。
2. 后续按风险安排完整 CI 矩阵、Box Lite/T-CameraPlus-S3 音频回归、ESP VoCat 功能缺口和文档漂移；任何“已修复/已验证”的结论都要有对应命令、CI 记录或硬件记录。
3. 恢复项目时先在本仓库执行 `git status --short --branch`、`git remote -v`、`git rev-parse HEAD`、`git log --oneline -30`；确认远端状态并读本文件、[AGENTS.md](AGENTS.md)、目标子系统文档和最近目标文件提交。保持工作区改动，更新代码只用非破坏性 Git 操作。
4. 激活适用的 ESP-IDF，检查 `idf.py --version`，用 `scripts/build.py --list-boards` 找准确板目录/变体。再运行与改动相称的主机测试、代表性固件构建及必要实机验证。对协议共用语义核查两传输，对音频覆盖采集/播放/唤醒/打断/重连。
5. **每完成一个明确阶段**：记录验证及仍未验证的范围 → 更新本文件 → `git commit` → `git push origin` → 对照本地 HEAD 与远端 `main` 确认推送成功。关键状态必须留在 Git 与本文件，不只留在对话里。
