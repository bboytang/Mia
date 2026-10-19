import AVFoundation
import Foundation
import os

@MainActor
final class YoumiVoiceSession: ObservableObject {
    enum State: String {
        case disconnected = "未连接"
        case connecting = "正在连接"
        case ready = "点击开始说话"
        case waiting = "Youmi 正在思考"
        case listening = "正在聆听，说完会自动回答"
        case speaking = "Youmi 正在回答"
    }

    @Published private(set) var state: State = .disconnected
    @Published private(set) var caption = ""
    @Published private(set) var audioLevel: Float = 0
    @Published private(set) var expression = YoumiReplyExpression()
    @Published var errorMessage: String?
    @Published private(set) var authorizationRejected = false

    var connectionProvider: (() async throws -> YoumiWebSocketConfiguration)?
    @Published private(set) var diagnostics = YoumiConnectionDiagnostics()
    @Published private(set) var microphoneFrames = 0
    @Published private(set) var uploadedFrames = 0
    @Published private(set) var droppedMicrophoneFrames = 0
    @Published private(set) var microphonePeak: Float = 0
    @Published private(set) var lastUserTranscript = ""
    @Published private(set) var replyText = ""
    @Published private(set) var memoryTask: YoumiMemoryTask?
    private let logger = Logger(subsystem: "com.bboytang.mia", category: "Youmi")
    private var reconnectTask: Task<Void, Never>?
    private var reconnectAttempts = 0
    @Published private(set) var conversationActive = false
    @Published private(set) var allowsAutomaticStart = true
    private var listeningTask: Task<Void, Never>?
    private var sendGeneration = UUID()
    private var acceptsReply = false
    private let makeAudio: () -> any YoumiConversationAudio
    private let recordPermission: () async -> Bool
    private var handshakeTimeout: Task<Void, Never>?
    private var replyTimeout: Task<Void, Never>?
    private var microphoneGeneration: UUID?

    private var transport: YoumiWebSocketTransport?
    private var audio: (any YoumiConversationAudio)?
    private var codec: YoumiOpusCodec?
    private var sessionID: String?
    private var sampleRate = 24_000
    private var receiveTask: Task<Void, Never>?
    private var sendTask: Task<Void, Never>?
    private var pendingMicrophoneFrames: [[Int16]] = []
    private var captionTimeline = YoumiCaptionTimeline()
    private var pendingPlaybackFrames: [UUID: Int] = [:]
    private var speechEnded = false
    private var startWhenConnected = false
    private var connectionGeneration = UUID()
    private var pendingExpression = YoumiReplyExpression()
    private var sentenceExpressions: [Int: YoumiReplyExpression] = [:]
    private var memoryRequest: (id: String, continuation: CheckedContinuation<Data, Error>)?
    private var memoryTimeout: Task<Void, Never>?

    init(makeAudio: @escaping () -> any YoumiConversationAudio = { YoumiAudioIO() },
         recordPermission: @escaping () async -> Bool = {
             await withCheckedContinuation { continuation in
                 AVAudioSession.sharedInstance().requestRecordPermission {
                     continuation.resume(returning: $0)
                 }
             }
         }) {
        self.makeAudio = makeAudio
        self.recordPermission = recordPermission
    }

    func beginConversation() async {
        guard state == .disconnected || state == .ready else { return }
        allowsAutomaticStart = true
        conversationActive = true
        if state == .ready { await startListening() }
        else { await connect(startListening: true) }
    }

    func toggleTalk() async {
        if conversationActive {
            disconnect()
            allowsAutomaticStart = false
        }
        else { await beginConversation() }
    }

    func checkDeviceBinding() async throws {
        disconnect()
        errorMessage = nil
        guard let connectionProvider else { throw YoumiConnectionError.invalidEndpoint }
        _ = try await connectionProvider()
    }

