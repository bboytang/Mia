import SwiftUI
import MediaPlayer

struct ContentView: View {
    @ObservedObject private var controller = MiaConversationController.shared
    @ObservedObject private var xiaozhi = MiaConversationController.shared.xiaozhi
    @ObservedObject private var session = MiaConversationController.shared.session
    @State private var showsSettings = false
    @AppStorage(MiaSkin.storageKey) private var skin: MiaSkin = .glass
    @AppStorage("mia.xiaozhi.websocketURL") private var serverURL = MiaXiaozhiClient.defaultWebSocket
    @AppStorage("mia.xiaozhi.otaURL") private var otaURL = MiaXiaozhiClient.defaultOTA

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                MiaCompanionBackground()
                Button { Task { await controller.toggle() } } label: {
                    MiaAvatarView(skin: skin, emotion: session.expression.emotion, state: orbState,
                                  intensity: session.expression.intensity, level: session.audioLevel)
                        .frame(width: geometry.size.width * 0.76, height: geometry.size.width * 0.76)
                        .contentShape(Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(session.conversationActive || controller.isStarting ? "结束对话" : "开始说话")
                .accessibilityValue(skin.title + " · " + session.expression.emotion.displayName)
                .accessibilityIdentifier("mia-avatar")
                .accessibilityHint("点小球开始或结束与 Mia 的聊天")
                .offset(y: -geometry.size.height * 0.06)

                VStack {
                    HStack {
                        Spacer()
                        Button { showsSettings = true } label: {
                            Image(systemName: "gearshape")
                                .font(.title3).frame(width: 44, height: 44)
                        }
                        .accessibilityLabel("设置")
                    }
                    Spacer()
                    Text(status)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.55))
                        .padding(.bottom, 36)
                }
                .padding(.horizontal, 22).padding(.top, 8)
            }
        }
        .foregroundStyle(.white.opacity(0.8))
        .preferredColorScheme(.dark)
        .onAppear { controller.showStandby() }
        .sheet(isPresented: $showsSettings) { MiaSettingsView(xiaozhi: xiaozhi, session: session) }
        .onChange(of: serverURL) { _, _ in controller.settingsChanged() }
        .onChange(of: otaURL) { _, _ in controller.settingsChanged() }
        .onChange(of: xiaozhi.activationCode) { _, code in if code != nil { showsSettings = true } }
        .onOpenURL { url in
            guard url.scheme == "mia", url.host == "conversation" else { return }
            if url.path == "/start" {
                Task {
                    do { try await controller.startInForeground() }
                    catch { session.errorMessage = error.localizedDescription }
                }
            }
        }
        .alert("连接出错", isPresented: Binding(
            get: { session.errorMessage != nil && xiaozhi.activationCode == nil },
            set: { if !$0 { session.errorMessage = nil } }
        )) {
            Button("知道了") { session.errorMessage = nil }
        } message: { Text(session.errorMessage ?? "未知错误") }
    }

    private var orbState: MiaOrbState {
        switch session.state {
        case .listening: .listening
        case .waiting, .connecting: .thinking
        case .speaking: .speaking
        default: .idle
        }
    }

    private var status: String {
        if xiaozhi.activationCode != nil { return "请在智控台绑定 Mia" }
        if controller.isStarting || session.state == .connecting { return "正在连接" }
        if !session.conversationActive { return "点小球开始 · 声音唤醒需先设置" }
        switch session.state {
        case .listening: return "在听"
        case .waiting: return "想一想"
        case .speaking: return "Mia 正在回答"
        default: return "待呼叫"
        }
    }
}

