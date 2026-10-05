import Foundation
import XCTest
@testable import Mia

private final class AccountURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (Int, Data, TimeInterval))?
    private let lock = NSLock()
    private var stopped = false

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        do {
            let (status, data, delay) = try Self.handler!(request)
            DispatchQueue.global().asyncAfter(deadline: .now() + delay) { [self] in
                lock.lock()
                let cancelled = stopped
                lock.unlock()
                guard !cancelled else { return }
                let response = HTTPURLResponse(url: request.url!, statusCode: status,
                                               httpVersion: nil,
                                               headerFields: ["Content-Type": "application/json"])!
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
                client?.urlProtocol(self, didLoad: data)
                client?.urlProtocolDidFinishLoading(self)
            }
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {
        lock.lock()
        stopped = true
        lock.unlock()
    }

    static func body(_ request: URLRequest) -> Data {
        if let data = request.httpBody { return data }
        guard let stream = request.httpBodyStream else { return Data() }
        stream.open()
        defer { stream.close() }
        var result = Data()
        var buffer = [UInt8](repeating: 0, count: 1024)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count <= 0 { break }
            result.append(contentsOf: buffer.prefix(count))
        }
        return result
    }
}

final class MiaAccountAccessTests: XCTestCase {
    @MainActor
    func testExpiredLoginStopsActiveVoiceBeforeRequestingLogin() {
        let access = MiaAccountAccess(read: { self.old }, save: { _ in }, clear: {})
        var recordingOrPlaying = true
        let token = access.prepareVoice(endpoint: endpoint, maintenanceMode: false,
                                        legacyToken: "maintenance-test",
                                        now: Date(timeIntervalSince1970: 2_000_000_000)) {
            recordingOrPlaying = false
        }
        XCTAssertNil(token)
        XCTAssertFalse(recordingOrPlaying)
        XCTAssertEqual(access.credential, old, "Expiry must not erase credentials on a network failure")
        let activeToken = access.prepareVoice(endpoint: endpoint, maintenanceMode: false,
                                              legacyToken: nil,
                                              now: Date(timeIntervalSince1970: 1_900_000_000)) {
            XCTFail("A valid credential must preserve stop/interrupt routing")
        }
        XCTAssertEqual(activeToken, old.token)
    }
    private let endpoint = "wss://8kraw.cloud/xiaozhi/v1/"
    private let fakeToken = String(repeating: "a", count: 43)
    private var urlSession: URLSession!

    override func setUp() {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [AccountURLProtocol.self]
        urlSession = URLSession(configuration: config)
    }

    override func tearDown() {
        urlSession.invalidateAndCancel()
        AccountURLProtocol.handler = nil
    }

    private func fixture(username: String = "friend", expiry: Double = 2_000_000_000) throws -> Data {
        try JSONSerialization.data(withJSONObject: ["username": username, "token": fakeToken,
                                                    "expires_at": expiry])
    }

    private var old: MiaAccountCredential {
        MiaAccountCredential(username: "old_friend", token: String(repeating: "b", count: 43),
                             expiresAt: 2_000_000_000, origin: "https://8kraw.cloud")
    }

    func testOriginConversionAndCredentialNeverCrossesHostsOrPorts() throws {
        XCTAssertEqual(try MiaAccountAPI.origin(for: "wss://EXAMPLE.com:443/xiaozhi/v1/?q=1"),
                       "https://example.com")
        XCTAssertEqual(try MiaAccountAPI.origin(for: "wss://example.com:8443/path"),
                       "https://example.com:8443")
        for invalid in ["ws://example.com/", "https://example.com/", "wss://user@example.com/",
                        "wss://example.com/#fragment", "wss:///missing"] {
            XCTAssertThrowsError(try MiaAccountAPI.origin(for: invalid))
        }
        XCTAssertTrue(old.usable(endpoint: endpoint, now: Date(timeIntervalSince1970: 1_900_000_000)))
        XCTAssertFalse(old.usable(endpoint: "wss://other.example/", now: Date()))
        XCTAssertFalse(old.usable(endpoint: "wss://8kraw.cloud:8443/", now: Date()))
        XCTAssertFalse(old.usable(endpoint: endpoint, now: Date(timeIntervalSince1970: 2_000_000_000)))
    }