    func disconnect() {
        memoryTask = nil
        memoryTimeout?.cancel()
        memoryTimeout = nil
        let request = memoryRequest
        memoryRequest = nil
        request?.continuation.resume(throwing: CancellationError())
        reconnectTask?.cancel()
        reconnectTask = nil
        reconnectAttempts = 0
        conversationActive = false
        listeningTask?.cancel()
        listeningTask = nil
        acceptsReply = false
        sendGeneration = UUID()
        handshakeTimeout?.cancel()
        handshakeTimeout = nil
        replyTimeout?.cancel()
        replyTimeout = nil
        pendingPlaybackFrames.removeAll()
        microphoneGeneration = nil
        authorizationRejected = false
        connectionGeneration = UUID()
        receiveTask?.cancel()
        receiveTask = nil
        sendTask?.cancel()
        sendTask = nil
        transport?.close()
        transport = nil
        audio?.stop()
        audio = nil
        codec = nil
        sessionID = nil
        pendingMicrophoneFrames.removeAll()
        speechEnded = false
        startWhenConnected = false
        captionTimeline.interrupt()
        resetExpression()
        caption = ""
        audioLevel = 0
        state = .disconnected
    }

    func connect(startListening: Bool = false) async {
        guard state == .disconnected || state == .ready else { return }
        state = .connecting
        if startListening { conversationActive = true }
        let generation = connectionGeneration
        startWhenConnected = startListening
        diagnostics = YoumiConnectionDiagnostics()
        microphoneFrames = 0
        uploadedFrames = 0
        droppedMicrophoneFrames = 0
        lastUserTranscript = ""
        microphonePeak = 0
        do {
            guard let connectionProvider else { throw YoumiConnectionError.invalidEndpoint }
            let config = try await connectionProvider()
            guard generation == connectionGeneration, state == .connecting else { return }
            let connection = YoumiWebSocketTransport(configuration: config, onConnection: { [weak self] status, code, reason in
                Task { @MainActor [weak self] in
                    guard let self, self.connectionGeneration == generation else { return }
                    if let status { self.diagnostics.httpStatus = status }
                    if let code {
                        self.diagnostics.closeCode = code
                        self.diagnostics.closeReason = YoumiConnectionDiagnostics.safeReason(reason)
                    }
                    self.logger.info("WS HTTP=\(status ?? 0) close=\(code ?? 0)")
                }
            }, onMessage: { [weak self] kind, value in
                Task { @MainActor [weak self] in
                    guard let self, self.connectionGeneration == generation else { return }
                    if kind == "error" { self.diagnostics.exception = value }
                    else { self.diagnostics.lastMessage = value }
                    self.logger.debug("WS \(kind, privacy: .public): \(value, privacy: .public)")
                }
            })
            transport = connection
            connection.open()
            try await connection.sendHello()
            receiveTask = Task { [weak self] in
                await self?.receiveLoop(connection)
            }
            handshakeTimeout = Task { [weak self] in
                do { try await Task.sleep(nanoseconds: 10_000_000_000) } catch { return }
                guard let self, self.connectionGeneration == generation,
                      self.state == .connecting else { return }
                self.fail(YoumiConnectionError.handshakeTimeout)
            }
        } catch { if generation == connectionGeneration { fail(error) } }
    }

    private func receiveLoop(_ connection: YoumiWebSocketTransport) async {
        do {
            while !Task.isCancelled {
                let frame = try await connection.receive()
                guard transport === connection else { return }
                switch frame {
                case .event(let event):
                    try handle(event)
                case .opus(let payload):
                    try handleAudio(payload)
                }
            }
        } catch {
            if !Task.isCancelled, transport === connection { fail(error) }
        }
    }

