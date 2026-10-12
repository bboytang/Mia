import SwiftUI
import AVFoundation

struct ContentView: View {
    var isActive = true
    @State private var showsSettings = false
    @StateObject private var xiaozhi = MiaXiaozhiClient()
    @StateObject private var session = MiaVoiceSession()
    @Environment(\.scenePhase) private var scenePhase
    @AppStorage("mia.xiaozhi.websocketURL") private var serverURL = MiaXiaozhiClient.defaultWebSocket
    @AppStorage("mia.xiaozhi.otaURL") private var otaURL = MiaXiaozhiClient.defaultOTA

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .top) {
                starMist(in: geometry)

                Image("MiaPortrait")
                    .resizable()
                    .scaledToFit()
                    .frame(width: geometry.size.width * 1.16,
                           height: geometry.size.height * 0.88, alignment: .top)
                    .mask {
                        LinearGradient(stops: [
                            .init(color: .white, location: 0),
                            .init(color: .white, location: 0.72),
                            .init(color: .white.opacity(0.25), location: 0.91),
                            .init(color: .clear, location: 1)
                        ], startPoint: .top, endPoint: .bottom)
                    }
                    .padding(.top, 8)
                    .accessibilityLabel("Mia 半身角色概念立绘")

                starMist(in: geometry)
                    .mask {
                        LinearGradient(stops: [
                            .init(color: .clear, location: 0),
                            .init(color: .clear, location: 0.57),
                            .init(color: .white.opacity(0.18), location: 0.70),
                            .init(color: .white, location: 0.92)
                        ], startPoint: .top, endPoint: .bottom)
                    }
                    .allowsHitTesting(false)

                LinearGradient(stops: [
                    .init(color: .clear, location: 0.48),
                    .init(color: Color(red: 0.12, green: 0.04, blue: 0.24).opacity(0.28), location: 0.68),
                    .init(color: .black.opacity(0.65), location: 1)
                ], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
                .allowsHitTesting(false)

                VStack(spacing: 0) {
                    header
                    Spacer(minLength: 12)
                    captionPanel
                    Button {
                        Task {
                            let stopping = session.conversationActive
                            await session.toggleTalk()
                            if stopping { xiaozhi.cancelDiscovery() }
                        }
                    } label: {
                        MiaAuroraOrb(level: session.audioLevel)
                            .frame(width: geometry.size.height < 700 ? 102 : 118,
                                   height: geometry.size.height < 700 ? 102 : 118)
                            .contentShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(talkButtonLabel)
                    .accessibilityHint(session.conversationActive ? "结束当前语音对话" : "开启自动语音对话")
                    .padding(.top, 12)
                    Text(xiaozhi.activationCode != nil ? "请在智控台绑定本机" : session.state.rawValue)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.8))
                        .padding(.top, 2)
                }
                .padding(.horizontal, 22)
                .padding(.top, 8)
                .padding(.bottom, 18)
                .frame(width: geometry.size.width, height: geometry.size.height)
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
        }
        .preferredColorScheme(.dark)
        .sheet(isPresented: $showsSettings) {
            MiaSettingsView(xiaozhi: xiaozhi, session: session)
        }
        .onAppear {
            let client = xiaozhi
            session.connectionProvider = { [weak client] in
                guard let client else { throw CancellationError() }
                return try await client.discover(
                    ota: UserDefaults.standard.string(forKey: "mia.xiaozhi.otaURL") ?? MiaXiaozhiClient.defaultOTA,
                    websocket: UserDefaults.standard.string(forKey: "mia.xiaozhi.websocketURL") ?? MiaXiaozhiClient.defaultWebSocket)
            }
            startAutomatically()
        }
        .onChange(of: isActive) { _, _ in startAutomatically() }
        .onChange(of: serverURL) { _, _ in session.disconnect(); xiaozhi.cancel() }
        .onChange(of: otaURL) { _, _ in session.disconnect(); xiaozhi.cancel() }
        .onChange(of: xiaozhi.activationCode) { _, code in
            if code != nil { showsSettings = true }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { session.disconnect(); xiaozhi.cancelDiscovery() }
            else if phase == .active { startAutomatically() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { note in
            if let type = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
               type == AVAudioSession.InterruptionType.began.rawValue { session.disconnect() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { note in
            if let reason = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
               reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue { session.disconnect() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification)) { _ in
            session.disconnect()
        }
        .onDisappear { session.disconnect(); xiaozhi.cancelDiscovery() }
        .alert("连接出错", isPresented: Binding(
            get: { session.errorMessage != nil && xiaozhi.activationCode == nil },
            set: { if !$0 { session.errorMessage = nil } }
        )) {
            Button("知道了") { session.errorMessage = nil }
        } message: {
            Text(session.errorMessage ?? "未知错误")
        }
    }

    private func startAutomatically() {
        guard isActive, scenePhase == .active,
              !ProcessInfo.processInfo.arguments.contains("-MiaDisableAutomaticConversation"),
              session.state == .disconnected, session.errorMessage == nil,
              xiaozhi.activationCode == nil else { return }
        Task { await session.beginConversation() }
    }

    private func starMist(in geometry: GeometryProxy) -> some View {
        Image("StarMistBackground")
            .resizable()
            .scaledToFill()
            .frame(width: geometry.size.width,
                   height: geometry.size.height + geometry.safeAreaInsets.top + geometry.safeAreaInsets.bottom)
            .clipped()
            .offset(y: -geometry.safeAreaInsets.top)
            .frame(width: geometry.size.width, height: geometry.size.height, alignment: .top)
    }

    private var talkButtonLabel: String {
        session.conversationActive ? "结束对话" : "开始说话"
    }

    private var header: some View {
        HStack {
            Spacer()
            Button {
                showsSettings = true
            } label: {
                Image(systemName: "gearshape")
                    .font(.title3)
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("设置")
        }
        .foregroundStyle(.white.opacity(0.85))
    }

    private var captionPanel: some View {
        Text(session.caption.isEmpty ? "Mia 的回答会显示在这里" : session.caption)
            .font(.system(size: 17, weight: .regular, design: .rounded))
            .foregroundStyle(.white.opacity(0.85))
            .frame(maxWidth: .infinity, minHeight: 80)
            .padding(.horizontal, 14)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 20))
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(.purple.opacity(0.65), lineWidth: 1)
            )
    }
}

