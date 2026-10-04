import SwiftUI

struct MiaAccountView: View {
    @ObservedObject var access: MiaAccountAccess
    let endpoint: String
    let onSuccess: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var username = ""
    @State private var password = ""
    @State private var confirmation = ""
    @State private var registering = false
    @State private var busy = false
    @State private var message: String?
    @State private var requestTask: Task<Void, Never>?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("用户名", text: $username)
                        .textContentType(.username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("密码", text: $password)
                        .textContentType(registering ? .newPassword : .password)
                    if registering {
                        SecureField("再次输入密码", text: $confirmation)
                            .textContentType(.newPassword)
                    }
                } footer: {
                    Text(registering ? "用户名为 3–32 个汉字、字母、数字或下划线；密码为 15–128 个字符，支持空格。"
                         : "登录后可直接与 Mia 对话。忘记密码请联系管理员。")
                }
                if let message { Section { Text(message).foregroundStyle(.red) } }
                Section {
                    Button(registering ? "注册并登录" : "登录") { submit() }
                        .disabled(busy || username.isEmpty || password.isEmpty)
                    if busy { ProgressView("正在处理") }
                    Button(registering ? "已有账号，去登录" : "没有账号，去注册") {
                        registering.toggle()
                        message = nil
                        password = ""
                        confirmation = ""
                    }
                    .disabled(busy)
                }
            }
            .navigationTitle(registering ? "注册 Mia 账号" : "登录 Mia")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
            }
            .onDisappear {
                requestTask?.cancel()
                access.cancelSignIn()
                password = ""
                confirmation = ""
            }
        }
        .preferredColorScheme(.dark)
    }

    private func submit() {
        if registering && password != confirmation {
            message = "两次密码不同"
            return
        }
        busy = true
        message = nil
        requestTask = Task { @MainActor in
            defer { busy = false }
            do {
                try await access.signIn(endpoint: endpoint, username: username,
                                         password: password, register: registering)
                guard !Task.isCancelled else { return }
                password = ""
                confirmation = ""
                onSuccess()
                dismiss()
            } catch {
                if !Task.isCancelled { message = error.localizedDescription }
            }
        }
    }
}