    private func handle(_ event: YoumiServerEvent) throws {
        switch event {
        case .hello(let id, let rate):
            handshakeTimeout?.cancel()
            handshakeTimeout = nil
            reconnectAttempts = 0
            errorMessage = nil
            sessionID = id
            sampleRate = rate
            codec = try YoumiOpusCodec(inputSampleRate: 16_000, outputSampleRate: rate)
            state = .ready
            if startWhenConnected {
                startWhenConnected = false
                resumeListening()
            }
        case .ttsStart:
            guard conversationActive, acceptsReply else { return }
            replyTimeout?.cancel()
            replyTimeout = nil
            pauseForReply()
            state = .speaking
            speechEnded = false
        case .ttsSentence(let text):
            guard state == .speaking, acceptsReply else { return }
            replyText = text
            captionTimeline.handle(event)
            if let id = captionTimeline.receivingSentenceID { sentenceExpressions[id] = pendingExpression }
            caption = captionTimeline.visibleText
        case .expressiveSentence(let text, let emotion, let intensity):
            guard state == .speaking, acceptsReply else { return }
            replyText = text
            pendingExpression = YoumiReplyExpression(emotion: emotion, intensity: intensity)
            captionTimeline.handle(event)
            if let id = captionTimeline.receivingSentenceID { sentenceExpressions[id] = pendingExpression }
        case .ttsStop:
            guard state == .speaking, acceptsReply else { return }
            speechEnded = true
            finishSpeechIfPlayed()
        case .userTranscript(let text):
            lastUserTranscript = text
            guard conversationActive, state == .listening, !text.isEmpty else { return }
            pendingPlaybackFrames.removeAll()
            captionTimeline.interrupt()
            resetExpression()
            caption = ""
            acceptsReply = true
            pauseForReply()
            state = .waiting
            replyTimeout?.cancel()
            replyTimeout = Task { [weak self] in
                do { try await Task.sleep(nanoseconds: 45_000_000_000) } catch { return }
                guard let self, self.state == .waiting else { return }
                self.fail(YoumiConnectionError.responseTimeout)
            }
        case .assistantText(let text):
            guard conversationActive, acceptsReply else { return }
            replyText = text
        case .expressiveText(let text, let emotion, let intensity):
            guard conversationActive, acceptsReply else { return }
            replyText = text
            pendingExpression = YoumiReplyExpression(emotion: emotion, intensity: intensity)
        case .emotion(let emotion):
            guard conversationActive, acceptsReply else { return }
            pendingExpression = YoumiReplyExpression(emotion: emotion)
        case .memoryTask(let task):
            memoryTask = task
        case .memoryResponse(let id, let payload):
            guard let request = memoryRequest, request.id == id else { return }
            memoryRequest = nil
            memoryTimeout?.cancel()
            memoryTimeout = nil
            request.continuation.resume(returning: payload)
        case .serverError:
            fail(YoumiConnectionError.upstreamError)
        case .privateAuthorizationRequired:
            fail(YoumiConnectionError.privateAuthorizationRequired)
        case .other:
            break
        }
    }

    private func handleAudio(_ payload: Data) throws {
        guard state == .speaking, let codec, let audio else { return }
        let samples = try codec.decode(payload)
        let frameID = UUID()
        pendingPlaybackFrames[frameID] = captionTimeline.receivingSentenceID ?? -1
        try audio.play(samples, generation: frameID)
    }

    private func startListening() async {
        guard let transport, codec != nil else { return }
        let permission = await recordPermission()
        guard self.transport === transport else { return }
        guard permission else {
            fail(YoumiAudioError.microphoneDenied)
            return
        }
        do {
            if audio == nil {
                let audio = makeAudio()
                let connection = connectionGeneration
                try audio.start(outputSampleRate: sampleRate,
                                onMicrophoneFrame: { [weak self] samples, generation in
                                    Task { @MainActor in self?.enqueueMicrophone(samples, generation: generation) }
                                },
                                onPlaybackFrame: { [weak self] _, level, generation in
                                    Task { @MainActor in
                                        self?.playbackAdvanced(level: level, frameID: generation)
                                    }
                                },
                                onAudioError: { [weak self] error in
                                    Task { @MainActor in
                                        guard let self, self.connectionGeneration == connection else { return }
                                        await self.handleAudioError(error)
                                    }
                                })
                self.audio = audio
            }
            try await transport.startListening(sessionID: sessionID, automatic: true)
            guard self.transport === transport else { return }
            audioLevel = 0
            acceptsReply = false
            sendGeneration = UUID()
            if microphoneGeneration == nil { microphoneGeneration = audio?.beginMicrophoneCapture() }
            state = .listening
            sendPendingMicrophoneFrames()
        } catch { if self.transport === transport { fail(error) } }
    }

    private func resumeListening() {
        let connection = connectionGeneration
        listeningTask?.cancel()
        listeningTask = Task { [weak self] in
            guard let self, self.connectionGeneration == connection,
                  self.conversationActive, self.state == .ready else { return }
            await self.startListening()
        }
    }

