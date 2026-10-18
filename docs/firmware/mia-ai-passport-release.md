# Mia AI Passport：安装包与小智原生 OTA

当前实现以本文为准；[第一阶段架构记录](mia-ai-passport.md)保留早期方案与差异审计。

用户确认：先用现有 HTTP/WS；OTA 直接由原小智后端管理；iPhone 不承担 OTA；
不要求完整 Flash 备份；首次实际刷机仍必须等待用户明确确认。固件源码不含设备
密钥、Wi-Fi 密码或服务器凭据。没有修改生产部署，没有执行设备写入或全片擦除。

开发构建命令（先启用 ESP-IDF 6.1 环境；编译不授权设备写入）：

```sh
python scripts/build.py folotoy/ai-passport --name mia-ai-passport --language zh-CN
```

## 已实现与仍需确认

- 复用原 AI Passport 的 ST7789、ES8311、ADC 按键和省电驱动；没有测试/启动菜单。
- 新构建名 `mia-ai-passport`，固件版本 `1.0.0`；上报的 **board.type 为
  `mia-ai-passport`**。`mia-ai-passport-dev` 也使用这一独立型号。原 `ai-passport`
  配置不变。原 manager 按 type 匹配 OTA，因此不能只改 BOARD_NAME。
- 两个 3MiB 槽，保护历史 cardid、Recovery、完整 NVS/PHY；资源 640KiB，使用
  14px 中文字库。是否适合实机显示仍需验证。
- 保持小智发现、激活、设备认证和 WS/Opus 语义；发现响应限制 16KiB，绑定后
  使用下发 token。Wi-Fi 保留 BluFi 传输；Mia iPhone 专属 BLE 配置/绑定界面仍未实现。
- 固件升级接入原 OTA version/url 响应和 `self.upgrade_firmware` MCP 入口。
  仅接受同一配置源下原 manager/单模块下载路径；禁止重定向、任意 URL、路径穿越。
- 签名、SHA-256、芯片/版本/分区/资源校验、备用槽写入、启动确认、失败回滚和
  持久状态均已有实现。资源在线更新仍禁用，避免 app 回滚后资源不兼容。
- 未完成实机音频、显示、BLE、首次安装、实际断电、双向 OTA 和回滚验收。
  软件构建与模拟故障测试不能证明这些硬件场景成功。

## 为什么首次出包还需要只读检查

**不需要整片备份。** 但最新 BSP 已删除身份/Recovery 声明，不能由最新模板推断
出厂设备布局。首次分段包需要实机的 4KiB 分区表、芯片/Flash 容量、硅片版本及
secure boot/Flash encryption 状态。这些检查不读取设备密钥、NVS 或 Wi-Fi 数据。

在实际连接设备的 USB 主机上，安装 esptool 5+ 后执行：

```sh
python -m scripts.passport.inspect_device --port /dev/ttyACM0 --output /private/path/passport-inspection
```

端口按实际平台替换。工具只执行 `flash-id`、`get-security-info` 和
`read-flash 0x8000 0x1000`，不会发出 write/erase/burn 命令。可能重启设备并暂留
下载模式，完成后可重新上电。产出 `partition-table.bin`、`device-review.json`、
`readonly-probe.log`。不自动把任何检查标为批准；输出目录拒绝复用，避免混用设备。
这不是 Android USB 驱动支持声明：Android 工具能否读指定区间、分段写和读回校验
仍需在平板上确认。不能把普通 Chrome Web Serial 或某个 BLE 小程序当成已验证方案。

目前打包工具自动支持历史契约：NVS `0x9000+0x6000`、PHY `0xf000+0x1000`、
factory `0x10000+0x300000`、cardid `0x356000+0x4000`，可带 Recovery 声明。
即使表中省略 Recovery，仍保护 `0x700000+0x100000`。其它布局、启用/未知的芯片
安全状态一律拒绝自动打包，需单独审查，不能假定未知区域为空。