private struct MiaSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var xiaozhi: MiaXiaozhiClient
    @ObservedObject var session: MiaVoiceSession
    @AppStorage("mia.xiaozhi.websocketURL") private var serverURL = MiaXiaozhiClient.defaultWebSocket
    @AppStorage("mia.xiaozhi.otaURL") private var otaURL = MiaXiaozhiClient.defaultOTA
    @State private var discoveryError: String?

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
                        LabeledContent("激活码", value: code).textSelection(.enabled)
                        Text("在你的智控台打开目标智能体，进入设备管理／添加设备，输入激活码。绑定后点击下方检查，再回首页开始说话。")
                            .font(.footnote)
                    }
                    Text(xiaozhi.status)
                    Button("检查设备绑定") {
                        session.disconnect()
                        discoveryError = nil
                        Task {
                            do { _ = try await xiaozhi.discover(ota: otaURL, websocket: serverURL) }
                            catch { discoveryError = error.localizedDescription }
                        }
                    }
                    .disabled(xiaozhi.checking)
                    if let discoveryError { Text(discoveryError).font(.footnote) }
                }
                Section("连接诊断（已隐藏凭据）") {
                    LabeledContent("HTTP 握手", value: session.diagnostics.httpStatus.map(String.init) ?? "未完成")
                    LabeledContent("关闭码", value: session.diagnostics.closeCode.map(String.init) ?? "未收到")
                    LabeledContent("关闭原因", value: session.diagnostics.closeReason)
                    LabeledContent("最后消息", value: session.diagnostics.lastMessage)
                    LabeledContent("异常", value: session.diagnostics.exception)
                }
            }
            .navigationTitle("设置")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { Button("完成") { dismiss() } }
            }
        }
    }
}

#Preview {
    ContentView()
}
