import XCTest
@testable import Mia

private final class CompanionAudioStub: MiaConversationAudio {
    var microphone: (([Int16], UUID) -> Void)?
    var playback: ((Double, Float, UUID) -> Void)?
    var audioError: ((Error) -> Void)?
    var engineStopped = false
    var capture = UUID()
    var starts = 0
    var rounds = 0
    var packets: [UUID] = []

    func start(outputSampleRate: Int, onMicrophoneFrame: @escaping ([Int16], UUID) -> Void,
               onPlaybackFrame: @escaping (Double, Float, UUID) -> Void,
               onAudioError: @escaping (Error) -> Void) throws {
        starts += 1
        microphone = onMicrophoneFrame; playback = onPlaybackFrame
        audioError = onAudioError
    }
    func play(_ samples: [Int16], generation: UUID) throws { packets.append(generation) }
    func interruptPlayback() { }
    func recoverConfiguration() throws -> Bool {
        guard engineStopped else { return false }
        engineStopped = false
        return true
    }
    func stop() { }
    func takeFinalMicrophoneFrame() -> [Int16]? { nil }
    func beginMicrophoneCapture() -> UUID { capture = UUID(); rounds += 1; return capture }
    func saySomething() {
        microphone?((0..<960).map { Int16(sin(Double($0) * .pi * 2 * 440 / 16_000) * 6_000) }, capture)
    }
    @discardableResult
    func finishPacket() -> UUID? {
        guard !packets.isEmpty else { return nil }
        let id = packets.removeFirst()
        playback?(0.06, 0.2, id)
        return id
    }
}

final class MiaCompanionSessionTests: XCTestCase {
    func testPersonalityIncludesTheMemoriesBehindItsGrowth() throws {
        let data = Data(#"{"version":1,"traits":[{"name":"坦率","description":"会直接表达判断","evidence_ids":["one","two","three"]}]}"#.utf8)
        let personality = try JSONDecoder().decode(MiaPersonality.self, from: data)
        XCTAssertEqual(personality.version, 1)
        XCTAssertEqual(personality.traits.first?.evidenceIDs, ["one", "two", "three"])
    }

    @MainActor
    private func waitUntil(_ condition: () -> Bool, file: StaticString = #filePath, line: UInt = #line) async throws {
        for _ in 0..<250 {
            if condition() { return }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        XCTFail("Companion state did not arrive", file: file, line: line)
    }

    @MainActor
    private func session(audio: CompanionAudioStub, query: String = "",
                         permission: @escaping () async -> Bool = { true }) -> MiaVoiceSession {
        let voice = MiaVoiceSession(makeAudio: { audio }, recordPermission: permission)
        voice.connectionProvider = {
            try MiaWebSocketConfiguration(endpoint: "ws://127.0.0.1:8769/xiaozhi/v1/" + query,
                                          clientID: UUID(), token: "fixture-only")
        }
        return voice
    }

    @MainActor
    func testExpressionsFollowPlayedSentencesAndIgnoreOldPackets() async throws {
        let audio = CompanionAudioStub()
        let voice = session(audio: audio, query: "?subtitles=queued")
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { audio.packets.count == 4 && voice.replyText == "下一句回复" }
        XCTAssertEqual(voice.expression.emotion, .calm)
        let old = try XCTUnwrap(audio.finishPacket())
        try await waitUntil { voice.expression.emotion == .happy }
        XCTAssertEqual(voice.expression.intensity, 0.8)
        audio.finishPacket()
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.expression.emotion, .happy)
        audio.finishPacket()
        try await waitUntil { voice.expression.emotion == .caring }
        XCTAssertEqual(voice.expression.intensity, 0.6)
        audio.finishPacket()
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        audio.saySomething()
        try await waitUntil { audio.packets.count == 4 && voice.state == .speaking }
        XCTAssertEqual(voice.expression.emotion, .calm)
        audio.playback?(0.06, 0.2, old)
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.expression.emotion, .calm)
        audio.finishPacket()
        try await waitUntil { voice.expression.emotion == .happy }
    }

