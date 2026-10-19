import Foundation
import Combine

enum YoumiError: LocalizedError {
    case invalidIdentity, invalidResponse, activationRequired, http(Int), endpointMismatch

    var errorDescription: String? {
        switch self {
        case .invalidIdentity: "Youmi设备标识无效"
        case .invalidResponse: "OTA 没有返回有效的Youmi连接配置"
        case .activationRequired: "请先在智控台将本机激活码绑定到智能体，再检查绑定状态"
        case .http(let status): "OTA 请求失败（HTTP \(status)）"
        case .endpointMismatch: "OTA 返回的服务器与配置不一致，或尝试降级安全连接，请检查地址"
        }
    }
}

struct YoumiIdentity: Equatable {
    let clientID: UUID
    let deviceID: String

    static func deviceID(for id: UUID) -> String {
        let hex = Array(id.uuidString.replacingOccurrences(of: "-", with: "").lowercased())
        return "02:" + stride(from: 0, to: 10, by: 2)
            .map { String(hex[$0...($0 + 1)]) }.joined(separator: ":")
    }

    static func validDeviceID(_ value: String) -> Bool {
        value.range(of: "^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", options: .regularExpression) != nil
    }

    init(defaults: UserDefaults = .standard) {
        let id = defaults.string(forKey: "mia.clientID").flatMap(UUID.init(uuidString:)) ?? UUID()
        defaults.set(id.uuidString, forKey: "mia.clientID")
        clientID = id
        let stored = defaults.string(forKey: "mia.xiaozhi.deviceID") ?? ""
        deviceID = Self.validDeviceID(stored) ? stored.lowercased() : Self.deviceID(for: id)
        defaults.set(deviceID, forKey: "mia.xiaozhi.deviceID")
    }
}

struct YoumiConfiguration {
    let endpoint: String
    let token: String?
    let activationCode: String?
}

private final class YoumiOTARedirectPolicy: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

@MainActor
final class YoumiClient: ObservableObject {
    nonisolated static let defaultWebSocket = "wss://43.143.230.174:8000/xiaozhi/v1/"
    nonisolated static let defaultOTA = "https://43.143.230.174/xiaozhi/ota/"
    let identity: YoumiIdentity
    @Published private(set) var activationCode: String?
    @Published private(set) var status = "尚未发现设备配置"
    @Published private(set) var checking = false
    private let session: URLSession
    private let redirectPolicy = YoumiOTARedirectPolicy()
    private var generation = UUID()
    private var discoveryTask: Task<(Data, URLResponse), Error>?

    init(identity: YoumiIdentity = YoumiIdentity()) {
        self.identity = identity
        self.session = URLSession(configuration: .ephemeral)
    }

    nonisolated static func migrateLegacyEndpoints(in defaults: UserDefaults) {
        // Only replace former built-in addresses; preserve custom servers and identity.
        if defaults.string(forKey: "mia.xiaozhi.websocketURL") == "ws://43.143.230.174:8000/xiaozhi/v1/" {
            defaults.set(defaultWebSocket, forKey: "mia.xiaozhi.websocketURL")
        }
        if defaults.string(forKey: "mia.xiaozhi.otaURL") == "http://43.143.230.174:8002/xiaozhi/ota/" {
            defaults.set(defaultOTA, forKey: "mia.xiaozhi.otaURL")
        }
    }

    nonisolated static func validatedURL(_ endpoint: String, schemes: [String]) throws -> URL {
        guard endpoint.count <= 4096, let url = URL(string: endpoint),
              let scheme = url.scheme?.lowercased(), schemes.contains(scheme),
              let host = url.host, !host.isEmpty, url.user == nil, url.password == nil,
              url.fragment == nil,
              !(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? [])
                .contains(where: { ["authorization", "token", "device-id", "client-id", "mia-private-credential",
                                    "private_credential", "authorization_code"].contains($0.name.lowercased()) }) else {
            throw YoumiConnectionError.invalidEndpoint
        }
        return url
    }

