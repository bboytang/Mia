import XCTest
@testable import Youmi

final class YoumiClientTests: XCTestCase {
    private let endpoint = "wss://fixture.example/xiaozhi/v1/"
    private func body(activation: Bool = false, endpoint: String? = nil) throws -> Data {
        var value: [String: Any] = ["websocket": ["url": endpoint ?? self.endpoint, "token": "fixture-only"]]
        if activation { value["activation"] = ["code": "123456"] }
        return try JSONSerialization.data(withJSONObject: value)
    }

    func testIdentityPersistsAndRepairsInvalidStoredMAC() throws {
        let name = "YoumiIdentityTest-" + UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let first = YoumiIdentity(defaults: defaults)
        XCTAssertEqual(first, YoumiIdentity(defaults: defaults))
        XCTAssertTrue(YoumiIdentity.validDeviceID(first.deviceID))
        XCTAssertTrue(first.deviceID.hasPrefix("02:"))
        defaults.set("ios-invalid", forKey: "mia.xiaozhi.deviceID")
        let repaired = YoumiIdentity(defaults: defaults)
        XCTAssertEqual(repaired.clientID, first.clientID)
        XCTAssertEqual(repaired.deviceID, first.deviceID)
    }

    func testProductionDefaultsSupportPrivateAuthorizationOverTLS() throws {
        let endpoints = try YoumiPrivateAuthorizationClient.endpoints(
            ota: YoumiClient.defaultOTA, websocket: YoumiClient.defaultWebSocket)
        XCTAssertEqual(endpoints.ota.absoluteString, "https://43.143.230.174/xiaozhi/ota/")
        XCTAssertEqual(endpoints.voice.absoluteString, "wss://43.143.230.174:8000/xiaozhi/v1/")
        let request = try YoumiPrivateAuthorizationClient.request(ota: YoumiClient.defaultOTA,
            websocket: YoumiClient.defaultWebSocket, identity: YoumiIdentity(),
            code: "abcdefghijklmnopqrstuv")
        XCTAssertEqual(request.url?.absoluteString, "https://43.143.230.174/xiaozhi/device/mia-auth/exchange")
    }

    func testUpgradeMigratesOnlyOldBuiltInAddressesAndPreservesIdentity() throws {
        let name = "YoumiEndpointUpgrade-" + UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let identity = YoumiIdentity(defaults: defaults)
        defaults.set("ws://43.143.230.174:8000/xiaozhi/v1/", forKey: "mia.xiaozhi.websocketURL")
        defaults.set("http://43.143.230.174:8002/xiaozhi/ota/", forKey: "mia.xiaozhi.otaURL")
        YoumiClient.migrateLegacyEndpoints(in: defaults)
        YoumiClient.migrateLegacyEndpoints(in: defaults)
        XCTAssertEqual(defaults.string(forKey: "mia.xiaozhi.websocketURL"), YoumiClient.defaultWebSocket)
        XCTAssertEqual(defaults.string(forKey: "mia.xiaozhi.otaURL"), YoumiClient.defaultOTA)
        XCTAssertEqual(YoumiIdentity(defaults: defaults), identity)

        defaults.set("wss://custom.example/voice/", forKey: "mia.xiaozhi.websocketURL")
        defaults.set("https://custom.example/ota/", forKey: "mia.xiaozhi.otaURL")
        let before = defaults.dictionaryRepresentation()
        YoumiClient.migrateLegacyEndpoints(in: defaults)
        XCTAssertEqual(defaults.dictionaryRepresentation() as NSDictionary, before as NSDictionary)
    }

