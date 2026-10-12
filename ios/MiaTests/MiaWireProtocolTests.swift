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
        let data = Data(#"{"type":"hello","transport":"websocket","session_id":"s-1","audio_params":{"format":"opus","sample_rate":24000,"channels":1,"frame_duration":60}}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data),
                       .hello(sessionID: "s-1", sampleRate: 24_000))
    }

    func testRejectsWrongServerTransport() {
        let data = Data(#"{"type":"hello","transport":"mqtt"}"#.utf8)

        XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(data))
    }

    func testRequiresSessionAndSupportedAudioParameters() throws {
        let valid = Data(#"{"type":"hello","transport":"websocket","session_id":"s","audio_params":{"format":"opus","sample_rate":16000,"channels":1,"frame_duration":60}}"#.utf8)
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(valid), .hello(sessionID: "s", sampleRate: 16_000))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: valid) as? [String: Any])
        object.removeValue(forKey: "session_id")
        XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(JSONSerialization.data(withJSONObject: object)))
        object["session_id"] = "s"
        for audio in [["format": "pcm", "sample_rate": 16000, "channels": 1, "frame_duration": 60],
                      ["format": "opus", "sample_rate": -1, "channels": 1, "frame_duration": 60],
                      ["format": "opus", "sample_rate": 16000, "channels": 2, "frame_duration": 60]] as [[String: Any]] {
            object["audio_params"] = audio
            XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(JSONSerialization.data(withJSONObject: object)))
        }
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
            try MiaWireProtocol.parseServerEvent(Data(#"{"type":"llm","text":"Mia 回复文本"}"#.utf8)),
            .assistantText("Mia 回复文本"))
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

    func testIgnoresUnknownMessageAndRejectsMalformedJSON() throws {
        XCTAssertEqual(
            try MiaWireProtocol.parseServerEvent(Data(#"{"type":"custom","value":1}"#.utf8)),
            .other)
        XCTAssertThrowsError(try MiaWireProtocol.parseServerEvent(Data("{".utf8)))
    }

    func testParsesServerErrorForUserFeedback() throws {
        let data = Data(#"{"type":"error","message":"没有听清，请再说一次"}"#.utf8)

        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(data),
                       .serverError("没有听清，请再说一次"))
    }
}