private struct MiaCompanionBackground: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 12,
                                paused: reduceMotion || scenePhase != .active)) { timeline in
            let phase = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
                .truncatingRemainder(dividingBy: 120) / 120 * Double.pi * 2
            GeometryReader { geometry in
                ZStack {
                    LinearGradient(colors: [Color(red: 0.012, green: 0.025, blue: 0.065),
                                            Color(red: 0.025, green: 0.015, blue: 0.07), .black],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                    Ellipse().fill(.blue.opacity(0.13)).blur(radius: 70)
                        .frame(width: geometry.size.width * 0.9, height: geometry.size.height * 0.45)
                        .offset(x: sin(phase) * 22, y: -geometry.size.height * 0.12)
                    Ellipse().fill(.purple.opacity(0.08)).blur(radius: 80)
                        .frame(width: geometry.size.width, height: geometry.size.height * 0.3)
                        .offset(x: -sin(phase) * 15, y: geometry.size.height * 0.2)
                    Path { path in
                        path.move(to: CGPoint(x: -20, y: geometry.size.height * 0.7))
                        path.addCurve(to: CGPoint(x: geometry.size.width + 20, y: geometry.size.height * 0.33),
                                      control1: CGPoint(x: geometry.size.width * 0.1, y: geometry.size.height * 0.55),
                                      control2: CGPoint(x: geometry.size.width * 0.8, y: geometry.size.height * 0.65))
                    }
                    .stroke(.cyan.opacity(0.06), lineWidth: 1)
                    .offset(y: sin(phase) * 12)
                }
            }
        }
        .ignoresSafeArea().allowsHitTesting(false).accessibilityHidden(true)
    }
}

