import XCTest
@testable import Mia

final class MiaWebSocketTransportTests: XCTestCase {
    func testRejectsInsecureAndMalformedEndpoints() {
        let id = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!

        XCTAssertThrowsError(try MiaWebSocketConfiguration(
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
        XCTAssertEqual(request.value(forHTTPHeaderField: "Device-Id"), "ios-" + id.uuidString.lowercased())
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret")
    }

    func testNoAuthorizationHeaderWhenTokenIsAbsent() throws {
        let config = try MiaWebSocketConfiguration(
            endpoint: "wss://example.com/", clientID: UUID(), token: nil)

        XCTAssertNil(config.request.value(forHTTPHeaderField: "Authorization"))
    }
}
