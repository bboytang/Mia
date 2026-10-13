import AppIntents

struct EndMiaConversationIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "结束与 Mia 聊天"
    static var description = IntentDescription("停止当前对话并释放 Mia 的麦克风，系统声音快捷指令由系统设置管理。")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult {
        #if MIA_WIDGET_EXTENSION
        // LiveActivityIntent is routed to the app's implementation by iOS.
        throw MiaIntentRoutingError.openApp
        #else
        MiaConversationController.shared.stop()
        #endif
        return .result()
    }
}

enum MiaIntentRoutingError: Error, CustomLocalizedStringResourceConvertible {
    case openApp
    var localizedStringResource: LocalizedStringResource { "请打开 Mia 结束对话。" }
}

#if !MIA_WIDGET_EXTENSION
@available(iOS 18.0, *)
struct StartMiaConversationIntent: AudioRecordingIntent, LiveActivityIntent {
    static var title: LocalizedStringResource = "开始与 Mia 聊天"
    static var description = IntentDescription("在后台开始与 Mia 的语音对话，不打开 App 界面。需先完成设备绑定、麦克风授权并允许实时活动；锁屏时不会开启 Mia 录音。")
    static var openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult {
        try await MiaConversationController.shared.startFromSystemAction()
        return .result()
    }
}

struct OpenMiaConversationIntent: AppIntent {
    static var title: LocalizedStringResource = "打开 Mia 开始聊天"
    static var description = IntentDescription("打开 Mia 并开始聊天，适用于系统不允许后台开始录音的情况。")
    static var openAppWhenRun = true

    @MainActor
    func perform() async throws -> some IntentResult {
        try await MiaConversationController.shared.startInForeground()
        return .result()
    }
}

@available(iOS 18.0, *)
struct MiaShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: StartMiaConversationIntent(),
                    phrases: ["开始与 \(.applicationName) 聊天"],
                    shortTitle: "开始聊天", systemImageName: "mic.fill")
        AppShortcut(intent: EndMiaConversationIntent(),
                    phrases: ["结束与 \(.applicationName) 聊天"],
                    shortTitle: "结束聊天", systemImageName: "stop.fill")
        AppShortcut(intent: OpenMiaConversationIntent(),
                    phrases: ["打开 \(.applicationName) 开始聊天"],
                    shortTitle: "打开并聊天", systemImageName: "bubble.left.and.bubble.right.fill")
    }
}
#endif
