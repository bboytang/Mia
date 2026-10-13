import SwiftUI

struct MiaMemoryView: View {
    @ObservedObject var session: MiaVoiceSession
    @State private var snapshot: MiaMemorySnapshot?
    @State private var working = false
    @State private var error: String?
    @State private var editing: MiaMemoryRecord?
    @State private var content = ""
    @State private var clearRequested = false
    @State private var resetRequested = false

    var body: some View {
        List {
            Section {
                Text("Mia 会提炼重要内容，敏感记忆需你确认。使用云端模型时，相关记忆会随聊天请求发送给模型服务。")
                    .font(.footnote)
                if let snapshot {
                    Toggle("自动记住重要内容", isOn: Binding(
                        get: { !snapshot.paused },
                        set: { enabled in Task { await perform("pause", fields: ["paused": !enabled]) } }
                    ))
                }
                Button("刷新") { Task { await perform("list") } }
            }
            if let error { Section { Text(error).foregroundStyle(.orange) } }
            if let snapshot {
                Section("记忆（最新 200 条）") {
                    if snapshot.memories.isEmpty { Text("还没有长期记忆") }
                    ForEach(snapshot.memories) { memory in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(memory.content)
                            if !memory.source.isEmpty {
                                Text("依据：" + memory.source).font(.caption).foregroundStyle(.secondary)
                            }
                            if !memory.confirmed {
                                Text("等待确认，不用于回答或性格成长").font(.caption).foregroundStyle(.orange)
                            }
                            HStack {
                                Button("修改") { editing = memory; content = memory.content }
                                if !memory.confirmed {
                                    Button("确认记住") {
                                        Task { await perform("update", fields: ["id": memory.id,
                                                           "content": memory.content, "confirmed": true]) }
                                    }
                                }
                            }.buttonStyle(.borderless)
                        }
                        .swipeActions {
                            Button("忘掉", role: .destructive) {
                                Task { await perform("delete", fields: ["id": memory.id]) }
                            }
                        }
                    }
                }
                Section("性格成长 · 第 \(snapshot.personality.version) 版") {
                    if snapshot.personality.traits.isEmpty {
                        Text("性格会在多次相处后逐渐形成，不会因一句话突然改变。")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    ForEach(snapshot.personality.traits) { trait in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(trait.name).font(.headline)
                            Text(trait.description)
                            ForEach(snapshot.memories.filter { trait.evidenceIDs.contains($0.id) }) { memory in
                                Text("成长依据：" + memory.content)
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    Button("恢复基础性格", role: .destructive) { resetRequested = true }
                }
                Section {
                    Button("清空全部记忆与成长", role: .destructive) { clearRequested = true }
                }
            }
        }
        .disabled(working)
        .overlay { if working { ProgressView() } }
        .navigationTitle("记忆与成长")
        .task {
            MiaConversationController.shared.stop()
            await perform("list")
        }
        .sheet(item: $editing) { memory in
            NavigationStack {
                Form { TextEditor(text: $content).frame(minHeight: 160) }
                    .navigationTitle("修改记忆")
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) { Button("取消") { editing = nil } }
                        ToolbarItem(placement: .confirmationAction) {
                            Button("保存") {
                                let updated = content
                                editing = nil
                                Task { await perform("update", fields: ["id": memory.id, "content": updated]) }
                            }.disabled(content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || content.count > 500)
                        }
                    }
            }
        }
        .confirmationDialog("清空后无法撤销", isPresented: $clearRequested, titleVisibility: .visible) {
            Button("清空全部记忆与成长", role: .destructive) { Task { await perform("clear") } }
        } message: { Text("服务器备份中的历史数据需由管理员另行处理。") }
        .confirmationDialog("恢复基础性格？", isPresented: $resetRequested, titleVisibility: .visible) {
            Button("恢复", role: .destructive) { Task { await perform("reset_personality") } }
        }
    }

    @MainActor
    private func perform(_ action: String, fields: [String: Any] = [:]) async {
        guard !working else { return }
        working = true
        error = nil
        defer { working = false }
        do { snapshot = try await session.manageMemory(action: action, fields: fields) }
        catch is CancellationError { }
        catch { self.error = error.localizedDescription }
    }
}

struct MiaWakeGuideView: View {
    var body: some View {
        List {
            Section("声音唤醒") {
                Text("先在 Mia 点小球，完成设备绑定和麦克风授权。")
                Text("在系统「设置 → 辅助功能 → 声音快捷指令」中添加动作「开始与 Mia 聊天」，训练口令「你好，米娅」。")
                Text("如果后台启动受系统限制，改选「打开 Mia 开始聊天」。首次调用可能需要解锁或确认。")
            }
            Section("麦克风与灵动岛") {
                Text("Mia 待机和结束聊天后不录音；系统声音快捷指令会继续使用麦克风在本机识别口令。")
                Text("要完全停止口令监听，请在系统声音快捷指令设置中关闭此功能。")
                Text("后台录音需允许实时活动；灵动岛展示状态和表情，显示时长由系统决定。")
            }
            Section("当前验证边界") {
                Text("后台唤醒与锁屏停止仍需在你的手机验证。系统不允许后台启动时，可选「打开 Mia 开始聊天」。")
            }
        }.navigationTitle("声音唤醒")
    }
}
