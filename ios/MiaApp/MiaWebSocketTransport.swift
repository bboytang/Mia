import Foundation

enum MiaConnectionError: LocalizedError {
    case invalidEndpoint
    case unexpectedMessage
    case handshakeTimeout
    case unauthorized
    case privateAuthorizationRequired
    case serverClosed
    case upstreamError
    case responseTimeout

    var errorDescription: String? {
        switch self {
        case .invalidEndpoint: "请输入有效的 ws:// 或 wss:// 地址，凭据不能放在地址中"
        case .unexpectedMessage: "服务端返回了无法识别的消息"
        case .handshakeTimeout: "服务端握手超时"
        case .unauthorized: "小智设备认证失败，请重新检查 OTA 和设备绑定"
        case .privateAuthorizationRequired: "请用智控台授权码完成授权"
        case .serverClosed: "小智服务端已关闭连接"
        case .upstreamError: "小智服务端报告语音处理错误，请查看智控台日志"
        case .responseTimeout: "小智未在规定时间内返回语音，请检查智能体的 ASR、LLM 和 TTS 配置"
        }
    }
}

struct MiaWebSocketConfiguration {
    let request: URLRequest

    init(endpoint: String, clientID: UUID, token: String?, deviceID: String? = nil) throws {
        let url = try MiaXiaozhiClient.validatedURL(endpoint, schemes: ["ws", "wss"])
        let device = deviceID ?? MiaXiaozhiIdentity.deviceID(for: clientID)
        guard MiaXiaozhiIdentity.validDeviceID(device) else { throw MiaXiaozhiError.invalidIdentity }
        guard token == nil || (token!.count <= 4096 && !token!.unicodeScalars.contains(where: { $0.value == 13 || $0.value == 10 })) else {
            throw MiaConnectionError.invalidEndpoint
        }

        var request = URLRequest(url: url)
        let identity = clientID.uuidString.lowercased()
        request.setValue("1", forHTTPHeaderField: "Protocol-Version")
        request.setValue(device, forHTTPHeaderField: "Device-Id")
        request.setValue(identity, forHTTPHeaderField: "Client-Id")
        if let token, !token.isEmpty {
            let authorization = token.contains(" ") ? token : "Bearer " + token
            request.setValue(authorization, forHTTPHeaderField: "Authorization")
        }
        self.request = request
    }
}

struct MiaConnectionDiagnostics: Equatable {
    var httpStatus: Int?
    var closeCode: Int?
    var closeReason = "未收到关闭原因"
    var lastMessage = "无"
    var exception = "无"

    static func safeReason(_ reason: Data?) -> String {
        guard let reason, !reason.isEmpty else { return "无关闭原因" }
        let text = String(data: reason, encoding: .utf8)
        if ["未授权", "认证失败", "无效握手"].contains(text ?? "") { return text! }
        return "内容已隐藏（\(reason.count) 字节）"
    }
}

private final class MiaSocketDiagnosticsDelegate: NSObject, URLSessionWebSocketDelegate {
    private let lock = NSLock()
    private var state = MiaConnectionDiagnostics()
    let update: (Int?, Int?, Data?) -> Void
    init(update: @escaping (Int?, Int?, Data?) -> Void) { self.update = update }
    var snapshot: MiaConnectionDiagnostics {
        lock.lock()
        defer { lock.unlock() }
        return state
    }
    func record(status: Int?, code: Int?, reason: Data?) {
        lock.lock()
        if let status { state.httpStatus = status }
        if let code {
            state.closeCode = code
            state.closeReason = MiaConnectionDiagnostics.safeReason(reason)
        }
        lock.unlock()
        update(status, code, reason)
    }
    func record(kind: String, value: String) {
        lock.lock()
        if kind == "error" { state.exception = value }
        else { state.lastMessage = value }
        lock.unlock()
    }
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol protocol: String?) {
        record(status: 101, code: nil, reason: nil)
    }
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        record(status: (webSocketTask.response as? HTTPURLResponse)?.statusCode,
               code: closeCode.rawValue, reason: reason)
    }
}

enum MiaIncomingFrame {
    case event(MiaServerEvent)
    case opus(Data)
}

final class MiaWebSocketTransport {
    private let socket: URLSessionWebSocketTask
    private let diagnosticDelegate: MiaSocketDiagnosticsDelegate
    private let diagnosticUpdate: (String, String) -> Void
    var diagnostics: MiaConnectionDiagnostics { diagnosticDelegate.snapshot }
    private func record(_ kind: String, _ value: String) {
        diagnosticDelegate.record(kind: kind, value: value)
        diagnosticUpdate(kind, value)
    }