核对报告后，工程审核记录 `identity_regions_reviewed=true`、
`recovery_boot_change_noted=true`，其它实测信息和分区表 SHA-256 必须匹配。
这表示身份保留范围与 bootloader 变化已被说明，**不表示用户已授权实际刷机**。

## 固定候选分区及分段安装

| 区域 | 地址 | 大小 | 安装动作 |
| --- | ---: | ---: | --- |
| IDF6 bootloader | `0x0` | 以构建为准，须小于 `0x8000` | 更换；无多固件菜单 |
| partition table | `0x8000` | `0x1000` | 更换 |
| NVS | `0x9000` | `0x6000` | 保留，不清空 |
| PHY | `0xf000` | `0x1000` | 保留 |
| otadata | `0x10000` | `0x2000` | 仅首次初始化为 FF |
| app A | `0x20000` | `0x300000` | 首次写入新 app |
| cardid | `0x356000` | `0x4000` | 原字节保留，readonly |
| app B | `0x360000` | `0x300000` | 首次不写；后续 OTA 备用槽 |
| assets | `0x660000` | `0xa0000` | 首次写入并初始化整个 FF 尾部 |
| Recovery | `0x700000` | `0x100000` | 原字节保留，不打包替换数据 |

更换 IDF6 bootloader **不保留原厂 UP 五秒 Recovery 启动 hook**；保留 Recovery
字节不等于仍能从原小程序恢复。主应用地址也与旧 Recovery 安装契约不同，不使用
原小程序安装这个布局。此变化必须在首次刷机审核时明确说明。

生成经过设备检查约束的分段审核包：

```sh
python -m scripts.passport.package_release \
  --build /private/path/verified-build \
  --device-table /private/path/passport-inspection/partition-table.bin \
  --device-review /private/path/passport-inspection/device-review.json \
  --private-key .private/passport-signing/release-key.pem \
  --sequence 1 --output /private/path/mia-passport-1.0.0-review.zip
```

缺少真实读取的表或安全审核就拒绝出包。不会用合成测试表代替实机表。
打包时解析 ESP 段结构，检查芯片、8MB 镜像头、硅片版本、XOR checksum 和附加
SHA-256；核对应用实际嵌入的签名公钥；签名后再验证；逐段检查擦除扇区也不与
保护区域重叠。最终包含 `flash-plan.json`（文件、偏移、长度、SHA-256、擦除范围）、
`usb/` 分段、`ota/` 签名文件、公钥及说明，不包含私钥、身份数据或 merged 镜像。
已有包不被覆盖，`flash_authorized` 始终为 false。此工具本身没有串口写入功能。

首次安装时只使用 flash-plan 中的 USB 分段。不得把 OTA 胶囊或 merged 文件从
`0x0` 写入；不得启用全片擦除。安卓刷机工具需支持这些分段和写后读取校验，
并核实 cardid/Recovery 保留；能力不足先停在只读阶段。用户确认具体审核包后才
执行写入。首次配置后需完成真实语音握手，A 槽才会成为后续 OTA 的已确认基线。

## 安卓平板官网页面操作（等待设备检查及首次确认）

