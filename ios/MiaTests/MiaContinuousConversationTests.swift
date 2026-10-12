import XCTest
@testable import Mia

private final class ConversationAudioStub: MiaConversationAudio {
    var microphone: (([Int16], UUID) -> Void)?
    var playback: ((Double, Float, UUID) -> Void)?
    var speech: ((UUID) -> Void)?
    var capture = UUID()
    var rounds = 0
    var muted = false
    var stopped = false
    var interruptions = 0
    var completions: [UUID] = []

    func start(outputSampleRate: Int, onMicrophoneFrame: @escaping ([Int16], UUID) -> Void,
               onPlaybackFrame: @escaping (Double, Float, UUID) -> Void,
               onSpeechActivity: @escaping (UUID) -> Void) throws {
        microphone = onMicrophoneFrame; playback = onPlaybackFrame; speech = onSpeechActivity
    }
    func play(_ samples: [Int16], generation: UUID) throws { completions.append(generation) }
    func interruptPlayback() { interruptions += 1 }
    func stop() { stopped = true; muted = true }
    func takeFinalMicrophoneFrame() -> [Int16]? { muted = true; return nil }
    func beginMicrophoneCapture() -> UUID {
        capture = UUID(); rounds += 1; muted = false; return capture
    }
    func saySomething() {
        let samples = (0..<960).map { Int16(sin(Double($0) * .pi * 2 * 440 / 16_000) * 6_000) }
        microphone?(samples, capture)
    }
    func finishPlaying() {
        let pending = completions; completions.removeAll()
        for generation in pending { playback?(0.06, 0.2, generation) }
    }
}

final class MiaContinuousConversationTests: XCTestCase {
    @MainActor
    private func waitUntil(_ condition: () -> Bool, file: StaticString = #filePath, line: UInt = #line) async throws {
        for _ in 0..<100 {
            if condition() { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        XCTFail("Conversation state did not arrive", file: file, line: line)
    }

    @MainActor
    private func session(audio: ConversationAudioStub) -> MiaVoiceSession {
        let voice = MiaVoiceSession(makeAudio: { audio }, recordPermission: { true })
        voice.connectionProvider = {
            try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/",
                                          clientID: UUID(), token: "fixture-only")
        }
        return voice
    }

    @MainActor
    func testAutomaticallyAnswersAndResumesAfterActualPlaybackForTwoRounds() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        for round in 1...2 {
            audio.saySomething()
            try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
            XCTAssertTrue(audio.muted)
            XCTAssertEqual(audio.rounds, round)
            XCTAssertFalse(voice.caption.contains("用户识别文本"))
            audio.finishPlaying()
            try await waitUntil { voice.state == .listening && audio.rounds == round + 1 }
            XCTAssertFalse(audio.muted)
        }
        await voice.toggleTalk()
        XCTAssertEqual(voice.state, .disconnected)
        XCTAssertFalse(voice.conversationActive)
        XCTAssertTrue(audio.stopped)
    }

    @MainActor
    func testVoiceInterruptDiscardsOldPlaybackAndSpeechCallbacks() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        let oldCapture = audio.capture
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        audio.speech?(oldCapture)
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        XCTAssertEqual(audio.interruptions, 1)
        XCTAssertEqual(voice.caption, "")
        audio.finishPlaying()
        audio.speech?(oldCapture)
        try await Task.sleep(nanoseconds: 100_000_000)
        XCTAssertEqual(audio.rounds, 2)
        XCTAssertEqual(voice.state, .listening)
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        audio.finishPlaying()
        try await waitUntil { voice.state == .listening && audio.rounds == 3 }
    }

    @MainActor
    func testMicrophonePermissionFailureDoesNotStartAudioOrRetry() async throws {
        let audio = ConversationAudioStub()
        let voice = MiaVoiceSession(makeAudio: { audio }, recordPermission: { false })
        voice.connectionProvider = {
            try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/",
                                          clientID: UUID(), token: "fixture-only")
        }
        await voice.beginConversation()
        try await waitUntil { voice.errorMessage != nil }
        XCTAssertEqual(voice.state, .disconnected)
        XCTAssertEqual(audio.rounds, 0)
        XCTAssertFalse(voice.conversationActive)
    }
}
