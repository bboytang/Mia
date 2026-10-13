import XCTest
@testable import Mia

private final class ConversationAudioStub: MiaConversationAudio {
    var microphone: (([Int16], UUID) -> Void)?
    var playback: ((Double, Float, UUID) -> Void)?
    var audioError: ((Error) -> Void)?
    var capture = UUID()
    var rounds = 0
    var muted = false
    var stopped = false
    var interruptions = 0
    var engineStopped = false
    var recoveries = 0
    var recoveryFails = false
    var completions: [UUID] = []

    func start(outputSampleRate: Int, onMicrophoneFrame: @escaping ([Int16], UUID) -> Void,
               onPlaybackFrame: @escaping (Double, Float, UUID) -> Void,
               onAudioError: @escaping (Error) -> Void) throws {
        microphone = onMicrophoneFrame; playback = onPlaybackFrame
        audioError = onAudioError
    }
    func play(_ samples: [Int16], generation: UUID) throws { completions.append(generation) }
    func interruptPlayback() { interruptions += 1 }
    func recoverConfiguration() throws -> Bool {
        guard engineStopped else { return false }
        if recoveryFails { throw MiaAudioError.captureRecoveryFailed }
        engineStopped = false
        recoveries += 1
        return true
    }
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
    @discardableResult
    func finishPlaybackFrame() -> UUID? {
        guard !completions.isEmpty else { return nil }
        let generation = completions.removeFirst()
        playback?(0.06, 0.2, generation)
        return generation
    }
}

