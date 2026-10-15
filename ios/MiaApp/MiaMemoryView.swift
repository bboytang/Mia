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
    @State private var events: [MiaEventList.Event] = []
    @State private var tracking: MiaEmotionTracking?
    @State private var enableTrackingRequested = false
    @State private var clearTrackingRequested = false
    @State private var editingObservation: MiaEmotionTracking.Observation?

    var body: some View {
        List {
            Section {
                Text("Mia 会提炼重要内容，敏感记忆需你确认。使用云端模型时，相关记忆会随聊天请求发送给模型服务。")
                    .font(.footnote)
                Text("每次回复后会在后台整理；“已接收”不等于“已保存”。刷新可查看已保存或等待确认的内容。")
                    .font(.footnote).foregroundStyle(.secondary)
                if let snapshot {
                    Toggle("自动记住重要内容", isOn: Binding(
                        get: { !snapshot.paused },
                        set: { enabled in Task { await perform("pause", fields: ["paused": !enabled]) } }
                    ))
                }
                if let task = session.memoryTask { Text(task.label).font(.footnote) }
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
                if snapshot.management?.supports("events") == true { eventSection }
                if snapshot.management?.supports("emotion_status") == true { trackingSection }
                Section {
                    Button("清空全部记忆与成长", role: .destructive) { clearRequested = true }
                }
            }
        }
        .disabled(working)
        .overlay { if working { ProgressView() } }
        .navigationTitle("记忆与成长")
        .task { await perform("list") }
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
        .confirmationDialog("启用长期情绪记录？", isPresented: $enableTrackingRequested, titleVisibility: .visible) {
            Button("启用") { Task { await perform("emotion_consent", fields: ["enabled": true]) } }
        } message: {
            Text("默认关闭。启用后记录聊天中关于你心情的观察，分析最近30天，最多保留90天。相关观察可能随请求发送给云端模型；可随时停用、更正或删除。这不等于心理诊断。")
        }
        .confirmationDialog("删除全部心情观察？", isPresented: $clearTrackingRequested, titleVisibility: .visible) {
            Button("删除观察", role: .destructive) { Task { await perform("emotion_clear") } }
        } message: { Text("删除已有观察，不会关闭当前的记录授权。") }
        .sheet(item: $editingObservation) { observation in
            NavigationStack {
                List {
                    Text(observation.sourceExcerpt)
                    ForEach(["positive", "negative", "neutral", "mixed"], id: \.self) { tendency in
                        Button(MiaEmotionTracking.tendencyLabel(tendency)) {
                            editingObservation = nil
                            Task { await perform("observation_update", fields: ["id": observation.id, "tendency": tendency]) }
                        }
                    }
                }.navigationTitle("更正当时的心情")
                    .toolbar { Button("取消") { editingObservation = nil } }
            }
        }
    }

    private var eventSection: some View {
        Section("互动记录（最新100条）") {
            if events.isEmpty { Text("还没有已记录的互动") }
            ForEach(events) { event in
                VStack(alignment: .leading, spacing: 4) {
                    Text(event.title)
                    if let source = event.userExcerpt, !source.isEmpty { Text("你说：" + source).font(.footnote) }
                    if let reply = event.assistantExcerpt, !reply.isEmpty { Text("Mia：" + reply).font(.footnote) }
                    Text("\(event.stateLabel) · 第\(event.version)版").font(.caption).foregroundStyle(.secondary)
                }.swipeActions {
                    Button("删除", role: .destructive) { Task { await perform("event_delete", fields: ["id": event.id]) } }
                }
            }
        }
    }

    private var trackingSection: some View {
        Section("长期心情记录") {
            if let tracking {
                Toggle("记录我的长期心情", isOn: Binding(
                    get: { tracking.consent.enabled == 1 },
                    set: { enabled in
                        if enabled { enableTrackingRequested = true }
                        else { Task { await perform("emotion_consent", fields: ["enabled": false]) } }
                    }
                ))
                Text("授权第\(tracking.consent.version)版。停用后停止采集和分析，已有观察仍可查看或删除。")
                    .font(.footnote).foregroundStyle(.secondary)
                if tracking.trend.status == "available" {
                    ForEach(["self_report", "inferred"], id: \.self) { kind in
                        if let group = tracking.trend.groups?[kind], !group.distribution.isEmpty {
                            Text("\(kind == "self_report" ? "你明确说过的" : "从表达推测的")：\(group.count)条，\(group.sessions)次会话")
                            Text(group.distribution.keys.sorted().map {
                                "\(MiaEmotionTracking.tendencyLabel($0))\(group.distribution[$0] ?? 0)条"
                            }.joined(separator: "、")).font(.caption)
                        }
                    }
                } else if tracking.consent.enabled == 1 {
                    Text("还不足以判断长期规律，需要至少5条观察、3次会话并跨7个自然日。")
                        .font(.footnote)
                }
                ForEach(tracking.observations ?? []) { observation in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(observation.sourceExcerpt.isEmpty ? "原始依据已移除" : observation.sourceExcerpt)
                        if observation.state != "active" {
                            Text("依据失效或未核实，不用于趋势").font(.caption).foregroundStyle(.orange)
                        }
                        Text("\(observation.sourceKind == "self_report" ? "明确自述" : "推测") · \(MiaEmotionTracking.tendencyLabel(observation.tendency)) · 置信度\(Int(observation.confidence * 100))%")
                            .font(.caption).foregroundStyle(.secondary)
                        Text(Date(timeIntervalSince1970: observation.observedAt).formatted(date: .abbreviated, time: .shortened))
                            .font(.caption).foregroundStyle(.secondary)
                        if observation.state == "active" {
                            Button("更正") { editingObservation = observation }.buttonStyle(.borderless)
                        }
                    }.swipeActions {
                        Button("删除", role: .destructive) { Task { await perform("observation_delete", fields: ["id": observation.id]) } }
                    }
                }
                Text("这里显示最新100条观察，不等于医学测量；Mia 的回复表情不作为你的心情记录。")
                    .font(.footnote).foregroundStyle(.secondary)
                Button("删除全部心情观察", role: .destructive) { clearTrackingRequested = true }
            }
        }
    }

    @MainActor
    private func perform(_ action: String, fields: [String: Any] = [:]) async {
        guard !working else { return }
        working = true
        error = nil
        defer { working = false }
        do {
            if action == "event_delete" {
                events = try await session.manageMemoryResult(action: action, fields: fields, as: MiaEventList.self).events
            } else if action.hasPrefix("emotion_") || action.hasPrefix("observation_") {
                tracking = try await session.manageMemoryResult(action: action, fields: fields, as: MiaEmotionTracking.self)
            } else {
                snapshot = try await session.manageMemory(action: action, fields: fields)
                try await session.refreshMemoryTask(latest: snapshot?.management?.supports("job_status") == true)
            }
            if snapshot?.management?.supports("events") == true {
                events = try await session.manageMemoryResult(action: "events", as: MiaEventList.self).events
            }
            if snapshot?.management?.supports("observations") == true {
                tracking = try await session.manageMemoryResult(action: "observations", as: MiaEmotionTracking.self)
            }
        }
        catch is CancellationError { }
        catch { self.error = error.localizedDescription }
    }
}