    private func handleAudioError(_ error: Error) async {
        guard let audioError = error as? YoumiAudioError, case .configurationChanged = audioError else {
            fail(error)
            return
        }
        do {
            guard let audio, try audio.recoverConfiguration() else { return }
            if state == .speaking || state == .waiting {
                await resumeAfterAudioRecovery()
            }
        } catch {
            let detail = error as NSError
            logger.error("Audio recovery failed: \(detail.domain, privacy: .public) / \(detail.code)")
            fail(YoumiAudioError.captureRecoveryFailed)
        }
    }

    private func pauseForReply() {
        if microphoneGeneration != nil {
            _ = audio?.takeFinalMicrophoneFrame()
            microphoneGeneration = nil
        }
        sendGeneration = UUID()
        sendTask?.cancel()
        sendTask = nil
        pendingMicrophoneFrames.removeAll()
        audioLevel = 0
    }

    private func resumeAfterAudioRecovery() async {
        guard conversationActive,
              state == .speaking || state == .waiting, let current = transport else { return }
        acceptsReply = false
        replyTimeout?.cancel()
        pendingPlaybackFrames.removeAll()
        audio?.interruptPlayback()
        speechEnded = false
        captionTimeline.interrupt()
        caption = ""
        audioLevel = 0
        resetExpression()
        state = .ready
        // Resume capture while abort/listen control waits on the network after recovery.
        microphoneGeneration = audio?.beginMicrophoneCapture()
        do {
            try await current.abort(sessionID: sessionID)
            guard transport === current, conversationActive else { return }
            await startListening()
        } catch { if transport === current { fail(error) } }
    }

    private func enqueueMicrophone(_ samples: [Int16], generation: UUID) {
        guard conversationActive, microphoneGeneration == generation,
              state == .listening || state == .ready else { return }
        audioLevel = YoumiAudioIO.level(for: samples)
        microphoneFrames += 1
        microphonePeak = max(microphonePeak, audioLevel)
        pendingMicrophoneFrames.append(samples)
        if pendingMicrophoneFrames.count > 10 {
            droppedMicrophoneFrames += 1
            pendingMicrophoneFrames.removeFirst()
        }
        if state == .listening { sendPendingMicrophoneFrames() }
    }

    private func sendPendingMicrophoneFrames() {
        guard sendTask == nil, !pendingMicrophoneFrames.isEmpty else { return }
        let connection = sendGeneration
        sendTask = Task { [weak self] in
            await self?.drainMicrophone(connection: connection)
        }
    }

    private func drainMicrophone(connection: UUID) async {
        while connection == sendGeneration, !pendingMicrophoneFrames.isEmpty, !Task.isCancelled {
            let samples = pendingMicrophoneFrames.removeFirst()
            do {
                guard let codec, let transport else { break }
                try await transport.sendOpus(codec.encode(samples))
                if connection == sendGeneration { uploadedFrames += 1 }
            } catch {
                if connection == sendGeneration, !Task.isCancelled { fail(error) }
                break
            }
        }
        if connection == sendGeneration { sendTask = nil }
    }

    private func playbackAdvanced(level: Float, frameID: UUID) {
        guard let sentenceID = pendingPlaybackFrames.removeValue(forKey: frameID) else { return }
        guard state == .speaking else { return }
        audioLevel = level
        captionTimeline.advancePlayback(sentenceID: sentenceID)
        if let current = sentenceExpressions[sentenceID] {
            expression = current
            sentenceExpressions = sentenceExpressions.filter { $0.key >= sentenceID }
        }
        caption = captionTimeline.visibleText
        finishSpeechIfPlayed()
    }

    private func resetExpression() {
        pendingExpression = YoumiReplyExpression()
        expression = YoumiReplyExpression()
        sentenceExpressions.removeAll()
    }

    func refreshMemoryTask(latest: Bool = false) async throws {
        let previousID = memoryTask?.id
        guard latest || previousID != nil else { return }
        let fields: [String: Any] = latest ? [:] : ["id": previousID!]
        let updated = try await manageMemoryResult(action: "job_status", fields: fields, as: YoumiMemoryTask.self)
        if memoryTask?.id == previousID { memoryTask = updated }
    }