    @MainActor
    func testAudioRecoveryDiscardsExpressionsAndLatePlaybackCallbacks() async throws {
        let audio = CompanionAudioStub()
        let voice = session(audio: audio, query: "?subtitles=queued")
        defer { voice.disconnect() }
        await voice.beginConversation()
        try await waitUntil { voice.state == .listening }
        audio.saySomething()
        try await waitUntil { audio.packets.count == 4 }
        audio.finishPacket()
        try await waitUntil { voice.expression.emotion == .happy }
        audio.engineStopped = true
        audio.audioError?(MiaAudioError.configurationChanged)
        try await waitUntil { voice.state == .listening && audio.rounds == 2 }
        XCTAssertEqual(voice.expression.emotion, .calm)
        let late = try XCTUnwrap(audio.finishPacket())
        while !audio.packets.isEmpty { audio.finishPacket() }
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.expression.emotion, .calm)
        audio.saySomething()
        try await waitUntil { audio.packets.count == 4 && voice.state == .speaking }
        audio.playback?(0.06, 0.2, late)
        try await Task.sleep(nanoseconds: 20_000_000)
        XCTAssertEqual(voice.expression.emotion, .calm)
        audio.finishPacket()
        try await waitUntil { voice.expression.emotion == .happy }
    }

    @MainActor
    func testMemoryManagementNeedsNoMicrophoneAndCorrelatesResponseID() async throws {
        let audio = CompanionAudioStub()
        var permissionRequests = 0
        let voice = session(audio: audio, query: "?memory=wrong_id_first", permission: {
            permissionRequests += 1; return false
        })
        defer { voice.disconnect() }
        let initial = try await voice.manageMemory(action: "list")
        XCTAssertEqual(initial.memories.first?.id, "fixture-memory")
        XCTAssertFalse(initial.paused)
        XCTAssertEqual(initial.personality.version, 0)
        let edited = try await voice.manageMemory(action: "update", fields: ["id": "fixture-memory", "content": "喜欢星空"])
        XCTAssertEqual(edited.memories.first?.content, "喜欢星空")
        let paused = try await voice.manageMemory(action: "pause", fields: ["paused": true])
        XCTAssertTrue(paused.paused)
        let deleted = try await voice.manageMemory(action: "delete", fields: ["id": "fixture-memory"])
        XCTAssertTrue(deleted.memories.isEmpty)
        XCTAssertEqual(permissionRequests, 0)
        XCTAssertEqual(audio.starts, 0)
        XCTAssertEqual(voice.microphoneFrames, 0)
        XCTAssertFalse(voice.conversationActive)
        XCTAssertEqual(voice.state, .ready)
    }

    @MainActor
    func testRejectedMemoryOperationDoesNotBreakIdleConnection() async throws {
        let audio = CompanionAudioStub()
        let voice = session(audio: audio)
        defer { voice.disconnect() }
        do {
            _ = try await voice.manageMemory(action: "invalid")
            XCTFail("Server rejection accepted")
        } catch MiaMemoryError.rejected { }
        XCTAssertEqual(voice.state, .ready)
        XCTAssertFalse(voice.conversationActive)
        XCTAssertEqual(audio.starts, 0)
        let snapshot = try await voice.manageMemory(action: "list")
        XCTAssertEqual(snapshot.memories.count, 1)
    }

    @MainActor
    func testConcurrentMemoryRequestIsRejectedAndDisconnectCancelsPendingRequest() async throws {
        let audio = CompanionAudioStub()
        let voice = session(audio: audio, query: "?memory=delayed")
        defer { voice.disconnect() }
        await voice.connect()
        try await waitUntil { voice.state == .ready }
        let pending = Task { try await voice.manageMemory(action: "list") }
        try await Task.sleep(nanoseconds: 50_000_000)
        do {
            _ = try await voice.manageMemory(action: "list")
            XCTFail("Overlapping request accepted")
        } catch MiaMemoryError.busy { }
        voice.disconnect()
        do {
            _ = try await pending.value
            XCTFail("Disconnected request completed")
        } catch is CancellationError { }
        XCTAssertEqual(voice.state, .disconnected)
        XCTAssertEqual(audio.starts, 0)
    }

    @MainActor
    func testCancelledMemoryRequestDoesNotBlockTheNextRequest() async throws {
        let audio = CompanionAudioStub()
        let voice = session(audio: audio, query: "?memory=delayed")
        defer { voice.disconnect() }
        await voice.connect()
        try await waitUntil { voice.state == .ready }
        let pending = Task { try await voice.manageMemory(action: "list") }
        try await Task.sleep(nanoseconds: 50_000_000)
        pending.cancel()
        do {
            _ = try await pending.value
            XCTFail("Cancelled request completed")
        } catch is CancellationError { }
        let snapshot = try await voice.manageMemory(action: "list")
        XCTAssertEqual(snapshot.memories.first?.id, "fixture-memory")
        XCTAssertEqual(audio.starts, 0)
    }

    func testExpressionProtocolAcceptsOptionalTagsAndBoundsIntensity() throws {
        let sentence = Data(#"{"type":"tts","state":"sentence_start","text":"很好","emotion":"happy","intensity":0.8}"#.utf8)
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(sentence), .expressiveSentence("很好", emotion: "happy", intensity: 0.8))
        let text = Data(#"{"type":"llm","text":"我在听","emotion":"caring","intensity":0.6}"#.utf8)
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(text), .expressiveText("我在听", emotion: "caring", intensity: 0.6))
        for (raw, intensity) in [("-3", 0.0), ("9", 1.0), ("true", 0.5), (#""high""#, 0.5), ("null", 0.5)] {
            let message = Data("{\"type\":\"tts\",\"state\":\"sentence_start\",\"text\":\"Mia\",\"emotion\":\"happy\",\"intensity\":\(raw)}".utf8)
            XCTAssertEqual(try MiaWireProtocol.parseServerEvent(message), .expressiveSentence("Mia", emotion: "happy", intensity: intensity))
        }
        XCTAssertEqual(MiaReplyExpression(emotion: "unknown").emotion, .calm)
        XCTAssertEqual(MiaReplyExpression(emotion: "loving").emotion, .caring)
    }

    func testMemoryResponseRequiresUUIDAndKeepsPayloadForMatchingRequest() throws {
        let id = UUID().uuidString
        let payload = Data("{\"type\":\"mia_memory\",\"request_id\":\"\(id)\",\"result\":{\"memories\":[],\"paused\":false,\"personality\":{\"version\":0,\"traits\":[]}}}".utf8)
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(payload), .memoryResponse(requestID: id, payload: payload))
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(Data(#"{"type":"mia_memory","request_id":"not-a-uuid"}"#.utf8)), .other)
        XCTAssertEqual(try MiaWireProtocol.parseServerEvent(Data(#"{"type":"mia_memory","request_id":3}"#.utf8)), .other)
    }
}