    nonisolated static func otaRequest(endpoint: String, identity: YoumiIdentity) throws -> URLRequest {
        guard YoumiIdentity.validDeviceID(identity.deviceID) else { throw YoumiError.invalidIdentity }
        var request = URLRequest(url: try validatedURL(endpoint, schemes: ["http", "https"]))
        request.httpMethod = "POST"
        request.timeoutInterval = 15
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue(identity.deviceID, forHTTPHeaderField: "Device-Id")
        request.setValue(identity.clientID.uuidString.lowercased(), forHTTPHeaderField: "Client-Id")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "version": 2, "mac_address": identity.deviceID,
            "uuid": identity.clientID.uuidString.lowercased(),
            "application": ["name": "mia-ios", "version": "0.1.0"],
            "board": ["type": "mia-ios"]
        ])
        return request
    }

    nonisolated static func parseOTA(_ data: Data, configuredEndpoint: String) throws -> YoumiConfiguration {
        guard data.count <= 65_536,
              let body = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              body["error"] == nil,
              let websocket = body["websocket"] as? [String: Any],
              let endpoint = websocket["url"] as? String else { throw YoumiError.invalidResponse }
        let url = try validatedURL(endpoint, schemes: ["ws", "wss"])
        let configured = try validatedURL(configuredEndpoint, schemes: ["ws", "wss"])
        guard url.host?.lowercased() == configured.host?.lowercased(),
              configured.scheme?.lowercased() != "wss" || url.scheme?.lowercased() == "wss" else { throw YoumiError.endpointMismatch }
        let token = websocket["token"] as? String
        guard websocket["token"] == nil || websocket["token"] is String else { throw YoumiError.invalidResponse }
        guard token == nil || (token!.count <= 4096 && !token!.contains(where: { $0.isWhitespace })) else {
            throw YoumiError.invalidResponse
        }
        let activation = body["activation"] as? [String: Any]
        let code = activation?["code"] as? String
        guard body["activation"] == nil || code != nil else { throw YoumiError.invalidResponse }
        if let code, code.range(of: "^[0-9]{6}$", options: .regularExpression) == nil {
            throw YoumiError.invalidResponse
        }
        return YoumiConfiguration(endpoint: configuredEndpoint, token: token?.isEmpty == false ? token : nil,
                                       activationCode: code)
    }

    func cancelDiscovery() {
        discoveryTask?.cancel()
        discoveryTask = nil
        generation = UUID()
        checking = false
    }

    func cancel() {
        cancelDiscovery()
        activationCode = nil
        status = "配置已改变，请重新连接"
    }

    func discover(ota: String, websocket: String) async throws -> YoumiWebSocketConfiguration {
        discoveryTask?.cancel()
        let current = UUID()
        generation = current
        checking = true
        defer { if generation == current { checking = false; discoveryTask = nil } }
        do {
            let request = try Self.otaRequest(endpoint: ota, identity: identity)
            let session = self.session
            let policy = redirectPolicy
            let task = Task { try await session.data(for: request, delegate: policy) }
            discoveryTask = task
            let (data, response) = try await withTaskCancellationHandler(operation: {
                try await task.value
            }, onCancel: { task.cancel() })
            try Task.checkCancellation()
            guard generation == current else { throw CancellationError() }
            guard let http = response as? HTTPURLResponse else { throw YoumiError.invalidResponse }
            guard http.statusCode == 200 else { throw YoumiError.http(http.statusCode) }
            let config = try Self.parseOTA(data, configuredEndpoint: websocket)
            activationCode = config.activationCode
            if config.activationCode != nil {
                status = "等待在智控台绑定智能体"
                throw YoumiError.activationRequired
            }
            var privateGrant = YoumiTokenStore.readPrivateGrant()
            if privateGrant?.matches(ota: ota, websocket: websocket, identity: identity) != true {
                privateGrant = nil
            }
            if let grant = privateGrant, grant.expiresAt.timeIntervalSinceNow < 86_400 {
                let renewed = try await YoumiPrivateAuthorizationClient.exchange(ota: ota, websocket: websocket,
                                                                               identity: identity, grant: grant)
                guard generation == current else { throw CancellationError() }
                try YoumiTokenStore.savePrivateGrant(renewed)
                privateGrant = renewed
            }
            status = "设备配置已就绪"
            return try YoumiWebSocketConfiguration(endpoint: config.endpoint, clientID: identity.clientID,
                                                  token: config.token, deviceID: identity.deviceID, privateGrant: privateGrant)
        } catch {
            if generation == current, activationCode == nil {
                status = "OTA 发现失败，请检查地址和网络"
            }
            throw error
        }
    }

    deinit {
        discoveryTask?.cancel()
        session.invalidateAndCancel()
    }
}
