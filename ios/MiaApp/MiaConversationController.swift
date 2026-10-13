import ActivityKit
import AVFoundation
import Combine
import UIKit

enum MiaConversationStartError: LocalizedError {
    case locked, microphonePermission, liveActivitiesDisabled, foregroundRequired, startFailed

    var errorDescription: String? {
        switch self {
        case .locked: "请先解锁 iPhone，再呼叫 Mia。"
        case .microphonePermission: "请打开 Mia 并允许麦克风权限。"
        case .liveActivitiesDisabled: "请在系统设置中允许 Mia 的实时活动，或打开 Mia 开始聊天。"
        case .foregroundRequired: "请打开 Mia 完成麦克风授权，再使用声音快捷指令。"
        case .startFailed: "Mia 未能开始录音，请打开 App 检查连接和设备绑定。"
        }
    }
}

@MainActor
final class MiaConversationController: ObservableObject {
    static let shared = MiaConversationController()

    let session: MiaVoiceSession
    let xiaozhi: MiaXiaozhiClient
    @Published private(set) var isStarting = false
    @Published private(set) var systemActionCount: Int
    @Published private(set) var lastSystemActionAt: Date?
    private let preferences: UserDefaults
    private let activity = MiaLiveActivityController()
    private let requestRecordPermission: () async -> Bool
    private var observations: Set<AnyCancellable> = []
    private var generation = UUID()
    private var requiresActivity = false
    private var emotion = "calm"
    private var intensity: Double = 0
    private var authorizationTask: Task<Void, Never>?

