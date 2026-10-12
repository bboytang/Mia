import XCTest
@testable import Mia

final class MiaWebSocketTransportTests: XCTestCase {
    func testOnlyDefinitiveUnauthorizedCloseInvalidatesLogin() {
        XCTAssertTrue(MiaWebSocketTransport.isUnauthorized(code: .policyViolation, reason: Data("未授权".utf8)))
        XCTAssertFalse(MiaWebSocketTransport.isUnauthorized(code: .policyViolation, reason: Data("无效握手".utf8)))
        XCTAssertFalse(MiaWebSocketTransport.isUnauthorized(code: .normalClosure, reason: Data("未授权".utf8)))
        XCTAssertFalse(MiaWebSocketTransport.isUnauthorized(code: .invalid, reason: nil))
    }
    func testAcceptsWSButRejectsMalformedAndCredentialURLs() {
        let id = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!

        XCTAssertNoThrow(try MiaWebSocketConfiguration(
            endpoint: "ws://example.com/xiaozhi/v1/", clientID: id, token: nil))
        XCTAssertThrowsError(try MiaWebSocketConfiguration(
            endpoint: "https://example.com/xiaozhi/v1/", clientID: id, token: nil))
        XCTAssertThrowsError(try MiaWebSocketConfiguration(
            endpoint: "wss://example.com/path#fragment", clientID: id, token: nil))
    }

    func testHandshakeUsesStableMobileIdentityAndBearerToken() throws {
        let id = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!
        let config = try MiaWebSocketConfiguration(
            endpoint: "wss://example.com/xiaozhi/v1/", clientID: id, token: "secret")
        let request = config.request

        XCTAssertEqual(request.url?.absoluteString, "wss://example.com/xiaozhi/v1/")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Protocol-Version"), "1")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Client-Id"), id.uuidString.lowercased())
        XCTAssertEqual(request.value(forHTTPHeaderField: "Device-Id"), "02:11:11:11:11:22")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret")
    }

    func testRejectsInvalidDeviceAndCredentialsInURLOrHeaders() {
        XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: "wss://example.com/", clientID: UUID(), token: nil, deviceID: "ios-invalid"))
        XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: "wss://user:pass@example.com/", clientID: UUID(), token: nil))
        XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: "wss://example.com/?authorization=private", clientID: UUID(), token: nil))
        for token in ["x\rInjected: x", "x\nInjected: x", "x\r\nInjected: x"] {
            XCTAssertThrowsError(try MiaWebSocketConfiguration(endpoint: "wss://example.com/", clientID: UUID(), token: token))
        }
    }

    func testCloseReasonRedactsUnknownText() {
        XCTAssertEqual(MiaConnectionDiagnostics.safeReason(Data("private credential".utf8)), "内容已隐藏（18 字节）")
        XCTAssertEqual(MiaConnectionDiagnostics.safeReason(Data("认证失败".utf8)), "认证失败")
        XCTAssertEqual(MiaConnectionDiagnostics.safeReason(nil), "无关闭原因")
    }

    func testNoAuthorizationHeaderWhenTokenIsAbsent() throws {
        let config = try MiaWebSocketConfiguration(
            endpoint: "wss://example.com/", clientID: UUID(), token: nil)

        XCTAssertNil(config.request.value(forHTTPHeaderField: "Authorization"))
    }
}
