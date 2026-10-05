import SwiftUI

struct ContentView: View {
    @State private var showsSettings = false
    @State private var showsLogin = false
    @StateObject private var account = MiaAccountAccess()
    @AppStorage("mia.maintenanceMode") private var maintenanceMode = false
    @AppStorage("mia.accountMigrationDone") private var accountMigrationDone = false
    @StateObject private var session = MiaVoiceSession()
    @AppStorage("mia.serverURL") private var serverURL = "wss://8kraw.cloud/xiaozhi/v1/"

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
                        if let token = account.prepareVoice(endpoint: serverURL, maintenanceMode: maintenanceMode,
                                                            legacyToken: MiaTokenStore.read(),
                                                            disconnect: session.disconnect) {
                            Task {
                                await session.toggleTalk(endpoint: serverURL,
                                                         token: token)
                            }
                        } else if maintenanceMode {
                            showsSettings = true
                        } else {
                            showsLogin = true
                        }
                    } label: {
                        MiaAuroraOrb(level: session.audioLevel)
                            .frame(width: geometry.size.height < 700 ? 102 : 118,
                                   height: geometry.size.height < 700 ? 102 : 118)
                            .contentShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(talkButtonLabel)
                    .accessibilityHint(session.state == .speaking ? "打断 Mia 并开始说话" : "轻触控制语音对话")
                    .disabled(session.state == .connecting)
                    .padding(.top, 12)
                    Text(account.token(endpoint: serverURL, maintenanceMode: maintenanceMode, legacyToken: MiaTokenStore.read()) == nil ? "轻触登录，与 Mia 对话" : session.state.rawValue)
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
            MiaSettingsView(account: account, session: session)
        }
        .sheet(isPresented: $showsLogin) {
            MiaAccountView(access: account, endpoint: serverURL) {
                maintenanceMode = false
                session.disconnect()
            }
        }
        .onAppear {
            if !accountMigrationDone {
                maintenanceMode = account.credential == nil && MiaTokenStore.read() != nil
                accountMigrationDone = true
            }
        }
        .onChange(of: serverURL) { _, _ in session.disconnect() }
        .onChange(of: maintenanceMode) { _, _ in session.disconnect() }
        .onChange(of: account.credential) { _, _ in session.disconnect() }
        .onChange(of: session.authorizationRejected) { _, rejected in
            if rejected && !maintenanceMode {
                account.invalidate(endpoint: serverURL)
                session.errorMessage = nil
                showsLogin = true
            }
        }
        .alert("连接出错", isPresented: Binding(
            get: { session.errorMessage != nil },
            set: { if !$0 { session.errorMessage = nil } }
        )) {
            Button("知道了") { session.errorMessage = nil }
        } message: {
            Text(session.errorMessage ?? "未知错误")
        }
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
        switch session.state {
        case .connecting: "正在连接"
        case .listening: "结束说话"
        case .speaking: "打断并开始说话"
        case .disconnected, .ready: "开始说话"
        }
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
    @ObservedObject var account: MiaAccountAccess
    @ObservedObject var session: MiaVoiceSession
    @AppStorage("mia.serverURL") private var serverURL = "wss://8kraw.cloud/xiaozhi/v1/"
    @AppStorage("mia.maintenanceMode") private var maintenanceMode = false
    @State private var showsLogin = false
    @State private var signingOut = false
    @State private var accessToken = ""
    @State private var tokenStatus = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("账号") {
                    if let credential = account.credential,
                       credential.usable(endpoint: serverURL) {
                        LabeledContent("用户名", value: credential.username)
                        Button("退出登录", role: .destructive) {
                            signingOut = true
                            maintenanceMode = false
                            Task {
                                await account.logout(endpoint: serverURL, disconnect: session.disconnect)
                                signingOut = false
                            }
                        }
                        .disabled(signingOut)
                    } else {
                        Button("登录或注册") { showsLogin = true }
                    }
                    if let warning = account.warning { Text(warning).font(.footnote) }
                }
                Section {
                    DisclosureGroup("高级维护") {
                        Toggle("使用维护令牌", isOn: $maintenanceMode)
                        TextField("服务端地址", text: $serverURL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                        SecureField("网关访问令牌", text: $accessToken)
                        Button("保存维护令牌") {
                            do {
                                try MiaTokenStore.save(accessToken)
                                session.disconnect()
                                tokenStatus = "已保存在本机钥匙串"
                            } catch {
                                tokenStatus = "保存失败：\(error.localizedDescription)"
                            }
                        }
                        if !tokenStatus.isEmpty { Text(tokenStatus).font(.footnote) }
                        Text("仅供管理员维护。日常使用请注册或登录账号。")
                            .font(.footnote)
                    }
                }
                Section("开发进度") {
                    LabeledContent("WebSocket 协议", value: "已接入")
                    LabeledContent("语音收发", value: "等待真机联调")
                    LabeledContent("Live2D 角色", value: "等待模型素材")
                }
            }
            .navigationTitle("设置")
            .onAppear { accessToken = MiaTokenStore.read() ?? "" }
            .sheet(isPresented: $showsLogin) {
                MiaAccountView(access: account, endpoint: serverURL) {
                    maintenanceMode = false
                    session.disconnect()
                }
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    ContentView()
}
