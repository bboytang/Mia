import SwiftUI

struct ContentView: View {
    @State private var showsSettings = false
    @StateObject private var session = MiaVoiceSession()
    @AppStorage("mia.serverURL") private var serverURL = "wss://8kraw.cloud/xiaozhi/v1/"

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Image("CityBackground")
                    .resizable()
                    .scaledToFill()
                    .frame(width: geometry.size.width, height: geometry.size.height)
                    .clipped()
                    .ignoresSafeArea()

                LinearGradient(
                    colors: [.black.opacity(0.32), .clear, .black.opacity(0.58)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .ignoresSafeArea()

                Image("MiaPortrait")
                    .resizable()
                    .scaledToFit()
                    .frame(width: geometry.size.width * 1.12,
                           height: geometry.size.height * 0.75)
                    .position(x: geometry.size.width / 2,
                              y: geometry.size.height * 0.49)
                    .accessibilityLabel("Mia 角色概念立绘")

                VStack(spacing: 0) {
                    header
                    Spacer()
                    captionPanel
                    waveform.padding(.top, 22)
                    Button {
                        if serverURL.isEmpty || MiaTokenStore.read() == nil {
                            showsSettings = true
                        } else {
                            Task {
                                await session.toggleTalk(endpoint: serverURL,
                                                         token: MiaTokenStore.read())
                            }
                        }
                    } label: {
                        Image(systemName: "mic.fill")
                            .font(.system(size: 31, weight: .light))
                            .foregroundStyle(.white)
                            .frame(width: 84, height: 84)
                            .background(
                                Circle().fill(
                                    LinearGradient(
                                        colors: [.indigo, .purple, .cyan],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                            )
                            .overlay(Circle().stroke(.white.opacity(0.8), lineWidth: 1.5))
                            .shadow(color: .purple.opacity(0.9), radius: 22)
                    }
                    .accessibilityLabel(session.state == .listening ? "结束说话" : "开始说话")
                    .disabled(session.state == .connecting)
                    .padding(.top, 12)
                    Text(MiaTokenStore.read() == nil ? "先在设置中填写网关令牌" : session.state.rawValue)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.8))
                        .padding(.top, 14)
                }
                .padding(.horizontal, 22)
                .padding(.top, 14)
                .padding(.bottom, 22)
            }
        }
        .sheet(isPresented: $showsSettings) {
            MiaSettingsView()
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

    private var header: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 3) {
                Text("MIA")
                    .font(.system(size: 27, weight: .light, design: .rounded))
                    .tracking(7)
                Text("你的语音伙伴")
                    .font(.footnote)
                    .foregroundStyle(.cyan.opacity(0.85))
            }
            Spacer()
            Button {
                showsSettings = true
            } label: {
                Image(systemName: "gearshape")
                    .font(.title3)
                    .frame(width: 44, height: 44)
                    .background(.ultraThinMaterial, in: Circle())
            }
            .accessibilityLabel("设置")
        }
        .foregroundStyle(.white)
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
                    .stroke(.cyan.opacity(0.55), lineWidth: 1)
            )
    }

    private var waveform: some View {
        HStack(alignment: .center, spacing: 5) {
            ForEach(0..<27, id: \.self) { index in
                Capsule()
                    .fill(index.isMultiple(of: 2) ? Color.cyan : Color.purple)
                    .frame(width: 3, height: CGFloat([9, 16, 25, 13, 33, 20, 12][index % 7])
                           * CGFloat(1 + min(session.audioLevel * 5, 1)))
            }
        }
        .frame(height: 37)
        .accessibilityHidden(true)
    }
}

private struct MiaSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("mia.serverURL") private var serverURL = "wss://8kraw.cloud/xiaozhi/v1/"
    @State private var accessToken = ""
    @State private var tokenStatus = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("wss://8kraw.cloud/xiaozhi/v1/", text: $serverURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                } header: {
                    Text("服务端")
                } footer: {
                    Text("请填写支持小智 WebSocket 协议的安全连接地址。")
                }
                Section("访问令牌") {
                    SecureField("网关访问令牌", text: $accessToken)
                    Button("保存令牌") {
                        do {
                            try MiaTokenStore.save(accessToken)
                            tokenStatus = "已保存在本机钥匙串"
                        } catch {
                            tokenStatus = "保存失败：\(error.localizedDescription)"
                        }
                    }
                    if !tokenStatus.isEmpty { Text(tokenStatus).font(.footnote) }
                }
                Section("开发进度") {
                    LabeledContent("WebSocket 协议", value: "已接入")
                    LabeledContent("语音收发", value: "等待真机联调")
                    LabeledContent("Live2D 角色", value: "等待模型素材")
                }
            }
            .navigationTitle("设置")
            .onAppear { accessToken = MiaTokenStore.read() ?? "" }
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
