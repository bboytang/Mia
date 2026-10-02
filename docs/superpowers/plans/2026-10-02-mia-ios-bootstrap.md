# Mia iOS Bootstrap Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在 Mia 仓库建立可通过 GitHub Actions 编译的独立 iPhone SwiftUI 工程。

**Architecture:** 使用 XcodeGen 从受版本控制的 `ios/project.yml` 生成 Xcode 工程。最小 SwiftUI App 只提供中文启动页；macOS runner 编译模拟器与未签名真机 App，上传构建产物。现有 ESP32 CI 不改动。

**Tech Stack:** SwiftUI、XcodeGen、Xcode、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-10-02-mia-ios-design.md`

## Global Constraints

- iOS 17.0 起，仅支持 iPhone；界面文字使用简体中文。
- 不更改 `main/`、ESP-IDF 依赖或现有 ESP32 工作流。
- 不将服务器密钥、Apple 签名材料或第三方角色模型提交到仓库。
- 构建产物必须明确标记为未签名；GitHub 编译通过不等于真机可安装。

## Review Focus

- 构建产物是否包含正确的 `.app`，IPA 包结构是否为 `Payload/Mia.app`。
- CI 是否在仅有 iOS 相关改动时运行，且不触发完整 ESP32 手动矩阵。
- 麦克风权限描述是否随应用包生成。
- XcodeGen 生成的 Bundle ID 与部署版本是否符合配置。
- 未签名产物是否明确告知用户必须自行签名。

---

### Task 1: 工程与构建基线

**Files:**
- Create: `ios/project.yml`
- Create: `ios/MiaApp/MiaApp.swift`
- Create: `ios/MiaApp/ContentView.swift`
- Create: `.github/workflows/ios.yml`
- Modify: `.gitignore`
- Create: `ios/README.md`

**Interfaces:** 无前置代码接口；产出 `Mia` Xcode scheme 与 `ios/project.yml` 配置文件。

- [ ] 建立 XcodeGen 工程定义和最小中文 SwiftUI 页面。
- [ ] 在 macOS runner 上安装 XcodeGen、生成工程并编译 iOS Simulator 与 iPhoneOS。
- [ ] 将未签名 iPhoneOS `.app` 包装为可重签 IPA，上传 `.app` 和 IPA artifact。
- [ ] 检查 workflow YAML、项目配置与 Git diff。
- [ ] 推送功能分支并读取 GitHub Actions 结果；失败时修正再验证。

### Task 2: 后续实施切片

语音协议、音频、服务器、字幕和 Live2D 分别编写后续实施计划。每个切片均有独立可验证产物，不将外部服务和角色模型的缺失误报为客户端完成。