struct MiaWakeGuideView: View {
    @Environment(\.openURL) private var openURL

    var body: some View {
        List {
            Section("声音唤醒") {
                Text("先在 Mia 点小球，完成设备绑定和麦克风授权。")
                Text("在系统「设置 → 辅助功能 → 声音快捷指令」中添加动作「开始与 Mia 聊天」，训练口令「你好，米娅」。")
                Text("此动作应直接在后台开始对话，不打开 Mia 界面。需允许实时活动；锁屏时先解锁再呼叫。")
            }
            Section("动作列表里找不到 Mia") {
                Text("先打开「快捷指令」App，添加快捷指令，搜索 Mia 的「开始与 Mia 聊天」操作，保存为「呼叫 Mia」。再回到声音快捷指令，选择已保存的「呼叫 Mia」并训练口令。")
                Text("「呼叫 Mia」只添加「开始与 Mia 聊天」操作，不添加「打开 App」或「打开 URL」。如果快捷指令 App 也没有这项操作，当前版本的后台唤醒入口尚不可用。")
                Button("打开快捷指令") { openURL(URL(string: "shortcuts://")!) }
                Text("未添加动作和训练口令前，待呼叫状态不会响应「你好，米娅」。锁屏调用可能要求先解锁；解锁本身不会自动开始录音。")
            }
            Section("麦克风与灵动岛") {
                Text("Mia 待机和结束聊天后不录音；系统声音快捷指令会继续使用麦克风在本机识别口令。")
                Text("要完全停止口令监听，请在系统声音快捷指令设置中关闭此功能。")
                Text("后台录音需允许实时活动；灵动岛展示状态和表情，显示时长由系统决定。")
            }
            Section("没有呼叫也被唤醒") {
                Text("声音快捷指令由 iOS 识别，Mia 完全退出后系统仍能监听并调用动作。Mia 无法读取原始口令或调整系统识别阈值。")
                Text("在系统声音快捷指令中删除原口令，再在安静环境用正常说话音量训练较独特的长口令，例如「你好米娅，开始陪我聊天」。这只能尝试降低误识别，不能保证完全消除。")
                Text("同时检查快捷指令 App 的「自动化」是否有其他规则调用 Mia。可对照设置中的「系统开始动作次数」和「最近系统动作」确认是否收到系统调用；诊断只保存次数和时间，不保存录音。")
            }
            Section("当前验证边界") {
                Text("后台唤醒与锁屏停止仍需在你的手机验证。若动作失败或需要打开 Mia，后台直接唤醒未通过；不会自动切到前台代替。")
            }
        }.navigationTitle("声音唤醒")
    }
}
