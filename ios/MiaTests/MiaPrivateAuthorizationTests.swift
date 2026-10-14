import XCTest
@testable import Mia

final class MiaPrivateAuthorizationTests: XCTestCase {
    private let ota = "https://fixture.example:8002/xiaozhi/ota/"
    private let voice = "wss://fixture.example:8000/xiaozhi/v1/"
    private let token = String(repeating: "a", count: 43)
    private let code = String(repeating: "b", count: 22)

    private func response(identity: MiaXiaozhiIdentity, fields: [String: Any] = [:]) throws -> Data {
        var scope: [String: Any] = ["device_id": identity.deviceID,
            "client_id": identity.clientID.uuidString.lowercased(), "persona_id": "mia",
            "expires_at": ISO8601DateFormatter().string(from: Date().addingTimeInterval(3600))]
        scope.merge(fields) { _, replacement in replacement }
        return try JSONSerialization.data(withJSONObject: ["code": 0, "data": [
            "private_credential": token, "expires_in": 3600, "scope": scope]])
    }

    func testExchangeUsesExistingIdentityAndNeverPutsPrivateProofInURLOrLegacyHeader() throws {
        let identity = MiaXiaozhiIdentity()
        let request = try MiaPrivateAuthorizationClient.request(ota: ota, websocket: voice, identity: identity, code: code)
        XCTAssertEqual(request.url?.absoluteString, "https://fixture.example:8002/xiaozhi/device/mia-auth/exchange")
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(request.url?.query)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: XCTUnwrap(request.httpBody)) as? [String: Any])
        XCTAssertEqual(body["device_id"] as? String, identity.deviceID)
        XCTAssertEqual(body["client_id"] as? String, identity.clientID.uuidString.lowercased())
        XCTAssertEqual(body["authorization_code"] as? String, code)
        XCTAssertNil(body["private_credential"])
    }

    func testExchangeRejectsInsecureCrossServerAndCredentialURLsBeforeSending() {
        let identity = MiaXiaozhiIdentity()
        for (testOTA, testVoice) in [(ota.replacingOccurrences(of: "https:", with: "http:"), voice),
                                    (ota, voice.replacingOccurrences(of: "wss:", with: "ws:")),
                                    (ota, "wss://other.example/xiaozhi/v1/"),
                                    (ota + "?authorization_code=" + code, voice),
                                    (ota, voice + "?mia-private-credential=" + token),
                                    ("https://fixture.example/unrelated/", voice)] {
            XCTAssertThrowsError(try MiaPrivateAuthorizationClient.request(ota: testOTA, websocket: testVoice,
                                                                         identity: identity, code: code))
        }
        for invalid in ["", "123456", code + "\n", String(repeating: ".", count: 22)] {
            XCTAssertThrowsError(try MiaPrivateAuthorizationClient.request(ota: ota, websocket: voice, identity: identity, code: invalid))
        }
    }

    func testVerifiedGrantIsPinnedToVoiceAddressDeviceClientAndExpiry() throws {
        let identity = MiaXiaozhiIdentity()
        let grant = try MiaPrivateAuthorizationClient.parse(response(identity: identity), ota: ota, websocket: voice, identity: identity)
        XCTAssertTrue(grant.matches(ota: ota, websocket: voice, identity: identity))
        XCTAssertFalse(grant.matches(ota: ota, websocket: voice, identity: identity, now: grant.expiresAt))
        let config = try MiaWebSocketConfiguration(endpoint: voice, clientID: identity.clientID,
            token: "legacy-fixture", deviceID: identity.deviceID, privateGrant: grant)
        XCTAssertEqual(config.request.value(forHTTPHeaderField: "Mia-Private-Credential"), token)
        XCTAssertEqual(config.request.value(forHTTPHeaderField: "Authorization"), "Bearer legacy-fixture")
        for endpoint in [voice.replacingOccurrences(of: "wss:", with: "ws:"),
                         "wss://other.example:8000/xiaozhi/v1/", "wss://fixture.example:9999/xiaozhi/v1/",
                         "wss://fixture.example:8000/other/"] {
            XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: endpoint, clientID: identity.clientID,
                                                              token: nil, deviceID: identity.deviceID, privateGrant: grant))
        }
        XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: voice, clientID: UUID(), token: nil,
                                                          deviceID: identity.deviceID, privateGrant: grant))
        for fields in [["device_id": "02:00:00:00:00:00"], ["client_id": "other"],
                       ["persona_id": "other"], ["expires_at": "2020-01-01T00:00:00Z"]] as [[String: Any]] {
            XCTAssertThrowsError(try MiaPrivateAuthorizationClient.parse(response(identity: identity, fields: fields),
                                                                         ota: ota, websocket: voice, identity: identity))
        }
    }

    func testPrivateKeychainPersistenceRenewalAndRemovalKeepDeviceBinding() throws {
        let identity = MiaXiaozhiIdentity()
        let grant = try MiaPrivateAuthorizationClient.parse(response(identity: identity), ota: ota, websocket: voice, identity: identity)
        try MiaTokenStore.clearPrivateGrant()
        defer { try? MiaTokenStore.clearPrivateGrant() }
        try MiaTokenStore.savePrivateGrant(grant)
        let saved = try XCTUnwrap(MiaTokenStore.readPrivateGrant())
        XCTAssertEqual(saved.credential, token)
        XCTAssertEqual(saved.deviceID, identity.deviceID)
        let renewal = try MiaPrivateAuthorizationClient.request(ota: ota, websocket: voice, identity: identity, grant: saved)
        XCTAssertEqual(renewal.url?.path, "/xiaozhi/device/mia-auth/renew")
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: XCTUnwrap(renewal.httpBody)) as? [String: Any])
        XCTAssertEqual(body["private_credential"] as? String, token)
        XCTAssertNil(body["authorization_code"])
        XCTAssertEqual(identity, MiaXiaozhiIdentity())
        try MiaTokenStore.clearPrivateGrant()
        XCTAssertNil(MiaTokenStore.readPrivateGrant())
        XCTAssertEqual(identity, MiaXiaozhiIdentity())
    }
}
