# Mia AI Passport：第一阶段实现与发布门禁（历史记录）

后续签名 OTA、原后端接入、免整片备份的只读检查与分段包规则，以
[当前安装与发布说明](mia-ai-passport-release.md)为准。下文保留第一阶段审计和早期方案。

本阶段提供可编译的专用开发配置、后端接入限制、只读审计工具和保留历史保护区的
8MB A/B 候选表。**不是可烧录交付，不是已完成的安全 OTA，不是实机验收。**
不得整片擦除，不发布合并镜像；首次 USB 写入必须取得设备所有者明确确认。
不修改生产部署，不新建后端，不在仓库保存真实设备密钥、Wi-Fi 密码或服务器凭据。

## 基线与差异审计

本地开始于 `2162fb4`，分支 `esp32-c`，工作树干净。
2026-10-18 只读取得两个上游：

| 来源 | 审计提交 | 结论 |
| --- | --- | --- |
| [专用小智固件](https://github.com/FoloToy/folo-ai-passport-xiaozhi/tree/72da544d1b51678f5d88967adc299b3aec956946) | `72da544` | 小智 2.5 系，要求 IDF >=6.0.1，推荐 6.1；只保留 Passport 板级实现 |
| [官方 BSP](https://github.com/FoloToy/ai-passport/tree/3d685a90bdb96dd8526d84edde1e63fec25b460e) | `3d685a9` | IDF 5.5.3 测试模板，不应搬入 Mia 的 6.1 工具链；当前默认单 factory 应用 |

Mia 已有同源的 `main/boards/folotoy/ai-passport/`：ST7789 240×320、ES8311、
CW2017、GPIO0 电阻梯按键。引脚与小智上游一致。复用现有协议、音频与 LVGL，
不导入 BSP demo 菜单、不创建第二个 `DECLARE_BOARD`。Mia 的板级实现有更完整的
省电/唤醒逻辑，不用上游较简版本覆盖。小智上游音频输入输出改成 16kHz；Mia
现有是 24kHz。本阶段不改采样率，待现有后端 hello 的实际采样率、重采样堆占用
及录放音测量后决定；C3 无 PSRAM，不能宣称支持 S3 AFE/AEC。

关键历史证据：[BSP `50fd39c` 分区表](https://github.com/FoloToy/ai-passport/blob/50fd39c/partitions.csv)
及同提交 `docs/development/ble-recovery-compatibility.zh_CN.md`：
`cardid@0x356000+0x4000`；`recovery@app/test@0x700000+0x100000`；
原厂 bootloader 按 UP 5 秒进入 Recovery，BLE 服务 FFF0–FFF4。
`52168b5` 删除 Recovery 声明，`0b6aed8` 又删除 cardid 并将 factory 扩至 Flash 末尾。
当前 CHANGELOG 仍称保留 cardid，与实际表不一致。**最新模板不代表出厂设备布局。**
这些历史地址需要保护，但不能保证已涵盖所有设备密钥或未知保留数据。

## 现有服务架构和地址

以 `docs/mia-companion-backend.md` 为准：现用自建 `xiaozhi-esp32-server v0.9.7`
及其原管理/认证/设备绑定；Mia companion 接原扩展点。`server/README.md` 内旧
独立网关记录不能作为新设备服务架构。

用户确认沿用 iPhone 当前地址，即 `ios/MiaApp/MiaXiaozhiClient.swift`：

- 发现/绑定：`http://43.143.230.174:8002/xiaozhi/ota/`
- 语音：`ws://43.143.230.174:8000/xiaozhi/v1/`

用户确认现阶段先用 HTTP/WS，专用开发 variant 已固定配置上述两个地址，
发现、激活和语音联调不再等待 TLS。固件仅接受配置中完全一致的地址，包括协议、
主机、端口和路径；HTTP/HTTPS、WS/WSS 均支持，但不会自动切换协议或回退公共服务。
配置为 HTTPS/WSS 时，HTTP/WS 响应仍被拒绝。缺少配置仍拒绝连接。
`CONFIG_MIA_PASSPORT_OTA_URL` 在此处是小智发现/激活接口，不代表允许 HTTP 下载固件。

目前凭据和语音会经明文链路传输。安全 OTA 发布方案仍保留 HTTPS 和签名验证要求，
现阶段应用与资源升级入口继续禁用，不会因为开放 HTTP 发现而开放未签名更新。
未来 TLS 地址可以通过同一配置替换；只配置地址，不包含 token。
尚未配置、访问或改动生产服务，不假定旧文档的 `8kraw.cloud` 已转发到当前自建小智。

发现保持原 `Device-Id`/`Client-Id`/激活协议；有效发现响应的 WebSocket 地址必须匹配
配置，写 NVS 前验证，不保存 MQTT 配置。语音握手继续使用服务下发的 Bearer，
保留原 hello、Opus、listen、abort、字幕/情绪语义。不复制 iPhone 的客户端 UUID
或 token 给新硬件，新设备需要由原 manager 授权绑定。
本阶段未完成真实后端认证联调，也未新增服务端固件管理 API。

用户已调整 OTA 管理范围：后续直接使用现有小智后端管理固件、发布版本和触发升级，
不开发 iPhone 固件升级入口、升级任务或结果页面。iPhone 仍用于配网、设备绑定和
日常配置；设备通过原后端获取升级信息、下载固件并上报结果。安全升级引擎仍需完成，
这一范围调整不代表已开放当前禁用的升级入口。

## 分阶段计划与验收

1. 架构与保护门禁（本次）：审计两个上游；独立构建 `mia-ai-passport-dev`；
   host 回归；测量实际 app 和资源大小；提交候选表及签名 OTA 设计。
2. 安全 OTA：实现签名清单、流式下载/哈希、兼容检查、故障处理、启动确认/回滚；
   接入原小智后端的固件管理与升级流程，将应用/MCP 升级入口统一到新引擎；
   模拟下载中断、断电、篡改、重放、启动失败，在原后端核对结果。
3. BLE/iPhone：复用 IDF6 BluFi 传输，增加短时物理确认、设备绑定和端点配置；
   iPhone 只承担配网、绑定和日常配置，不实现固件 OTA 管理。
4. 实机/首次安装：私有备份与迁移表审核，用户明确同意后生成分段签名发布包；
   安卓 USB 实测，A/B OTA 双向、断电、回滚、BLE、安全和音频/屏幕/电源全链路验收。

## 第一阶段已落地的限制

新增 release variant 复用相同引脚、Kconfig 板型和 CMake 映射；`BOARD_NAME` 为
独立 `mia-ai-passport-dev`，不复用原版本的 OTA 身份。主入口直接进入 Application，
没有测试菜单或多固件选择器。现有 LCD/表情与按键复用，Mia 专属美术界面尚未完成。
专用配置通过 `main/CMakeLists.txt` 选择已有 14px/1bpp 中文字库；保持图标与表情，
原 ai-passport 仍为 20px/4bpp。默认 20px 资源在 Actions 实测为 1,324,917 字节，
无法放入 640KiB 资源区；缩小字库以保留两个 3MiB 槽和历史保护区。可读性需实测，
后续如需更大文字，应审核专用压缩/子集字库，不能删掉身份区或 Recovery 腾空间。

- `main/passport/backend_policy.h` 为可 host 编译的端点匹配模块。
- `main/ota.cc` 仅此配置固定发现端点、拒绝被重定向的语音地址，过滤旧 firmware/MQTT。
- `main/protocols/websocket_protocol.cc` 在握手前再次检查，防止旧 NVS 注入地址。
- `main/application.cc` 此配置始终使用 WebSocket，避免默认 MQTT 回退。
- `main/main.cc` 此配置遇到 NVS 版本或损坏问题停止，禁止自动擦 NVS。
- `main/boards/common/blufi.cpp` 删除 Wi-Fi 密码日志。原 BluFi 不等于可信绑定；
  本阶段只启用现有配网能力，未实现手机配置/绑定，未宣称可直接与现有 iOS 客户端互通。
- 旧 URL-only 应用 OTA、MCP 直传 URL、资源下载均在该配置拒绝执行。
  当前发现即确认镜像的调用也被禁止；没有通过它假装完成启动健康确认。
- 已启用 IDF rollback 编译选项，但完整 trial boot 健康策略和结果上报尚未实现。

## 8MB 候选布局（不授权写入）

| 区域 | 偏移 | 字节数 | 用途 |
| --- | ---: | ---: | --- |
| bootloader/分区表 | `0x0` / `0x8000` | 以实际构建及原厂审计为准 | 迁移需审核 boot hook、大小和安全 eFuse |
| nvs | `0x9000` | `0x6000` (24 KiB) | 保留原 NVS 范围，禁止格式化 |
| phy_init | `0xf000` | `0x1000` | 保留 |
| otadata | `0x10000` | `0x2000` | 新 A/B 状态，覆盖旧应用头；首次迁移需审查 |
| ota_0 | `0x20000` | `0x300000` (3 MiB) | 应用 A |
| 未使用区 | `0x320000` | `0x36000` | 未知历史内容，不当成可写空白 |
| cardid | `0x356000` | `0x4000` | 历史身份区，readonly，不生成其镜像 |
| 未使用区 | `0x35a000` | `0x6000` | 同上 |
| ota_1 | `0x360000` | `0x300000` (3 MiB) | 应用 B |
| assets | `0x660000` | `0xa0000` (640 KiB) | 共用只读资源；本阶段禁用在线改写 |
| recovery | `0x700000` | `0x100000` (1 MiB) | 原厂 Recovery 原字节保留，不生成其镜像 |

总边界 `0x800000`。两个槽必须均容纳**最终签名格式**的应用，需保留签名/对齐
开销。当前 CI 应用未签名，容量只是初步可行性数据。单个共享 assets 不能随 app
独立更新，否则旧 app 回滚后可能不兼容；第一版冻结资源格式与内容，后续独立资源
升级须另外审核原子性。3MiB 槽或 640KiB 资源不足时构建必须失败，先优化资源；
若仍不可行，另提交独立 Recovery 方案审核，禁止单槽原地覆盖。

保留 Recovery 字节**不代表**替换后的 IDF6 bootloader 还能进入原厂 Recovery。
新表的主应用地址也与旧 Recovery 的 `0x10000` 安装契约不同，不能用原小程序
直接安装/更新此布局。无启动菜单不妨碍将来审核独立紧急恢复入口。
在确认原厂 bootloader hook、secure boot/加密状态及 Recovery 行为前，不承诺兼容。

## 安全 OTA 设计（下一阶段实现契约）

保持原小智发现/激活响应，优先复用现有小智后端的固件目录、版本发布、设备升级
触发与状态展示。先核对当前部署版本的实际实现，再对签名元数据、设备兼容性和
确认/回滚结果等缺口做最小扩展；不预先设计第二套管理 API 或独立升级服务。
不新增 iPhone OTA 功能。账号到设备归属和后台操作权限复用原认证/绑定，不能
信任请求中自报的 owner。设备只接受授权给自身的兼容升级，重复触发须幂等，
升级标识与结果关联方式需结合原后端确认。手机账号 token 不作为 Flash 中的长期设备密钥。

签名清单采用 envelope：精确 payload 字节（base64）和签名（base64）、key_id。
payload 为有严格上限的 UTF-8 JSON：schema、board=`mia-ai-passport`、chip=`esp32c3`、
flash_bytes=8388608、PSRAM=false、layout_id、partition_table_sha256、version、
release_sequence、image_size、image_sha256、HTTPS image_url、资源兼容版本及最小
硬件/bootloader版本。禁止重复键、未知必需语义和非整数大小/序列。

签名算法固定 ECDSA P-256/SHA-256，对原始 payload 字节验证，避免重新序列化歧义。
公钥离线固定在固件，key_id 仅选择已固定公钥；私钥离线/受控发布作业保管，不能
从响应下载公钥。签名覆盖 board、布局、序列与镜像 SHA-256，因而同时认证镜像。
完整 envelope/字段校验、签名验证和兼容检查均在擦除备用槽前完成。

安全顺序：

1. 验证任务归属与签名清单；HTTPS 证书链/主机名验证，禁止跨源/降级重定向、URL 凭据。
2. 核对 board/chip/revision/8MB/布局/资源/版本序列、镜像长度和备用槽容量；
   拒绝当前正在运行的槽及 cardid/Recovery，核对 ESP image header/app descriptor。
3. 独立低优先级 OTA task，固定小缓冲（例如 4KiB），下载写备用槽并计算 SHA-256。
   不阻塞主事件循环和音频任务；禁止并发写 Flash 的升级任务；检查电量/供电。
4. HTTP 错误、断网、短读、超长、超时、写失败均 `esp_ota_abort`，保留当前启动槽。
   第一版不持久断点续传：重试重新从 0 下载备用槽。断电留下的半镜像不得切换启动。
5. 精确长度与签名清单哈希一致后 `esp_ota_end` 验证 ESP 镜像，再持久记录任务 trial
   状态、设置备用启动槽并重启；不得先报告成功。SHA-256 本身不是真实性证明。
6. 新镜像在有界期限内验证 NVS、分区、音频路径、屏幕初始化及真实认证 WebSocket
   hello/协议启动；仅成功才 `esp_ota_mark_app_valid_cancel_rollback`。
   失败调用 rollback/reboot，崩溃/超时由 watchdog + IDF rollback 恢复旧 app。
   离线无法完成健康检查时按策略回滚，不以一次发现 HTTP 200 代替健康。
7. 旧 app/新 app 启动后依据 running partition、IDF image state 与持久任务记录上报
   confirmed/rolled_back/interrupted；原小智后端展示这些结果，不以下载 100% 视为成功。
   release_sequence 只在确认后提交，允许试运行失败回旧版本且防止已确认版本重放。

NVS schema 变更必须向后兼容；否则 A/B 回滚仍可能损坏原 app。首版不改设备身份
namespace。固件签名不能防物理攻击；secure boot/Flash encryption 与 eFuse 写入是
独立制造/迁移审核，本阶段不烧任何 eFuse。

## 私有只读备份与安卓 USB 路径

目前用户不清楚是否已有备份，应按没有备份处理。不要把备份上传 GitHub/CI/聊天，
其中可能包含身份、Wi-Fi 密码和设备密钥。首次写入前用支持 ESP32-C3 USB Serial/JTAG
和完整 8MB **读取**的工具保存两份独立读出的备份，比较 SHA-256；另记录不含密钥
值的芯片/Flash/eFuse 安全状态。若是加密表/未知表，审计工具拒绝继续，不做自动迁移。

本仓库提供的审计命令只读取本地文件，不会接触串口：

```sh
python -m scripts.passport.audit_flash /private/path/ai-passport-full-backup.bin
```

输出分区结构、备份与历史区域哈希和保护告警，不输出原始身份内容。
报告永远 `flash_authorized=false`；即使历史区域全 FF 或表中没声明也不自动授权。
实际 NVS/隐藏区/密钥位置仍需人工核实，工具不是密钥定位器。

安卓平板需 OTG 数据线和稳定供电；选用明确支持该 USB 设备、8MB 读取、分段写入、
写后读取校验且能关闭全片擦除的工具。不能假定普通安卓 Chrome 支持 Web Serial，
也不能把 FoLoToy BLE 小程序视为 Mia HTTPS OTA 客户端。若安卓工具不能完整备份或
分段校验，先停在读取阶段，改用可验证的 USB 主机方案。

最终经审核的首次包才列出 bootloader、分区表、应用、assets 各自文件/偏移/长度/
SHA-256、允许擦写的扇区及保护范围。每个分段的**擦除扇区**也不能覆盖保留区；
完成写入后读回比对，并确认保留区哈希未变。此文候选地址不是刷机指令。
由于未最终确认分区，本次不生成用户可直接烧录的文件、首次刷机校验清单或 OTA
发布清单。首次写入必须等待用户明确确认，当前授权仅覆盖开发/构建/只读分析。

## 验证与交付路径

```sh
python3 -m unittest discover -s scripts/tests -v
source /path/to/esp-idf-v6.1/export.sh
python scripts/build.py folotoy/ai-passport --name mia-ai-passport-dev --language zh-CN
python -m scripts.passport.build_report build
```

`partitions/mia-passport-8m-candidate.csv` 为可编译候选表，不能拿它刷机。
规范构建脚本会在隔离 CI 内部生成合并构建输出，但 CI 不上传任何 .bin 或刷机参数；
只上传含精确提交 ID 的容量报告。通用 Build Boards 工作流也禁止上传本开发 variant。
`build_report` 从实际生成的分区表、ESP32-C3 app header/IDF descriptor、app 与 assets
读取容量/大小/哈希。这个报告不是签名 release manifest。

host 测试覆盖端点限制的真实 C++ 编译执行、原厂/新版 BSP 表、MD5 损坏、缺失 MD5、
边界/重叠/标签/对齐错误、完整备份长度、候选保护范围、超容及错误芯片/SDK。
GitHub Actions 构建专用配置、原 ai-passport、xmini-c3 OLED 及 S3 atom-echos3r
无屏配置，覆盖本次条件编译和共用代码。仍需真实语音录放、打断、重连、表情、按键、BLE/iPhone互通、断电回滚和电量测试；
没有设备连接，任何 CI 成功都不代表这些实测成功。
