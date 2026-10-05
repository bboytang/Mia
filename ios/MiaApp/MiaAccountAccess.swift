import Foundation
import Combine

struct MiaAccountCredential: Codable, Equatable {
    let username: String
    let token: String
    let expiresAt: Double
    let origin: String

    func usable(endpoint: String, now: Date = Date()) -> Bool {
        expiresAt > now.timeIntervalSince1970 && origin == (try? MiaAccountAPI.origin(for: endpoint))
    }
}

enum MiaAccountError: LocalizedError {
    case invalidResponse
    case server(status: Int, message: String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: "服务器返回了无效的登录信息"
        case .server(_, let message): message
        }
    }
}

final class MiaAccountRedirectPolicy: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

struct MiaAccountAPI {
    var session: URLSession = .shared
    private let redirects = MiaAccountRedirectPolicy()

    init(session: URLSession = .shared) { self.session = session }

    static func origin(for endpoint: String) throws -> String {
        guard var components = URLComponents(string: endpoint),
              components.scheme?.lowercased() == "wss",
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              components.fragment == nil else { throw MiaConnectionError.invalidEndpoint }
        components.scheme = "https"
        components.host = host.lowercased()
        if components.port == 443 { components.port = nil }
        components.path = ""
        components.query = nil
        guard let url = components.url else { throw MiaConnectionError.invalidEndpoint }
        return url.absoluteString
    }

    private func request(origin: String, action: String) throws -> URLRequest {
        guard let url = URL(string: origin + "/api/auth/" + action) else {
            throw MiaConnectionError.invalidEndpoint
        }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        request.httpMethod = "POST"
        request.httpShouldHandleCookies = false
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
        return request
    }

    private func response(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        let (data, response) = try await session.data(for: request, delegate: redirects)
        guard let response = response as? HTTPURLResponse else { throw MiaAccountError.invalidResponse }
        guard response.statusCode == expectedStatus else {
            struct Failure: Decodable { let message: String }
            let message = (try? JSONDecoder().decode(Failure.self, from: data))?.message
            throw MiaAccountError.server(status: response.statusCode,
                                         message: message ?? "账号请求失败，请稍后再试")
        }
        return data
    }

    func signIn(endpoint: String, username: String, password: String,
                register: Bool) async throws -> MiaAccountCredential {
        let origin = try Self.origin(for: endpoint)
        var request = try request(origin: origin, action: register ? "register" : "login")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["username": username, "password": password])
        let data = try await response(request, expectedStatus: register ? 201 : 200)
        struct SessionResponse: Decodable {
            let username: String
            let token: String
            let expires_at: Double
        }
        guard let item = try? JSONDecoder().decode(SessionResponse.self, from: data),
              !item.username.isEmpty, item.username.count <= 32,
              (32...256).contains(item.token.utf8.count),
              item.token.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0)
                  || (97...122).contains($0) || $0 == 45 || $0 == 95 }),
              item.expires_at.isFinite, item.expires_at > Date().timeIntervalSince1970 else {
            throw MiaAccountError.invalidResponse
        }
        return MiaAccountCredential(username: item.username, token: item.token,
                                    expiresAt: item.expires_at, origin: origin)
    }

    func logout(endpoint: String, credential: MiaAccountCredential) async throws {
        let origin = try Self.origin(for: endpoint)
        guard credential.origin == origin else { throw MiaConnectionError.invalidEndpoint }
        var request = try request(origin: origin, action: "logout")
        request.setValue("Bearer " + credential.token, forHTTPHeaderField: "Authorization")
        _ = try await response(request, expectedStatus: 204)
    }
}

@MainActor
final class MiaAccountAccess: ObservableObject {
    @Published private(set) var credential: MiaAccountCredential?
    @Published var warning: String?
    private let api: MiaAccountAPI
    private let save: (MiaAccountCredential) throws -> Void
    private let clear: () throws -> Void
    private var loginGeneration = UUID()

    init(api: MiaAccountAPI = MiaAccountAPI(),
         read: () -> MiaAccountCredential? = MiaTokenStore.readAccount,
         save: @escaping (MiaAccountCredential) throws -> Void = MiaTokenStore.saveAccount,
         clear: @escaping () throws -> Void = MiaTokenStore.clearAccount) {
        self.api = api
        self.save = save
        self.clear = clear
        credential = read()
    }

    func token(endpoint: String, maintenanceMode: Bool, legacyToken: String?, now: Date = Date()) -> String? {
        if maintenanceMode { return legacyToken }
        guard let credential, credential.usable(endpoint: endpoint, now: now) else { return nil }
        return credential.token
    }

    func prepareVoice(endpoint: String, maintenanceMode: Bool, legacyToken: String?,
                      now: Date = Date(), disconnect: () -> Void) -> String? {
        let available = token(endpoint: endpoint, maintenanceMode: maintenanceMode,
                              legacyToken: legacyToken, now: now)
        if available == nil { disconnect() }
        return available
    }

    func signIn(endpoint: String, username: String, password: String, register: Bool) async throws {
        let generation = UUID()
        loginGeneration = generation
        let item = try await api.signIn(endpoint: endpoint, username: username,
                                        password: password, register: register)
        try Task.checkCancellation()
        guard generation == loginGeneration else { throw CancellationError() }
        try save(item)
        credential = item
        warning = nil
    }

    func cancelSignIn() { loginGeneration = UUID() }

    func invalidate(endpoint: String) {
        guard credential?.origin == (try? MiaAccountAPI.origin(for: endpoint)) else { return }
        cancelSignIn()
        credential = nil
        do { try clear() }
        catch { warning = "登录已失效，但本机凭据清理失败。" }
    }

    func logout(endpoint: String, disconnect: () -> Void) async {
        let previous = credential
        cancelSignIn()
        disconnect()
        credential = nil
        warning = nil
        do { try clear() }
        catch { warning = "本机已退出，但钥匙串凭据清理失败。" }
        if let previous {
            do { try await api.logout(endpoint: endpoint, credential: previous) }
            catch {
                warning = warning == nil ? "本机已退出，但服务端会话撤销未确认。"
                    : "本机已退出，但钥匙串清理失败，服务端会话撤销也未确认。"
            }
        }
    }
}