final class MiaContinuousConversationTests: XCTestCase {
    @MainActor
    private func waitUntil(_ condition: () -> Bool, file: StaticString = #filePath, line: UInt = #line) async throws {
        for _ in 0..<250 {
            if condition() { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        XCTFail("Conversation state did not arrive", file: file, line: line)
    }

    @MainActor
    private func session(audio: ConversationAudioStub,
                         endpoint: String = "ws://127.0.0.1:8769/xiaozhi/v1/") -> MiaVoiceSession {
        let voice = MiaVoiceSession(makeAudio: { audio }, recordPermission: { true })
        voice.connectionProvider = {
            try MiaWebSocketConfiguration(endpoint: endpoint,
                                          clientID: UUID(), token: "fixture-only")
        }
        return voice
    }

    @MainActor
    func testQueuedSentencesFollowPlaybackAndClearBetweenReplies() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio, endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/?subtitles=queued")
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { audio.completions.count == 4 && voice.replyText == "下一句回复" }
        XCTAssertEqual(voice.caption, "")

        let oldPacket = audio.finishPlaybackFrame()
        try await waitUntil { voice.caption == "第一句回复" }
        audio.finishPlaybackFrame()
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.caption, "第一句回复")
        XCTAssertEqual(voice.state, .speaking)
        audio.finishPlaybackFrame()
        try await waitUntil { voice.caption == "下一句回复" }
        audio.finishPlaybackFrame()
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        XCTAssertEqual(voice.caption, "下一句回复")

        audio.saySomething()
        try await waitUntil { audio.completions.count == 4 && voice.state == .speaking }
        XCTAssertEqual(voice.caption, "")
        if let oldPacket { audio.playback?(0.06, 0.2, oldPacket) }
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.caption, "")
        XCTAssertEqual(voice.state, .speaking)
        audio.finishPlaybackFrame()
        try await waitUntil { voice.caption == "第一句回复" }
        audio.finishPlaying()
        try await waitUntil { voice.state == .listening && audio.rounds == 3 }
        XCTAssertEqual(voice.caption, "下一句回复")
    }

    @MainActor
    func testAudioRecoveryDiscardsOldCaptionCallbacks() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio, endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/?subtitles=queued")
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { audio.completions.count == 4 }
        let oldPacket = audio.finishPlaybackFrame()
        try await waitUntil { voice.caption == "第一句回复" }

        audio.engineStopped = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        XCTAssertEqual(voice.caption, "")
        audio.finishPlaying()
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.caption, "")
        XCTAssertEqual(voice.state, .listening)

        audio.saySomething()
        try await waitUntil { audio.completions.count == 4 && voice.state == .speaking }
        if let oldPacket { audio.playback?(0.06, 0.2, oldPacket) }
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.caption, "")
        audio.finishPlaybackFrame()
        try await waitUntil { voice.caption == "第一句回复" }
        audio.finishPlaying()
        try await waitUntil { voice.state == .listening && audio.rounds == 3 }
        XCTAssertEqual(voice.caption, "下一句回复")
        XCTAssertNil(voice.errorMessage)
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
            XCTAssertGreaterThan(voice.microphoneFrames, 0)
            XCTAssertGreaterThan(voice.uploadedFrames, 0)
            XCTAssertGreaterThan(voice.microphonePeak, 0)
            XCTAssertEqual(voice.lastUserTranscript, "用户识别文本")
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
        XCTAssertFalse(voice.allowsAutomaticStart)
        voice.disconnect()
        XCTAssertFalse(voice.allowsAutomaticStart)
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        XCTAssertTrue(voice.allowsAutomaticStart)
    }

    @MainActor
    func testMicrophoneDuringReplyDoesNotInterruptOrUploadAndListeningResumes() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        let captured = voice.microphoneFrames
        let uploaded = voice.uploadedFrames
        XCTAssertTrue(audio.muted)
        // Simulate late microphone callbacks even though the input is muted.
        audio.microphone?([Int16](repeating: .max, count: 960), audio.capture)
        audio.saySomething()
        try await Task.sleep(nanoseconds: 100_000_000)
        XCTAssertEqual(voice.state, .speaking)
        XCTAssertEqual(audio.interruptions, 0)
        XCTAssertEqual(audio.rounds, 1)
        XCTAssertEqual(voice.microphoneFrames, captured)
        XCTAssertEqual(voice.uploadedFrames, uploaded)
        audio.finishPlaying()
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        XCTAssertFalse(audio.muted)
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        XCTAssertNil(voice.errorMessage)
        await voice.toggleTalk()
        XCTAssertEqual(voice.state, .disconnected)
        XCTAssertTrue(audio.stopped)
        audio.finishPlaying()
        audio.saySomething()
        try await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertEqual(voice.state, .disconnected)
        XCTAssertEqual(voice.caption, "")
    }

    @MainActor
    func testMicrophoneWhileThinkingDoesNotRestartListeningOrUpload() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio, endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/?thinking=delayed")
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { voice.state == .waiting }
        let captured = voice.microphoneFrames
        let uploaded = voice.uploadedFrames
        XCTAssertTrue(audio.muted)
        audio.saySomething()
        try await Task.sleep(nanoseconds: 100_000_000)
        XCTAssertEqual(voice.state, .waiting)
        XCTAssertEqual(audio.interruptions, 0)
        XCTAssertEqual(audio.rounds, 1)
        XCTAssertEqual(voice.microphoneFrames, captured)
        XCTAssertEqual(voice.uploadedFrames, uploaded)
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        audio.finishPlaying()
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
    }

    @MainActor
    func testActiveConversationResumesMicrophoneAfterServerReconnect() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        let config = try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/?close_once=1",
                                                  clientID: UUID(), token: "fixture-only")
        var calls = 0
        voice.connectionProvider = { calls += 1; return config }
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { calls >= 2 && voice.state == .listening && audio.rounds == 2 }
        XCTAssertTrue(voice.conversationActive)
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
    }

    @MainActor
    func testExplicitStopCancelsActiveConversationReconnect() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        let config = try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/?close_once=1",
                                                  clientID: UUID(), token: "fixture-only")
        var calls = 0
        voice.connectionProvider = { calls += 1; return config }
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.errorMessage != nil && voice.state == .disconnected }
        XCTAssertTrue(voice.conversationActive)
        await voice.toggleTalk()
        try await Task.sleep(nanoseconds: 1_200_000_000)
        XCTAssertEqual(calls, 1)
        XCTAssertFalse(voice.conversationActive)
        XCTAssertFalse(voice.allowsAutomaticStart)
        XCTAssertEqual(audio.rounds, 1)
    }

    @MainActor
    func testAudioConfigurationRecoversInPlaceWithoutReconnectionOrPopup() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        let config = try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/",
                                                  clientID: UUID(), token: "fixture-only")
        var connections = 0
        voice.connectionProvider = { connections += 1; return config }
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        for _ in 0..<3 { audio.audioError?(MiaAudioError.configurationChanged) }
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(audio.recoveries, 0)
        audio.engineStopped = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { audio.recoveries == 1 }
        XCTAssertEqual(voice.state, .listening)
        XCTAssertNil(voice.errorMessage)
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        XCTAssertEqual(connections, 1)
        XCTAssertEqual(audio.rounds, 1)
        XCTAssertNil(voice.errorMessage)
    }

    @MainActor
    func testAudioRecoveryDuringPlaybackDiscardsOldAudioAndResumesOnSameConnection() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        audio.engineStopped = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        audio.finishPlaying()
        XCTAssertEqual(voice.state, .listening)
        XCTAssertEqual(audio.interruptions, 1)
        XCTAssertNil(voice.errorMessage)
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
    }

    @MainActor
    func testUnrecoverableAudioStopsOnceWithoutReconnecting() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.engineStopped = true
        audio.recoveryFails = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { voice.state == .disconnected }
        XCTAssertEqual(voice.errorMessage, MiaAudioError.captureRecoveryFailed.localizedDescription)
        try await Task.sleep(nanoseconds: 1_200_000_000)
        XCTAssertEqual(audio.rounds, 1)
        XCTAssertFalse(voice.conversationActive)
    }

    @MainActor
    func testBindingRecheckClearsOldActivationErrorBeforeReturningHome() async throws {
        let audio = ConversationAudioStub()
        let voice = session(audio: audio)
        let client = MiaXiaozhiClient()
        var bound = false
        voice.connectionProvider = {
            try await client.discover(ota: "http://127.0.0.1:8770/ota/" + (bound ? "" : "?activation=1"),
                                      websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
        }
        defer { voice.disconnect() }
        await voice.beginConversation()
        XCTAssertNotNil(voice.errorMessage)
        XCTAssertNotNil(client.activationCode)
        bound = true
        try await voice.checkDeviceBinding()
        XCTAssertNil(client.activationCode)
        XCTAssertNil(voice.errorMessage)
        XCTAssertEqual(client.status, "设备配置已就绪")
        XCTAssertEqual(audio.rounds, 0)
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
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
        XCTAssertEqual(voice.microphoneFrames, 0)
        XCTAssertEqual(voice.uploadedFrames, 0)
    }

    @MainActor
    func testSpeechOnsetIsBufferedWhileAudioRecoveryResumesListening() async throws {
        let audio = ConversationAudioStub()
        var permissionCalls = 0
        var resume: CheckedContinuation<Bool, Never>?
        let voice = MiaVoiceSession(makeAudio: { audio }, recordPermission: {
            permissionCalls += 1
            if permissionCalls == 2 {
                return await withCheckedContinuation { resume = $0 }
            }
            return true
        })
        voice.connectionProvider = {
            try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/",
                                          clientID: UUID(), token: "fixture-only")
        }
        defer { resume?.resume(returning: false); voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { voice.state == .speaking && !audio.completions.isEmpty }
        audio.engineStopped = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { resume != nil }
        XCTAssertFalse(audio.muted)
        audio.saySomething()
        // Deliver the captured frame before allowing the listen control to continue.
        try await Task.sleep(nanoseconds: 50_000_000)
        let continuation = resume
        resume = nil
        continuation?.resume(returning: true)
        try await waitUntil { voice.state == .speaking && audio.rounds == 2 }
        XCTAssertEqual(audio.interruptions, 1)
    }
}
