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

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data),
                       .hello(sessionID: "s-1", sampleRate: 24_000))
    }

    func testRejectsWrongServerTransport() {
        let data = Data(#"{"type":"hello","transport":"mqtt"}"#.utf8)

        XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(data))
    }

    func testReadsServerSampleRateAndFallsBackForInvalidValue() throws {
        let valid = Data(#"{"type":"hello","transport":"websocket","audio_params":{"sample_rate":16000}}"#.utf8)
        let invalid = Data(#"{"type":"hello","transport":"websocket","audio_params":{"sample_rate":-1}}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(valid),
                       .hello(sessionID: nil, sampleRate: 16_000))
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(invalid),
                       .hello(sessionID: nil, sampleRate: 24_000))
    }

    func testParsesMiaSpeechSentence() throws {
        let data = Data(#"{"type":"tts","state":"sentence_start","text":"你好，我是 Mia。"}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data), .ttsSentence("你好，我是 Mia。"))
    }

    func testSendsManualListenControl() throws {
        let data = try MiaWireProtocol.startListening(sessionID: "s-1")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(object["type"] as? String, "listen")
        XCTAssertEqual(object["state"] as? String, "start")
        XCTAssertEqual(object["mode"] as? String, "manual")
        XCTAssertEqual(object["session_id"] as? String, "s-1")
    }

    func testSendsStopAndAbortControl() throws {
        let stop = try XCTUnwrap(JSONSerialization.jsonObject(
            with: MiaWireProtocol.stopListening(sessionID: "s-1")) as? [String: Any])
        let abort = try XCTUnwrap(JSONSerialization.jsonObject(
            with: MiaWireProtocol.abort(sessionID: "s-1")) as? [String: Any])

        XCTAssertEqual(stop["state"] as? String, "stop")
        XCTAssertEqual(stop["session_id"] as? String, "s-1")
        XCTAssertEqual(abort["type"] as? String, "abort")
        XCTAssertEqual(abort["session_id"] as? String, "s-1")
    }

    func testParsesSpeechLifecycleAndEmotion() throws {
        XCTAssertEqual(
            try MiaWireProtocol.parseServerEvent(Data(#"{"type":"tts","state":"start"}"#.utf8)),
            .ttsStart)
        XCTAssertEqual(
            try MiaWireProtocol.parseServerEvent(Data(#"{"type":"tts","state":"stop"}"#.utf8)),
            .ttsStop)
        XCTAssertEqual(
            try MiaWireProtocol.parseServerEvent(Data(#"{"type":"llm","emotion":"happy"}"#.utf8)),
            .emotion("happy"))
    }

    func testKeepsUserSpeechSeparateFromMiaSpeech() throws {
        let data = Data(#"{"type":"stt","text":"用户说的话"}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data), .userTranscript("用户说的话"))
    }
}
