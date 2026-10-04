import Foundation

enum MiaConnectionError: LocalizedError {
    case invalidEndpoint
    case unexpectedMessage
    case handshakeTimeout
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .invalidEndpoint: "请输入有效的 wss:// 服务端地址"
        case .unexpectedMessage: "服务端返回了无法识别的消息"
        case .handshakeTimeout: "服务端握手超时"
        case .unauthorized: "登录已失效，请重新登录"
        }
    }
}

struct MiaWebSocketConfiguration {
    let request: URLRequest

    init(endpoint: String, clientID: UUID, token: String?) throws {
        guard let url = URL(string: endpoint),
              url.scheme?.lowercased() == "wss",
              url.host != nil,
              url.fragment == nil,
              url.user == nil,
              url.password == nil else {
            throw MiaConnectionError.invalidEndpoint
        }

        var request = URLRequest(url: url)
        let identity = clientID.uuidString.lowercased()
        request.setValue("1", forHTTPHeaderField: "Protocol-Version")
        request.setValue("ios-" + identity, forHTTPHeaderField: "Device-Id")
        request.setValue(identity, forHTTPHeaderField: "Client-Id")
        if let token, !token.isEmpty {
            let authorization = token.contains(" ") ? token : "Bearer " + token
            request.setValue(authorization, forHTTPHeaderField: "Authorization")
        }
        self.request = request
    }
}

enum MiaIncomingFrame {
    case event(MiaServerEvent)
    case opus(Data)
}

final class MiaWebSocketTransport {
    private let socket: URLSessionWebSocketTask

    static func isUnauthorized(code: URLSessionWebSocketTask.CloseCode, reason: Data?) -> Bool {
        code == .policyViolation && reason.flatMap { String(data: $0, encoding: .utf8) } == "未授权"
    }

    private func connectionError(_ error: Error) -> Error {
        Self.isUnauthorized(code: socket.closeCode, reason: socket.closeReason)
            ? MiaConnectionError.unauthorized : error
    }

    init(configuration: MiaWebSocketConfiguration, session: URLSession = .shared) {
        socket = session.webSocketTask(with: configuration.request)
    }

    func open() {
        socket.resume()
    }

    func sendHello() async throws {
        try await sendText(MiaWireProtocol.hello())
    }

    func startListening(sessionID: String?) async throws {
        try await sendText(MiaWireProtocol.startListening(sessionID: sessionID))
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

    func receive() async throws -> MiaIncomingFrame {
        let message: URLSessionWebSocketTask.Message
        do { message = try await socket.receive() }
        catch { throw connectionError(error) }
        switch message {
        case .string(let text):
            return .event(try MiaWireProtocol.parseServerEvent(Data(text.utf8)))
        case .data(let data):
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
