# Youmi iPhone 客户端

客户端使用 SwiftUI，提供语音对话、实时活动、系统快捷动作、记忆与情绪管理，以及玻璃流体和蓝金星环皮肤。

| 目录 | 内容 |
| --- | --- |
| `YoumiApp/` | App、音频、连接、授权、设置与界面 |
| `YoumiActivity/` | 锁屏与灵动岛扩展 |
| `YoumiShared/` | App 与扩展共用的活动和快捷动作 |
| `YoumiTests/` | 单元与协议集成测试 |
| `YoumiUITests/` | 原生界面测试 |
| `TestsSupport/` | 本地协议测试夹具 |

最低 iOS 17。安装 XcodeGen 后，在本目录执行：

```sh
xcodegen generate
xcodebuild -project Youmi.xcodeproj -scheme Youmi -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build
```

构建、测试、设备打包与预览由 [iOS 工作流](../.github/workflows/ios.yml) 执行。实际交付和真机状态见[当前交接](../docs/youmi/handoff.md)及[客户端交接](../docs/youmi/ios/ios-handoff.md)。

[路线图](../docs/youmi/ios/ios-roadmap.md) · [安装包交付](../docs/youmi/ios/ios-secure-delivery.md) · [历史版本记录](../docs/youmi/history/ios.md)