    func testOTARequestUsesMatchingIdentityAndActualClientCapabilities() throws {
        let identity = YoumiIdentity()
        let request = try YoumiClient.otaRequest(endpoint: "https://fixture.example/ota/", identity: identity)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Device-Id"), identity.deviceID)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Client-Id"), identity.clientID.uuidString.lowercased())
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let data = try XCTUnwrap(request.httpBody)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(object["mac_address"] as? String, identity.deviceID)
        XCTAssertEqual((object["application"] as? [String: Any])?["name"] as? String, "mia-ios")
        let hello = try XCTUnwrap(JSONSerialization.jsonObject(with: YoumiWireProtocol.hello()) as? [String: Any])
        XCTAssertNil(hello["features"])
    }

    func testOTAParsesActivationAndNeverAcceptsCredentialRedirectOrTLSDowngrade() throws {
        let config = try YoumiClient.parseOTA(body(activation: true), configuredEndpoint: endpoint)
        XCTAssertEqual(config.activationCode, "123456")
        XCTAssertEqual(config.token, "fixture-only")
        XCTAssertThrowsError(try YoumiClient.parseOTA(body(endpoint: "wss://other.example/"), configuredEndpoint: endpoint))
        XCTAssertThrowsError(try YoumiClient.parseOTA(body(endpoint: "ws://fixture.example/"), configuredEndpoint: endpoint))
        XCTAssertThrowsError(try YoumiClient.parseOTA(Data("{}".utf8), configuredEndpoint: endpoint))
        XCTAssertThrowsError(try YoumiClient.parseOTA(Data(repeating: 32, count: 65_537), configuredEndpoint: endpoint))
    }

    @MainActor
    func testDiscoveryRequiresBindingAndUsesFreshOTATokenAfterActivation() async throws {
        let client = YoumiClient()
        do {
            _ = try await client.discover(ota: "http://127.0.0.1:8770/ota/?activation=1", websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
            XCTFail("An unbound device must not enter the voice session")
        } catch YoumiError.activationRequired { }
        XCTAssertEqual(client.activationCode, "123456")
        let config = try await client.discover(ota: "http://127.0.0.1:8770/ota/", websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
        XCTAssertNil(client.activationCode)
        XCTAssertEqual(config.request.value(forHTTPHeaderField: "Authorization"), "Bearer fixture-only")
        XCTAssertEqual(config.request.value(forHTTPHeaderField: "Device-Id"), client.identity.deviceID)
    }

    @MainActor
    func testOTAFailureDoesNotFollowRedirectOrEchoBody() async throws {
        for status in [302, 401, 500] {
            let client = YoumiClient()
            do {
                _ = try await client.discover(ota: "http://127.0.0.1:8770/ota/?status=\(status)", websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
                XCTFail("Bad HTTP response accepted")
            } catch YoumiError.http(let actual) { XCTAssertEqual(actual, status) }
        }
    }

    func testNetworkRecoveryExcludesAuthenticationAndCancellation() {
        XCTAssertTrue(YoumiVoiceSession.shouldReconnect(YoumiConnectionError.serverClosed))
        XCTAssertTrue(YoumiVoiceSession.shouldReconnect(YoumiConnectionError.handshakeTimeout))
        XCTAssertFalse(YoumiVoiceSession.shouldReconnect(YoumiConnectionError.unauthorized))
        XCTAssertFalse(YoumiVoiceSession.shouldReconnect(YoumiError.activationRequired))
        XCTAssertFalse(YoumiVoiceSession.shouldReconnect(URLError(.cancelled)))
    }

    @MainActor
    func testCancelledDiscoveryCannotRestoreBindingOrConfiguration() async throws {
        let client = YoumiClient()
        let pending = Task {
            try await client.discover(ota: "http://127.0.0.1:8770/ota/?activation=1&delay=1",
                                      websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
        }
        try await Task.sleep(nanoseconds: 50_000_000)
        client.cancel()
        do { _ = try await pending.value; XCTFail("Cancelled discovery restored configuration") } catch { }
        XCTAssertNil(client.activationCode)
        XCTAssertFalse(client.checking)
        XCTAssertEqual(client.status, "配置已改变，请重新连接")
    }
}