    static func isUnauthorized(code: URLSessionWebSocketTask.CloseCode, reason: Data?) -> Bool {
        code == .policyViolation && reason.flatMap { String(data: $0, encoding: .utf8) } == "未授权"
    }

    private func connectionError(_ error: Error) -> Error {
        let ns = error as NSError
        record("error", "\(ns.domain) / \(ns.code)")
        diagnosticDelegate.record(status: (socket.response as? HTTPURLResponse)?.statusCode,
                                  code: socket.closeCode.rawValue, reason: socket.closeReason)
        if Self.isUnauthorized(code: socket.closeCode, reason: socket.closeReason)
            || (socket.response as? HTTPURLResponse)?.statusCode == 401 {
            return MiaConnectionError.unauthorized
        }
        return socket.closeCode != .invalid ? MiaConnectionError.serverClosed : error
    }

    init(configuration: MiaWebSocketConfiguration, session: URLSession = .shared,
         onConnection: @escaping (Int?, Int?, Data?) -> Void = { _, _, _ in },
         onMessage: @escaping (String, String) -> Void = { _, _ in }) {
        diagnosticDelegate = MiaSocketDiagnosticsDelegate(update: onConnection)
        diagnosticUpdate = onMessage
        socket = session.webSocketTask(with: configuration.request)
        // Memory management can return 200 bounded records; audio frames stay capped below.
        socket.maximumMessageSize = 1_048_576
        socket.delegate = diagnosticDelegate
    }

    func open() {
        socket.resume()
    }

    func sendHello() async throws {
        try await sendText(MiaWireProtocol.hello())
    }

    func startListening(sessionID: String?, automatic: Bool = false) async throws {
        try await sendText(MiaWireProtocol.startListening(sessionID: sessionID, automatic: automatic))
    }

    func stopListening(sessionID: String?) async throws {
        try await sendText(MiaWireProtocol.stopListening(sessionID: sessionID))
    }

    func abort(sessionID: String?) async throws {
        try await sendText(MiaWireProtocol.abort(sessionID: sessionID))
    }

    func sendOpus(_ frame: Data) async throws {
        do { try await socket.send(.data(frame)) }
        catch { throw connectionError(error) }
    }

    func manageMemory(sessionID: String?, requestID: String, action: String,
                      fields: [String: Any]) async throws {
        var object = fields
        object["type"] = "mia_memory"
        object["session_id"] = sessionID ?? ""
        object["request_id"] = requestID
        object["action"] = action
        let data = try JSONSerialization.data(withJSONObject: object)
        guard data.count <= 8_192 else { throw MiaWireError.invalidMessage }
        try await sendText(data)
    }

    func receive() async throws -> MiaIncomingFrame {
        let message: URLSessionWebSocketTask.Message
        do { message = try await socket.receive() }
        catch { throw connectionError(error) }
        switch message {
        case .string(let text):
            guard text.utf8.count <= 1_048_576 else { throw MiaConnectionError.unexpectedMessage }
            if text == "认证失败" || text == "未授权" {
                record("message", "认证失败文本")
                record("error", "服务端设备认证失败")
                throw MiaConnectionError.unauthorized
            }
            let type = (try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any])?["type"] as? String
            guard type == "mia_memory" || text.utf8.count <= 65_536 else { throw MiaConnectionError.unexpectedMessage }
            let known = ["hello", "stt", "tts", "llm", "error", "mia_memory", "mia_authorization"]
            record("message", known.contains(type ?? "") ? type! : "未知文本消息")
            return .event(try MiaWireProtocol.parseServerEvent(Data(text.utf8)))
        case .data(let data):
            record("message", "Opus 二进制（\(data.count) 字节）")
            guard !data.isEmpty, data.count <= 4_000 else { throw MiaConnectionError.unexpectedMessage }
            return .opus(data)
        @unknown default:
            throw MiaConnectionError.unexpectedMessage
        }
    }

    func close() {
        socket.cancel(with: .normalClosure, reason: nil)
    }

    private func sendText(_ data: Data) async throws {
        guard let text = String(data: data, encoding: .utf8) else {
            throw MiaWireError.invalidMessage
        }
        do { try await socket.send(.string(text)) }
        catch { throw connectionError(error) }
    }
}
