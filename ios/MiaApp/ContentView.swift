import SwiftUI

struct ContentView: View {
    @State private var showsSettings = false

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

                VStack(spacing: 0) {
                    header
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "sparkles.rectangle.stack")
                            .font(.system(size: 31, weight: .ultraLight))
                        Text("Mia 即将登场")
                            .font(.system(size: 20, weight: .medium, design: .rounded))
                        Text("角色动画模型准备中")
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                    .foregroundStyle(.white.opacity(0.86))
                    .shadow(color: .purple.opacity(0.8), radius: 15)
                    Spacer()
                    captionPanel
                    waveform.padding(.top, 22)
                    Button {
                        showsSettings = true
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
                    .accessibilityLabel("语音设置")
                    .padding(.top, 12)
                    Text("语音连接准备中 · 点击配置服务端")
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
        Text("Mia 的回答会显示在这里")
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
                    .frame(width: 3, height: CGFloat([9, 16, 25, 13, 33, 20, 12][index % 7]))
            }
        }
        .frame(height: 37)
        .accessibilityHidden(true)
    }
}

private struct MiaSettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("mia.serverURL") private var serverURL = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("服务端") {
                    TextField("wss://你的域名/xiaozhi/v1/", text: $serverURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                } footer: {
                    Text("请填写支持小智 WebSocket 协议的安全连接地址。")
                }
                Section("开发进度") {
                    LabeledContent("WebSocket 协议", value: "已接入")
                    LabeledContent("语音收发", value: "开发中")
                    LabeledContent("Live2D 角色", value: "等待模型素材")
                }
            }
            .navigationTitle("设置")
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