用户提供并已审计的入口为
[FoLoToy 官网刷机页](https://ai-passport.folotoy.cn/tools/web-flasher/)。
2026-10-18 读取的实际 `WebFlasher-Bmc0ckqe.js` 支持最多八个本地 `.bin`、逐个
填写地址，调用 `writeFlash` 时 `eraseAll:false`、`flashMode/flashFreq/flashSize:keep`，
并提供 MD5 写后核验。页面另有单独 `eraseFlash` 操作，**不要点击“清除设备数据”**。
页面会更新，这些源码检查不能替代平板实际连接或设备读取验证。

1. 平板以 Chrome 打开上述 HTTPS 页面，数据线/OTG 连接已开机设备，点击
   “连接设备”，选择 `USB JTAG/serial debug unit`。仅连接不代表已授权写入。
2. 当前页面没有导出 4KiB 分区表或完整芯片安全状态的控件，因此目前只连接并保存
   非敏感连接日志；不要用“直接刷入官方固件”替代实机分区检查。服务器上的 Python
   工具无法通过网页访问平板 USB。仅有这个页面时，实机只读检查路径仍未打通。
3. 检查通过、取得最终 `flash-plan.json`，且用户明确批准首次写入后，解压审核包。
   在“选择本地固件”中加入 **`usb/` 内的五个文件**。不要选择 `ota/` 中的文件。
4. 逐项手动填写地址：bootloader `0x0`、partition-table `0x8000`、
   otadata-initial `0x10000`、mia-ai-passport `0x20000`、assets `0x660000`。
   页面按添加顺序提供的默认值只适合常见三段布局，**不能依赖默认地址**。
5. 逐项与包内偏移、大小和 SHA-256 对照。先使用页面默认 `115200` 波特率，
   在以上前提全部满足后才点击“开始写入”。保持供电，等待每段校验完成和重启。
6. 首次配置及绑定后，实际验证显示、按键、麦克风和扬声器，建立已确认 A 槽；
   再由原小智后台测试下一版签名 OTA、断网重试及启动失败回滚。

以上是审核后的操作流程，不表示当前已具备可安全写入的最终包；没有实机表和安全
状态时不指导点击开始写入，也不以官网默认整包覆盖方式填补信息缺口。

## 原小智后台如何发布后续升级

源码审计基线为 `xiaozhi-esp32-server v0.9.7`，提交
`87c6df77b0220ddbd8fc804f984f83f69f3225e5`，未改生产实例。

- 全模块部署：`OTAMagController` 允许上传 `.bin`，按文件原字节存储/分发；
  `DeviceServiceImpl.checkDeviceActive` 只给已绑定且开启自动更新的设备返回新版，
  按 `board.type` 匹配，URL 为 `/xiaozhi/otaMag/download/<uuid>`，最多下载三次。
  使用**已有固件管理页面**，必要时在原固件类型字典登记 `mia-ai-passport`。
- 单模块部署：沿用 `data/bin/mia-ai-passport_<版本>.bin` 和
  `/xiaozhi/ota/download/<文件名>`。当前用户是原 manager 架构，不能另开单模块服务。
- 后台上传的是 `ota/mia-ai-passport_<版本>.bin` 签名胶囊，而非 USB app 或 merged。
  两种下载接口都原样分发文件，不需要第二个 manifest 下载端点或新后端。
- 设备启动检查原发现接口；如后台通过已有 MCP 管理能力调用
  `self.upgrade_firmware`，也进入相同签名引擎，耗时操作跑独立 worker。
  **不声称仅发布版本就会向所有在线设备即时推送**；后台实际触发能力仍需联调。
- `self.firmware.get_status` 通过原 MCP 返回 confirmed/downloading/trial/failed/
  interrupted/rolled_back 等状态及序列。没有新增 iPhone 页面，也未修改后台页面；
  后台能否直接展示该工具结果，需使用当前部署实际验证。

后续每次发布先更新专用配置中的 `CONFIG_APP_PROJECT_VER`，例如 `1.0.1`，构建后
用同一私钥签名，`sequence` 严格递增（首版 1，下一版 2）。后台版本号必须与
镜像内版本相同。普通发布不重新生成密钥、不更新分区表和 assets、不触碰 cardid。

```sh
python -m scripts.passport.sign_release \
  --app /private/path/build/xiaozhi.bin \
  --partition-table /private/path/build/partition_table/partition-table.bin \
  --assets /private/path/build/generated_assets.bin \
  --private-key .private/passport-signing/release-key.pem \
  --sequence 2 --output /private/path/mia-ai-passport_1.0.1.bin
```

签名工具还输出版本清单和校验值。初始 `1.0.0/sequence=1` 与设备自带版本相同，
用作发布基线，不是要求设备重新安装同版本。版本或序列没有增加时，设备拒绝升级。

## 签名文件与失败恢复

MIAOTA1 v1 文件是 **256 字节签名头 + 原 ESP app**，不是可 USB 烧录的 ESP 镜像。
前 192 字节是固定小端格式：magic/schema、应用大小、发布序列、8MB Flash、C3
chip id、保留位、32 字节板型、32 字节版本、应用/分区表/资源 SHA-256；随后是
64 字节 P-256 ECDSA `r||s`，签名前 192 字节的 SHA-256。固定布局避免 JSON
重排或重复字段歧义。分区表按 4KiB FF 补齐、资源按 640KiB FF 补齐后计算哈希。

发布公钥在 `main/passport/release_public_key.h` 及 `.pem`。本次新建的私钥位于
`.private/passport-signing/release-key.pem`，目录 0700、文件 0600，被 Git 忽略，
不进入 CI、代码、安装包或聊天。请将它在受保护位置长期保管；丢失它将无法给
已安装的设备发布同信任链 OTA。`create_signing_key.py` 只用于新产品信任根，拒绝
覆盖现有公钥，不能当作每次发布步骤。

下载头必须先通过签名、递增版本/序列、型号、当前布局/冻结资源及实际 ESP image
header/app descriptor 检查，随后才擦写备用槽。HTTP 可沿用当前原服务；真实性
依赖固件固定公钥，不依赖服务的 MD5。支持 HTTPS 并验证证书，但暂不强制迁移 TLS。
HTTP 的保密性及可用性仍不由签名提供。禁止任何跨源/降级重定向和 URL 凭据。

总下载限时五分钟，单次网络操作限时十五秒；超长、短读、断网、写入错误均中止。
第一版不做持久断点续传，重新领取 URL 后从备用槽起点重新下载。使用固定小缓冲，
不会占用主循环执行下载；写完从 Flash 读回计算 SHA-256，再 `esp_ota_end`，之后
才记录 trial 和设置新启动槽。复位时 downloading 标为 interrupted，不选半镜像。

试运行时 120 秒健康期限从 app 入口、板级初始化之前开始；NVS、显示/codec
初始化、有效采样率及带设备 token 的 WS hello 完成后确认。离线/初始化失败会
回滚，不用一次 OTA HTTP 200 确认镜像。第一次 USB 安装没有旧 Mia app，不能
宣称可自动回到原厂固件；只有建立已确认的 A 槽后，A/B 失败回滚才有基线。
物理麦克风/扬声器/屏幕是否正常仍需人工实测，握手不等于硬件录放音验收。

## 验证与证据边界

host 测试直接编译实际 `capsule.cc`、`crypto_psa.cc` 和 `signed_update.cc`。
ESP/HTTP/NVS/Flash/timer 接口为测试桩，PSA 边界由 OpenSSL 实现以验证真实签名与
哈希；不冒充 ESP 芯片运行。覆盖签名/型号/布局/资源损坏、重放、低电量、错误芯片
及硅片版本、短读/多读/超时、写失败、Flash 哈希错误、IDF end/boot 失败、试运行
超时回滚、确认后迟到的 timer、首次 A 槽确认和断电状态恢复。IDF6 PSA 本身在 CI
做真实编译，硬件 crypto、Flash 原子性、watchdog 和掉电仍需实机验证。

CI 另验证真实编译出的 ESP checksum/SHA、应用和资源大小，构建 dev/release、原
AI Passport、C3 OLED、S3 无屏。工程输入 artifact 不是首次安装包，没有 flash plan；
仅用于本地签名与审核后的打包，私钥不发送到 CI。没有实机只读数据时不生成最终
供用户直接烧录的分段包，也不以构建成功代替设备安全审核。
