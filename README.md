# Youmi

Youmi 是一套包含 ESP32 语音设备固件、iPhone 客户端和后端扩展的语音陪伴项目。

| 目录 | 内容 |
| --- | --- |
| [ios/](ios/README.md) | iPhone App、实时活动、语音与客户端测试 |
| [server/](server/README.md) | 后端性格、持续情绪、记忆、授权及管理界面 |
| [main/](main/) | ESP-IDF 固件、板级实现、音频、显示与协议 |
| [scripts/](scripts/) | 固件构建、资源生成和 CI 验证 |
| [docker/](docker/) | 固件构建容器 |
| [docs/](docs/README.md) | 使用说明、开发文档、当前交接与历史资料 |

开发状态从 [Youmi 当前交接](docs/youmi/handoff.md) 开始；硬件开发见[固件说明](docs/firmware/README_zh.md)。

固件推荐 ESP-IDF **6.1**，最低 **6.0.1**；不支持 5.x。每次构建只选择一个板型，使用 `python3 scripts/build.py --list-boards` 查找实际板型与变体。iOS 使用 XcodeGen 生成 `Youmi.xcodeproj`。

[中文](README_zh.md) · [日本語](README_ja.md) · [文档目录](docs/README.md)
