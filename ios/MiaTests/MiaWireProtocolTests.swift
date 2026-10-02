import XCTest
@testable import Mia

final class MiaWireProtocolTests: XCTestCase {
    func testHelloAdvertisesWebSocketAndOpus() throws {
        let data = try MiaWireProtocol.hello()
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let audio = try XCTUnwrap(object["audio_params"] as? [String: Any])

        XCTAssertEqual(object["type"] as? String, "hello")
        XCTAssertEqual(object["transport"] as? String, "websocket")
        XCTAssertEqual(object["version"] as? Int, 1)
        XCTAssertEqual(audio["format"] as? String, "opus")
        XCTAssertEqual(audio["sample_rate"] as? Int, 16_000)
        XCTAssertEqual(audio["channels"] as? Int, 1)
        XCTAssertEqual(audio["frame_duration"] as? Int, 60)
    }

    func testAcceptsServerHelloWithSessionId() throws {
        let data = Data(#"{"type":"hello","transport":"websocket","session_id":"s-1"}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data), .hello(sessionID: "s-1"))
    }

    func testRejectsWrongServerTransport() {
        let data = Data(#"{"type":"hello","transport":"mqtt"}"#.utf8)

        XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(data))
    }

    func testParsesMiaSpeechSentence() throws {
        let data = Data(#"{"type":"tts","state":"sentence_start","text":"你好，我是 Mia。"}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data), .ttsSentence("你好，我是 Mia。"))
    }
}