    func manageMemory(action: String, fields: [String: Any] = [:]) async throws -> YoumiMemorySnapshot {
        try await manageMemoryResult(action: action, fields: fields, as: YoumiMemorySnapshot.self)
    }

    func manageMemoryResult<Result: Decodable>(action: String, fields: [String: Any] = [:],
                                               as type: Result.Type) async throws -> Result {
        guard memoryRequest == nil else { throw YoumiMemoryError.busy }
        if state == .disconnected { await connect() }
        for _ in 0..<220 {
            if state != .connecting { break }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        guard let connection = transport, sessionID != nil else { throw YoumiMemoryError.unavailable }
        guard memoryRequest == nil else { throw YoumiMemoryError.busy }
        let requestID = UUID().uuidString
        try Task.checkCancellation()
        let payload = try await withTaskCancellationHandler(operation: {
          try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Data, Error>) in
            guard !Task.isCancelled else { continuation.resume(throwing: CancellationError()); return }
            memoryRequest = (requestID, continuation)
            memoryTimeout = Task { [weak self] in
                do { try await Task.sleep(nanoseconds: 8_000_000_000) } catch { return }
                guard let self, self.memoryRequest?.id == requestID else { return }
                let request = self.memoryRequest
                self.memoryRequest = nil
                request?.continuation.resume(throwing: YoumiMemoryError.unavailable)
            }
            Task { [weak self] in
                guard let self, self.memoryRequest?.id == requestID else { return }
                do { try await connection.manageMemory(sessionID: self.sessionID, requestID: requestID,
                                                        action: action, fields: fields) }
                catch {
                    guard self.memoryRequest?.id == requestID else { return }
                    let request = self.memoryRequest
                    self.memoryRequest = nil
                    self.memoryTimeout?.cancel()
                    request?.continuation.resume(throwing: error)
                }
            }
          }
        }, onCancel: { [weak self] in
            Task { @MainActor [weak self] in
                guard let self, self.memoryRequest?.id == requestID else { return }
                let request = self.memoryRequest
                self.memoryRequest = nil
                self.memoryTimeout?.cancel()
                self.memoryTimeout = nil
                request?.continuation.resume(throwing: CancellationError())
            }
        })
        guard let object = try JSONSerialization.jsonObject(with: payload) as? [String: Any],
              object["error"] == nil, let result = object["result"] as? [String: Any] else {
            throw YoumiMemoryError.rejected
        }
        return try JSONDecoder().decode(type,
                                        from: JSONSerialization.data(withJSONObject: result))
    }

    private func finishSpeechIfPlayed() {
        guard speechEnded, pendingPlaybackFrames.isEmpty else { return }
        audioLevel = 0
        state = .ready
        resumeListening()
    }

    nonisolated static func shouldReconnect(_ error: Error) -> Bool {
        if let error = error as? YoumiConnectionError {
            switch error {
            case .serverClosed, .handshakeTimeout: return true
            default: return false
            }
        }
        return (error as NSError).domain == NSURLErrorDomain
            && ![NSURLErrorCancelled, NSURLErrorAppTransportSecurityRequiresSecureConnection].contains((error as NSError).code)
    }

    private func fail(_ error: Error) {
        let attempts = reconnectAttempts
        let resumeConversation = conversationActive
        let lastDiagnostics = transport?.diagnostics ?? diagnostics
        errorMessage = error.localizedDescription
        disconnect()
        diagnostics = lastDiagnostics
        if let error = error as? YoumiConnectionError, case .unauthorized = error {
            authorizationRejected = true
        }
        guard Self.shouldReconnect(error), attempts < 3 else { return }
        conversationActive = resumeConversation
        reconnectAttempts = attempts + 1
        let generation = connectionGeneration
        let delay = UInt64(1 << attempts) * 1_000_000_000
        reconnectTask = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: delay) } catch { return }
            guard let self, self.connectionGeneration == generation else { return }
            await self.connect(startListening: resumeConversation)
        }
    }
}
