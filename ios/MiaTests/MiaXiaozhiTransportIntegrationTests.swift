import XCTest
@testable import Mia

final class MiaXiaozhiTransportIntegrationTests: XCTestCase {
    private func configuration(token: String? = "fixture-only", query: String = "") throws -> MiaWebSocketConfiguration {
        try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/" + query,
                                     clientID: UUID(), token: token)
    }

    func testURLSessionHeadersHelloAndBidirectionalOpusEventOrder() async throws {
        let transport = MiaWebSocketTransport(configuration: try configuration())
        defer { transport.close() }
        transport.open()
        try await transport.sendHello()
        guard case .event(.hello(let id, let rate)) = try await transport.receive() else {
            return XCTFail("HTTP 101 alone is not a voice session")
        }
        XCTAssertEqual(id, "fixture-session")
        XCTAssertEqual(rate, 16_000)
        let codec = try MiaOpusCodec(inputSampleRate: 16_000, outputSampleRate: rate)
        let samples = (0..<960).map { Int16(sin(Double($0) * .pi * 2 * 440 / 16_000) * 6_000) }
        let packet = try codec.encode(samples)
        try await transport.startListening(sessionID: id)
        try await transport.sendOpus(packet)
        try await transport.stopListening(sessionID: id)
        for expected in [MiaServerEvent.userTranscript("用户识别文本"), .emotion("happy"), .ttsStart, .ttsSentence("Mia 回复")] {
            guard case .event(let actual) = try await transport.receive() else { return XCTFail("Wrong message order") }
            XCTAssertEqual(actual, expected)
        }
        guard case .opus(let received) = try await transport.receive() else { return XCTFail("No binary Opus") }
        XCTAssertEqual(received, packet)
        XCTAssertEqual(try codec.decode(received).count, 960)
        guard case .event(.ttsStop) = try await transport.receive() else { return XCTFail("No TTS stop") }
        try await transport.abort(sessionID: id)
        XCTAssertEqual(transport.diagnostics.httpStatus, 101)
    }

    func testAuthenticationFailureTextIsNotMalformedJSON() async throws {
        let transport = MiaWebSocketTransport(configuration: try configuration(token: nil))
        defer { transport.close() }
        transport.open()
        do {
            _ = try await transport.receive()
            XCTFail("Missing token accepted")
        } catch MiaConnectionError.unauthorized { }
        XCTAssertEqual(transport.diagnostics.lastMessage, "认证失败文本")
    }

    @MainActor
    func testServerCloseRecoversWithoutStartingMicrophoneAndExplicitDisconnectCancelsRetry() async throws {
        let voice = MiaVoiceSession()
        let config = try configuration(query: "?close_once=1")
        var calls = 0
        voice.connectionProvider = { calls += 1; return config }
        await voice.connect()
        for _ in 0..<60 {
            if calls >= 2 && voice.state == .ready { break }
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        XCTAssertGreaterThanOrEqual(calls, 2)
        XCTAssertEqual(voice.state, .ready)
        XCTAssertEqual(voice.audioLevel, 0)
        voice.disconnect()
        let afterDisconnect = calls
        try await Task.sleep(nanoseconds: 1_200_000_000)
        XCTAssertEqual(calls, afterDisconnect)
        XCTAssertEqual(voice.state, .disconnected)
    }
}