    init(session: MiaVoiceSession? = nil, xiaozhi: MiaXiaozhiClient? = nil,
         preferences: UserDefaults = .standard,
         requestRecordPermission: @escaping () async -> Bool = {
             await withCheckedContinuation { continuation in
                 AVAudioSession.sharedInstance().requestRecordPermission {
                     continuation.resume(returning: $0)
                 }
             }
         }) {
        let session = session ?? MiaVoiceSession()
        let xiaozhi = xiaozhi ?? MiaXiaozhiClient()
        self.session = session
        self.xiaozhi = xiaozhi
        self.preferences = preferences
        systemActionCount = preferences.integer(forKey: "mia.shortcuts.invocationCount")
        let lastInvocation = preferences.double(forKey: "mia.shortcuts.lastInvocation")
        lastSystemActionAt = lastInvocation > 0 ? Date(timeIntervalSince1970: lastInvocation) : nil
        self.requestRecordPermission = requestRecordPermission
        session.connectionProvider = { [weak xiaozhi] in
            guard let xiaozhi else { throw CancellationError() }
            return try await xiaozhi.discover(
                ota: UserDefaults.standard.string(forKey: "mia.xiaozhi.otaURL") ?? MiaXiaozhiClient.defaultOTA,
                websocket: UserDefaults.standard.string(forKey: "mia.xiaozhi.websocketURL") ?? MiaXiaozhiClient.defaultWebSocket)
        }
        activity.onUnavailable = { [weak self] in
            guard let self, self.requiresActivity else { return }
            self.stop()
        }
        session.$state.combineLatest(session.$conversationActive)
            .sink { [weak self] state, active in
                // @Published emits before the stored property changes.
                self?.refreshActivity(state: state, active: active)
            }.store(in: &observations)
        session.$expression
            .sink { [weak self] expression in
                self?.updateEmotion(expression.emotion.rawValue, intensity: expression.intensity)
            }.store(in: &observations)
        let center = NotificationCenter.default
        center.publisher(for: UIApplication.protectedDataWillBecomeUnavailableNotification)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in self?.stop() }.store(in: &observations)
        center.publisher(for: AVAudioSession.interruptionNotification)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] note in
                if let type = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                   type == AVAudioSession.InterruptionType.began.rawValue { self?.stop() }
            }.store(in: &observations)
        center.publisher(for: AVAudioSession.routeChangeNotification)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] note in
                if let reason = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
                   reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue { self?.stop() }
            }.store(in: &observations)
        center.publisher(for: AVAudioSession.mediaServicesWereResetNotification)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in self?.stop() }.store(in: &observations)
        authorizationTask = Task { [weak self] in
            for await enabled in ActivityAuthorizationInfo().activityEnablementUpdates {
                guard !Task.isCancelled else { return }
                if !enabled, let self, self.requiresActivity { self.stop() }
            }
        }
    }

    deinit { authorizationTask?.cancel() }

    func startFromSystemAction() async throws {
        systemActionCount += 1
        let now = Date()
        lastSystemActionAt = now
        preferences.set(systemActionCount, forKey: "mia.shortcuts.invocationCount")
        preferences.set(now.timeIntervalSince1970, forKey: "mia.shortcuts.lastInvocation")
        // A repeated system invocation must not disturb an existing or pending conversation.
        guard !session.conversationActive, !isStarting else { return }
        try await start(requiresLiveActivity: true)
    }

    func start(requiresLiveActivity: Bool = false) async throws {
        guard UIApplication.shared.isProtectedDataAvailable else { throw MiaConversationStartError.locked }
        if session.conversationActive {
            if requiresLiveActivity {
                do {
                    try activity.start(.init(phase: .connecting))
                    requiresActivity = true
                    refreshActivity(state: session.state, active: true)
                    try await waitForCapture(attempt: generation)
                } catch { stop(); throw error }
            }
            return
        }
        guard !isStarting else { throw MiaConversationStartError.startFailed }
        if UIApplication.shared.applicationState != .active,
           AVAudioSession.sharedInstance().recordPermission == .undetermined {
            throw MiaConversationStartError.foregroundRequired
        }
        isStarting = true
        let attempt = generation
        defer { if attempt == generation { isStarting = false } }
        let permitted = await requestRecordPermission()
        guard attempt == generation else { throw CancellationError() }
        guard UIApplication.shared.isProtectedDataAvailable else { throw MiaConversationStartError.locked }
        guard permitted else { throw MiaConversationStartError.microphonePermission }
        requiresActivity = requiresLiveActivity
        do { try activity.start(.init(phase: .connecting)) }
        catch {
            if requiresLiveActivity { requiresActivity = false; throw error }
        }
        await session.beginConversation()
        if requiresLiveActivity {
            do { try await waitForCapture(attempt: attempt) }
            catch {
                if attempt == generation { stop() }
                throw error
            }
        }
    }

    func startInForeground(requiresLiveActivity: Bool = false) async throws {
        for _ in 0..<60 {
            if UIApplication.shared.applicationState == .active {
                try await start(requiresLiveActivity: requiresLiveActivity)
                return
            }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        throw MiaConversationStartError.foregroundRequired
    }

    private func waitForCapture(attempt: UUID) async throws {
        // Keep the recording intent running until the real audio engine starts.
        for _ in 0..<400 {
            guard attempt == generation else { throw CancellationError() }
            guard session.conversationActive else { throw MiaConversationStartError.startFailed }
            if session.state == .listening || session.state == .waiting || session.state == .speaking { return }
            if session.errorMessage != nil { throw MiaConversationStartError.startFailed }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        throw MiaConversationStartError.startFailed
    }

    func toggle() async {
        if session.conversationActive || isStarting { stop() }
        else {
            do { try await start() }
            catch is CancellationError { }
            catch { session.errorMessage = error.localizedDescription }
        }
    }

    func stop() {
        generation = UUID()
        isStarting = false
        requiresActivity = false
        session.disconnect()
        xiaozhi.cancelDiscovery()
        emotion = "calm"
        intensity = 0
        refreshActivity(state: .disconnected, active: false)
    }

    func settingsChanged() {
        stop()
        xiaozhi.cancel()
    }

    func showStandby() {
        guard UIApplication.shared.applicationState == .active,
              !session.conversationActive, !isStarting else { return }
        try? activity.start(.init(phase: .standby))
    }

    func updateEmotion(_ emotion: String, intensity: Double) {
        self.emotion = emotion
        self.intensity = intensity
        refreshActivity(state: session.state, active: session.conversationActive)
    }

    private func refreshActivity(state: MiaVoiceSession.State, active: Bool) {
        let phase: MiaActivityAttributes.Phase
        if !active { phase = .standby }
        else {
            switch state {
            case .disconnected, .connecting, .ready: phase = .connecting
            case .listening: phase = .listening
            case .waiting: phase = .thinking
            case .speaking: phase = .speaking
            }
        }
        activity.update(.init(phase: phase, emotion: active ? emotion : "calm",
                              intensity: active ? intensity : 0))
    }
}
