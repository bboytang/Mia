import Foundation

enum MiaPrivateAuthorizationError: LocalizedError {
    case secureEndpointRequired, invalidCode, invalidResponse, http(Int)

    var errorDescription: String? {
        switch self {
        case .secureEndpointRequired: "请先配置同一服务器的 HTTPS OTA 和 WSS 地址"
        case .invalidCode: "授权码无效或已过期，请在智控台为本机重新生成"
        case .invalidResponse: "授权与本机设备不一致，请重新检查智控台授权"
        case .http(let status): "私有授权请求失败（HTTP \(status)）"
        }
    }
}

struct MiaPrivateDeviceGrant: Codable {
    let credential: String
    let expiresAt: Date
    let otaEndpoint: String
    let voiceEndpoint: String
    let deviceID: String
    let clientID: UUID

    func matches(ota: String, websocket: String, identity: MiaXiaozhiIdentity, now: Date = Date()) -> Bool {
        guard expiresAt > now, deviceID == identity.deviceID, clientID == identity.clientID,
              let endpoints = try? MiaPrivateAuthorizationClient.endpoints(ota: ota, websocket: websocket) else { return false }
        return otaEndpoint == endpoints.ota.absoluteString && voiceEndpoint == endpoints.voice.absoluteString
    }

    func header(for url: URL, device: String, client: UUID, now: Date = Date()) throws -> String {
        guard url.scheme?.lowercased() == "wss", voiceEndpoint == url.absoluteString,
              deviceID == device, clientID == client, expiresAt > now,
              credential.range(of: "^[A-Za-z0-9_-]{43}$", options: .regularExpression) != nil else {
            throw MiaConnectionError.privateAuthorizationRequired
        }
        return credential
    }
}

private final class MiaPrivateRedirectPolicy: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

enum MiaPrivateAuthorizationClient {
    static func endpoints(ota: String, websocket: String) throws -> (ota: URL, voice: URL) {
        guard let otaURL = try? MiaXiaozhiClient.validatedURL(ota, schemes: ["https"]),
              let voiceURL = try? MiaXiaozhiClient.validatedURL(websocket, schemes: ["wss"]),
              otaURL.host?.lowercased() == voiceURL.host?.lowercased(),
              otaURL.query == nil, voiceURL.query == nil,
              otaURL.path.hasSuffix("/ota/") || otaURL.path.hasSuffix("/ota") else {
            throw MiaPrivateAuthorizationError.secureEndpointRequired
        }
        return (otaURL, voiceURL)
    }

    static func request(ota: String, websocket: String, identity: MiaXiaozhiIdentity,
                        code: String? = nil, grant: MiaPrivateDeviceGrant? = nil) throws -> URLRequest {
        let urls = try endpoints(ota: ota, websocket: websocket)
        var components = URLComponents(url: urls.ota, resolvingAgainstBaseURL: false)!
        let path = components.path.hasSuffix("/") ? String(components.path.dropLast()) : components.path
        components.path = String(path.dropLast(4)) + "/device/mia-auth/" + (grant == nil ? "exchange" : "renew")
        guard let url = components.url else { throw MiaPrivateAuthorizationError.secureEndpointRequired }
        var body: [String: Any] = ["device_id": identity.deviceID,
                                   "client_id": identity.clientID.uuidString.lowercased()]
        if let grant {
            guard grant.matches(ota: ota, websocket: websocket, identity: identity) else {
                throw MiaConnectionError.privateAuthorizationRequired
            }
            body["private_credential"] = try grant.header(for: urls.voice, device: identity.deviceID, client: identity.clientID)
        } else {
            guard let code, code.range(of: "^[A-Za-z0-9_-]{22}$", options: .regularExpression) != nil else {
                throw MiaPrivateAuthorizationError.invalidCode
            }
            body["authorization_code"] = code
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 15
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        return request
    }

    static func parse(_ data: Data, ota: String, websocket: String, identity: MiaXiaozhiIdentity,
                      now: Date = Date()) throws -> MiaPrivateDeviceGrant {
        struct Scope: Decodable {
            let deviceId: String
            let clientId: String
            let personaId: String
            let expiresAt: String
        }
        struct Grant: Decodable {
            let privateCredential: String
            let expiresIn: Int
            let scope: Scope
        }
        struct Response: Decodable { let code: Int; let data: Grant? }
        guard data.count <= 65_536 else { throw MiaPrivateAuthorizationError.invalidResponse }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard let response = try? decoder.decode(Response.self, from: data) else {
            throw MiaPrivateAuthorizationError.invalidResponse
        }
        guard response.code == 0 else { throw MiaPrivateAuthorizationError.invalidCode }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let expiry = response.data.flatMap { formatter.date(from: $0.scope.expiresAt) }
        formatter.formatOptions = [.withInternetDateTime]
        guard let grant = response.data,
              let expiresAt = expiry ?? formatter.date(from: grant.scope.expiresAt), expiresAt > now,
              expiresAt.timeIntervalSince(now) <= 30 * 86_400 + 300,
              (1...2_592_000).contains(grant.expiresIn), grant.scope.personaId == "mia",
              grant.scope.deviceId == identity.deviceID,
              grant.scope.clientId == identity.clientID.uuidString.lowercased(),
              grant.privateCredential.range(of: "^[A-Za-z0-9_-]{43}$", options: .regularExpression) != nil else {
            throw MiaPrivateAuthorizationError.invalidResponse
        }
        let urls = try endpoints(ota: ota, websocket: websocket)
        return MiaPrivateDeviceGrant(credential: grant.privateCredential, expiresAt: expiresAt,
            otaEndpoint: urls.ota.absoluteString, voiceEndpoint: urls.voice.absoluteString,
            deviceID: identity.deviceID, clientID: identity.clientID)
    }

    static func exchange(ota: String, websocket: String, identity: MiaXiaozhiIdentity,
                         code: String? = nil, grant: MiaPrivateDeviceGrant? = nil) async throws -> MiaPrivateDeviceGrant {
        let request = try request(ota: ota, websocket: websocket, identity: identity, code: code, grant: grant)
        let session = URLSession(configuration: .ephemeral)
        defer { session.invalidateAndCancel() }
        let (data, response) = try await session.data(for: request, delegate: MiaPrivateRedirectPolicy())
        guard let http = response as? HTTPURLResponse else { throw MiaPrivateAuthorizationError.invalidResponse }
        guard http.statusCode == 200 else { throw MiaPrivateAuthorizationError.http(http.statusCode) }
        return try parse(data, ota: ota, websocket: websocket, identity: identity)
    }
}