private struct MiaSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject private var controller = MiaConversationController.shared
    @ObservedObject var xiaozhi: MiaXiaozhiClient
    @ObservedObject var session: MiaVoiceSession
    @AppStorage("mia.xiaozhi.websocketURL") private var serverURL = MiaXiaozhiClient.defaultWebSocket
    @AppStorage("mia.xiaozhi.otaURL") private var otaURL = MiaXiaozhiClient.defaultOTA
    @State private var discoveryError: String?
    @State private var authorizationCode = ""
    @State private var authorizationStatus: String?
    @State private var authorizing = false
    @State private var showsMemory = false

    var body: some View {
        NavigationStack {
            Form {
                Section("小智服务端") {
                    TextField("WebSocket 地址", text: $serverURL)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                        .accessibilityLabel("WebSocket 地址")
                    TextField("OTA 地址", text: $otaURL)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                        .accessibilityLabel("OTA 地址")
                    if serverURL.hasPrefix("ws://") || otaURL.hasPrefix("http://") {
                        Text("当前为明文连接，语音和设备令牌可能被网络中间人读取。正式部署请使用 HTTPS / WSS。")
                            .font(.footnote)
                    }
                }
                Section("设备绑定") {
                    LabeledContent("设备标识", value: xiaozhi.identity.deviceID)
                        .textSelection(.enabled)
                    if let code = xiaozhi.activationCode {
                        LabeledContent("激活码", value: code)
                            .textSelection(.enabled)
                            .accessibilityElement(children: .ignore)
                            .accessibilityLabel("激活码")
                            .accessibilityValue(code)
                            .accessibilityIdentifier("xiaozhi-activation-code")
                        Text("在你的智控台打开目标智能体，进入设备管理／添加设备，输入激活码。绑定后点击下方检查，再回首页开始说话。")
                            .font(.footnote)
                    }
                    Text(xiaozhi.status)
                    Button("检查设备绑定") {
                        discoveryError = nil
                        Task {
                            do { try await session.checkDeviceBinding() }
                            catch { discoveryError = error.localizedDescription }
                        }
                    }
                    .disabled(xiaozhi.checking)
                    if let discoveryError { Text(discoveryError).font(.footnote) }
                }
                Section("私有授权") {
                    Text("在智控台为上述已绑定设备生成一次性授权码，完成后恢复个性化语音。")
                        .font(.footnote)
                    SecureField("智控台授权码", text: $authorizationCode)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .accessibilityIdentifier("mia-private-authorization-code")
                    Button("完成私有授权") {
                        controller.stop()
                        authorizing = true
                        authorizationStatus = nil
                        let selectedOTA = otaURL, selectedVoice = serverURL, code = authorizationCode
                        Task {
                            defer { authorizing = false; authorizationCode = "" }
                            do {
                                let grant = try await MiaPrivateAuthorizationClient.exchange(ota: selectedOTA,
                                    websocket: selectedVoice, identity: xiaozhi.identity, code: code)
                                guard selectedOTA == otaURL, selectedVoice == serverURL else { throw CancellationError() }
                                try MiaTokenStore.savePrivateGrant(grant)
                                authorizationStatus = "授权已保存，回首页即可恢复个性化语音。"
                                session.errorMessage = nil
                            } catch is CancellationError { authorizationStatus = "地址已改变，请重新授权。" }
                            catch { authorizationStatus = error.localizedDescription }
                        }
                    }
                    .disabled(authorizing || authorizationCode.isEmpty)
                    Button("移除本机私有凭据") {
                        controller.stop()
                        do { try MiaTokenStore.clearPrivateGrant(); authorizationStatus = "本机凭据已移除。服务器授权可在智控台撤销。" }
                        catch { authorizationStatus = error.localizedDescription }
                    }
                    .disabled(authorizing)
                    if let authorizationStatus { Text(authorizationStatus).font(.footnote) }
                }
                Section("Mia") {
                    NavigationLink("个性化皮肤") { MiaSkinView() }
                    Button {
                        controller.stop()
                        showsMemory = true
                    } label: {
                        HStack {
                            Text("记忆与成长")
                            Spacer()
                            Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(.tertiary)
                        }
                    }.foregroundStyle(.primary).accessibilityLabel("记忆与成长")
                    NavigationLink("设置声音唤醒") { MiaWakeGuideView() }
                    Button("关闭 Mia 对话") { MiaConversationController.shared.stop() }
                }
                Section("声音设备") {
                    LabeledContent("麦克风", value: controller.inputDevice)
                    LabeledContent("播放设备", value: controller.outputDevice)
                    HStack {
                        Text("选择播放设备")
                        Spacer()
                        MiaAudioRoutePicker().frame(width: 44, height: 44)
                    }
                    Text("开始对话后可在这里确认耳机是否被选中。")
                        .font(.footnote)
                }
                Section("最近一次语音识别") {
                    Text(session.lastUserTranscript.isEmpty ? "尚未收到识别结果" : session.lastUserTranscript)
                        .textSelection(.enabled)
                    Text("先核对识别文字是否符合原话；若文字正确而回复或歌曲不对，应检查回复或音乐服务。这里只显示，不保存为诊断日志。")
                        .font(.footnote)
                }
                Section("连接诊断（已隐藏凭据）") {
                    LabeledContent("设备采样率", value: String(format: "%.0f Hz", controller.hardwareSampleRate))
                    LabeledContent("上传前丢弃帧", value: String(session.droppedMicrophoneFrames))
                    LabeledContent("系统开始动作次数", value: String(controller.systemActionCount))
                    LabeledContent("最近系统动作", value: controller.lastSystemActionAt?.formatted(date: .abbreviated, time: .standard) ?? "未调用")
                    LabeledContent("对话状态", value: session.state.rawValue)
                    LabeledContent("采集音频帧", value: String(session.microphoneFrames))
                    LabeledContent("上传音频帧", value: String(session.uploadedFrames))
                    LabeledContent("输入峰值", value: String(format: "%.1f%%", session.microphonePeak * 100))
                    LabeledContent("HTTP 握手", value: session.diagnostics.httpStatus.map(String.init) ?? "未完成")
                    LabeledContent("关闭码", value: session.diagnostics.closeCode.map(String.init) ?? "未收到")
                    LabeledContent("关闭原因", value: session.diagnostics.closeReason)
                    LabeledContent("最后消息", value: session.diagnostics.lastMessage)
                    LabeledContent("异常", value: session.diagnostics.exception)
                }
            }
            .onAppear { controller.refreshAudioRoute() }
            .navigationTitle("设置")
            .navigationDestination(isPresented: $showsMemory) { MiaMemoryView(session: session) }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { Button("完成") { dismiss() } }
            }
        }
    }
}

#Preview {
    ContentView()
}

private struct MiaAudioRoutePicker: UIViewRepresentable {
    func makeUIView(context: Context) -> MPVolumeView {
        let view = MPVolumeView(frame: .zero)
        view.showsVolumeSlider = false
        view.accessibilityLabel = "选择播放设备"
        return view
    }

    func updateUIView(_ uiView: MPVolumeView, context: Context) { }
}
