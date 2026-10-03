# Mia iOS Protocol Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 让 iOS 客户端能够按小智 WebSocket 协议构造聆听命令并解析 Mia 语音状态。

**Architecture:** `MiaWireProtocol` 是不依赖网络或界面的 JSON 消息边界。测试直接验证生成的消息字段及解析结果，后续 WebSocket 会话层复用它。

**Tech Stack:** Swift、Foundation、XCTest、GitHub Actions macOS runner。

**Spec:** `docs/superpowers/specs/2026-10-02-mia-ios-design.md`

## Global Constraints

- 继续使用 WebSocket 版本 1、Opus 16 kHz 单声道 60 ms 上行参数。
- 用户语音的 STT 消息不得进入主界面字幕；解析器可识别它供内部流程使用。
- 未知服务器消息不得令整个会话崩溃。

## Review Focus

- 服务器 hello 的采样率缺失或无效时使用 24 kHz 默认值，不接受非正数。
- `tts` 的 `sentence_start` 只有字符串文本才生成 Mia 字幕事件。
- `listen` 控制消息带上服务器会话 ID，缺失时兼容现有空字符串行为。
- 未知消息类型仍可安全解析为 `other`。
- 解析失败应抛出明确错误，不让无效 JSON 进入状态更新。

---

### Task 1: 扩展消息契约

**Files:**
- Modify: `ios/MiaApp/MiaWireProtocol.swift`
- Modify: `ios/MiaTests/MiaWireProtocolTests.swift`

**Interfaces:**
- Produces: `MiaWireProtocol.startListening(sessionID:) throws -> Data`、`stopListening(sessionID:) throws -> Data`、`abort(sessionID:) throws -> Data`。
- Produces: `MiaServerEvent.ttsStart`、`.ttsStop`、`.userTranscript(String)`、`.emotion(String)`。

- [ ] 添加失败测试：发送 `listen/start/manual`、`listen/stop` 与 `abort` 的 JSON 字段。
- [ ] 添加失败测试：解析 TTS 开始/结束、用户 STT 和 LLM 情绪消息。
- [ ] GitHub Actions 运行测试，确认失败原因是缺失的新协议行为。
- [ ] 实现最小消息构造和解析代码。
- [ ] GitHub Actions 测试通过，确认模拟器与真机编译及产物上传。