    func testRegistrationRequestPreservesPasswordAndParsesCompleteSession() async throws {
        let response = try fixture()
        AccountURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.absoluteString, "https://8kraw.cloud/api/auth/register")
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Cache-Control"), "no-store")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let body = try JSONSerialization.jsonObject(with: AccountURLProtocol.body(request)) as! [String: String]
            XCTAssertEqual(body, ["username": "Friend", "password": " preserve this password "])
            return (201, response, 0)
        }
        let item = try await MiaAccountAPI(session: urlSession).signIn(
            endpoint: endpoint, username: "Friend", password: " preserve this password ", register: true)
        XCTAssertEqual(item.username, "friend")
        XCTAssertEqual(item.token, fakeToken)
        XCTAssertEqual(item.origin, "https://8kraw.cloud")
        XCTAssertEqual(item.expiresAt, 2_000_000_000)
    }

    func testLoginUsesLoginRouteAndRejectsMalformedOrExpiredSessions() async throws {
        let invalid: [[String: Any]] = [[:], ["username": "friend", "token": "bad\nheader", "expires_at": 2_000_000_000],
                                       ["username": "friend", "token": fakeToken, "expires_at": 1],
                                       ["username": "", "token": fakeToken, "expires_at": 2_000_000_000]]
        for body in invalid {
            let data = try JSONSerialization.data(withJSONObject: body)
            AccountURLProtocol.handler = { request in
                XCTAssertEqual(request.url?.path, "/api/auth/login")
                return (200, data, 0)
            }
            do {
                _ = try await MiaAccountAPI(session: urlSession).signIn(
                    endpoint: endpoint, username: "friend", password: "test password 123", register: false)
                XCTFail("Invalid credential accepted")
            } catch { XCTAssertTrue(error is MiaAccountError) }
        }
    }

    func testHTTPUnauthorizedAndRateLimitAreExplicitServerErrors() async throws {
        for status in [401, 429] {
            AccountURLProtocol.handler = { _ in
                (status, Data("{\"error\":\"test_error\",\"message\":\"请稍后重试\"}".utf8), 0)
            }
            do {
                _ = try await MiaAccountAPI(session: urlSession).signIn(
                    endpoint: endpoint, username: "friend", password: "test password 123", register: false)
                XCTFail("HTTP error accepted")
            } catch {
                guard let accountError = error as? MiaAccountError,
                      case .server(let code, _) = accountError else { return XCTFail("Wrong error") }
                XCTAssertEqual(code, status)
            }
        }
    }

    func testCredentialBearingRequestsNeverFollowRedirects() {
        let task = urlSession.dataTask(with: URL(string: "https://8kraw.cloud/api/auth/logout")!)
        let response = HTTPURLResponse(url: task.originalRequest!.url!, statusCode: 302,
                                       httpVersion: nil, headerFields: ["Location": "https://other.example/"])!
        var proposed = URLRequest(url: URL(string: "https://other.example/")!)
        proposed.setValue("Bearer " + fakeToken, forHTTPHeaderField: "Authorization")
        var called = false
        MiaAccountRedirectPolicy().urlSession(urlSession, task: task,
            willPerformHTTPRedirection: response, newRequest: proposed) { request in
                called = true
                XCTAssertNil(request)
            }
        XCTAssertTrue(called)
        task.cancel()
    }

    @MainActor
    func testTLSFailureAndBadLoginRetainExistingCredential() async throws {
        let access = MiaAccountAccess(api: MiaAccountAPI(session: urlSession), read: { self.old },
                                     save: { _ in XCTFail("Must not save") }, clear: { XCTFail("Must not clear") })
        AccountURLProtocol.handler = { _ in throw URLError(.secureConnectionFailed) }
        do {
            try await access.signIn(endpoint: endpoint, username: "friend", password: "test password 123", register: false)
            XCTFail("TLS failure accepted")
        } catch { XCTAssertEqual((error as? URLError)?.code, .secureConnectionFailed) }
        XCTAssertEqual(access.credential, old)
        AccountURLProtocol.handler = { _ in (401, Data(), 0) }
        do {
            try await access.signIn(endpoint: endpoint, username: "friend", password: "test password 123", register: false)
            XCTFail("Wrong password accepted")
        } catch { XCTAssertTrue(error is MiaAccountError) }
        XCTAssertEqual(access.credential, old)
    }

    @MainActor
    func testFailedKeychainSaveDoesNotDeleteOrReplaceOldCredential() async throws {
        let response = try fixture()
        AccountURLProtocol.handler = { _ in (200, response, 0) }
        let access = MiaAccountAccess(api: MiaAccountAPI(session: urlSession), read: { self.old },
                                     save: { _ in throw NSError(domain: "test-storage", code: 1) },
                                     clear: { XCTFail("Must not delete before update") })
        do {
            try await access.signIn(endpoint: endpoint, username: "friend", password: "test password 123", register: false)
            XCTFail("Storage failure ignored")
        } catch { XCTAssertEqual((error as NSError).domain, "test-storage") }
        XCTAssertEqual(access.credential, old)
    }

    @MainActor
    func testCancelledLoginDoesNotSaveCredential() async throws {
        let started = expectation(description: "Request started")
        let response = try fixture()
        AccountURLProtocol.handler = { _ in started.fulfill(); return (200, response, 0.5) }
        let access = MiaAccountAccess(api: MiaAccountAPI(session: urlSession), read: { self.old },
                                     save: { _ in XCTFail("Cancelled login saved") }, clear: {})
        let task = Task { try await access.signIn(endpoint: endpoint, username: "friend",
                                                  password: "test password 123", register: false) }
        await fulfillment(of: [started], timeout: 2)
        task.cancel()
        do { try await task.value; XCTFail("Cancellation ignored") } catch {}
        XCTAssertEqual(access.credential, old)
    }

    @MainActor
    func testLogoutCapturesTokenBeforeClearingAndNeverFallsBackWhenOffline() async {
        var cleared = false
        var disconnectedWithOldSession = false
        let access = MiaAccountAccess(api: MiaAccountAPI(session: urlSession), read: { self.old },
                                     save: { _ in XCTFail("Must not restore") }, clear: { cleared = true })
        AccountURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/auth/logout")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer " + self.old.token)
            throw URLError(.notConnectedToInternet)
        }
        await access.logout(endpoint: endpoint) { disconnectedWithOldSession = access.credential == self.old }
        XCTAssertTrue(disconnectedWithOldSession)
        XCTAssertTrue(cleared)
        XCTAssertNil(access.credential)
        XCTAssertNotNil(access.warning)
        XCTAssertNil(access.token(endpoint: endpoint, maintenanceMode: false, legacyToken: "old-maintenance"))
        XCTAssertEqual(access.token(endpoint: endpoint, maintenanceMode: true, legacyToken: "old-maintenance"), "old-maintenance")
    }

    @MainActor
    func testLateLoginCannotRestoreSessionAfterLogout() async throws {
        let started = expectation(description: "Login started")
        let response = try fixture()
        AccountURLProtocol.handler = { request in
            if request.url?.path == "/api/auth/logout" { return (204, Data(), 0) }
            started.fulfill()
            return (200, response, 0.3)
        }
        let access = MiaAccountAccess(api: MiaAccountAPI(session: urlSession), read: { self.old },
                                     save: { _ in XCTFail("Late login restored") }, clear: {})
        let login = Task { try await access.signIn(endpoint: endpoint, username: "friend",
                                                   password: "test password 123", register: false) }
        await fulfillment(of: [started], timeout: 2)
        await access.logout(endpoint: endpoint, disconnect: {})
        do { try await login.value; XCTFail("Late login accepted") } catch { XCTAssertTrue(error is CancellationError) }
        XCTAssertNil(access.credential)
        XCTAssertNil(access.warning)
    }

    @MainActor
    func testDefiniteRejectionClearsOnlyMatchingOriginAndCannotUseLegacyImplicitly() {
        var cleared = false
        let access = MiaAccountAccess(read: { self.old }, save: { _ in }, clear: { cleared = true })
        XCTAssertNil(access.token(endpoint: "wss://other.example/", maintenanceMode: false, legacyToken: "legacy"))
        access.invalidate(endpoint: "wss://other.example/")
        XCTAssertEqual(access.credential, old)
        XCTAssertFalse(cleared)
        access.invalidate(endpoint: endpoint)
        XCTAssertNil(access.credential)
        XCTAssertTrue(cleared)
        XCTAssertNil(access.token(endpoint: endpoint, maintenanceMode: false, legacyToken: "legacy"))
    }

    func testRealKeychainSessionRoundTripAndUpdate() throws {
        let existing = MiaTokenStore.readAccount()
        defer {
            if let existing { try? MiaTokenStore.saveAccount(existing) }
            else { try? MiaTokenStore.clearAccount() }
        }
        try MiaTokenStore.saveAccount(old)
        XCTAssertEqual(MiaTokenStore.readAccount(), old)
        let replacement = MiaAccountCredential(username: "new_friend", token: fakeToken,
                                               expiresAt: 2_000_000_000, origin: "https://8kraw.cloud")
        try MiaTokenStore.saveAccount(replacement)
        XCTAssertEqual(MiaTokenStore.readAccount(), replacement)
        try MiaTokenStore.clearAccount()
        XCTAssertNil(MiaTokenStore.readAccount())
    }
}
