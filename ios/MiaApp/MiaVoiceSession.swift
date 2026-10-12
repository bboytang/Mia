import AVFoundation
import Foundation
import os

@MainActor
final class MiaVoiceSession: ObservableObject {
    enum State: String {
        case disconnected = "未连接"
        case connecting = "正在连接"
        case ready = "点击开始说话"
        case waiting = "Mia 正在思考，轻触可打断"
        case listening = "正在聆听，点击结束"
        case speaking = "Mia 正在回答"
    }

    @Published private(set) var state: State = .disconnected
    @Published private(set) var caption = ""
    @Published private(set) var audioLevel: Float = 0
    @Published var errorMessage: String?
    @Published private(set) var authorizationRejected = false

    var connectionProvider: (() async throws -> MiaWebSocketConfiguration)?
    @Published private(set) var diagnostics = MiaConnectionDiagnostics()
    @Published private(set) var lastUserTranscript = ""
    @Published private(set) var replyText = ""
    private let logger = Logger(subsystem: "com.bboytang.mia", category: "Xiaozhi")
    private var reconnectTask: Task<Void, Never>?
    private var reconnectAttempts = 0
    private var recordingTimeout: Task<Void, Never>?
    private var handshakeTimeout: Task<Void, Never>?
    private var replyTimeout: Task<Void, Never>?
    private var playbackGeneration = UUID()
    private var microphoneGeneration: UUID?

    private var transport: MiaWebSocketTransport?
    private var audio: MiaAudioIO?
    private var codec: MiaOpusCodec?
    private var sessionID: String?
    private var sampleRate = 24_000
    private var receiveTask: Task<Void, Never>?
    private var sendTask: Task<Void, Never>?
    private var pendingMicrophoneFrames: [[Int16]] = []
    private var captionTimeline = MiaCaptionTimeline()
    private var pendingPlaybackFrames = 0
    private var speechEnded = false
    private var startWhenConnected = false
    private var connectionGeneration = UUID()

    func toggleTalk() async {
        switch state {
        case .disconnected:
            startWhenConnected = true
            await connect(startListening: true)
        case .ready:
            await startListening()
        case .listening:
            await stopListening()
        case .waiting, .speaking:
            guard let current = transport else { return }
            do {
                replyTimeout?.cancel()
                try await current.abort(sessionID: sessionID)
                guard transport === current else { return }
                playbackGeneration = UUID()
                audio?.stop()
                audio = nil
                pendingPlaybackFrames = 0
                speechEnded = false
                audioLevel = 0
                captionTimeline.interrupt()
                caption = ""
                state = .ready
                await startListening()
            } catch { if transport === current { fail(error) } }
        case .connecting:
            break
        }
    }

    func disconnect() {
        reconnectTask?.cancel()
        reconnectTask = nil
        reconnectAttempts = 0
        recordingTimeout?.cancel()
        recordingTimeout = nil
        handshakeTimeout?.cancel()
        handshakeTimeout = nil
        replyTimeout?.cancel()
        replyTimeout = nil
        playbackGeneration = UUID()
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
        pendingPlaybackFrames = 0
        speechEnded = false
        startWhenConnected = false
        captionTimeline.interrupt()
        caption = ""
        audioLevel = 0
        state = .disconnected
    }

    func connect(startListening: Bool = false) async {
        state = .connecting
        let generation = connectionGeneration
        startWhenConnected = startListening
        diagnostics = MiaConnectionDiagnostics()
        do {
            guard let connectionProvider else { throw MiaConnectionError.invalidEndpoint }
            let config = try await connectionProvider()
            guard generation == connectionGeneration, state == .connecting else { return }
            let connection = MiaWebSocketTransport(configuration: config, onConnection: { [weak self] status, code, reason in
                Task { @MainActor [weak self] in
                    guard let self, self.connectionGeneration == generation else { return }
                    if let status { self.diagnostics.httpStatus = status }
                    if let code {
                        self.diagnostics.closeCode = code
                        self.diagnostics.closeReason = MiaConnectionDiagnostics.safeReason(reason)
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
                self.fail(MiaConnectionError.handshakeTimeout)
            }
        } catch { if generation == connectionGeneration { fail(error) } }
    }

    private func receiveLoop(_ connection: MiaWebSocketTransport) async {
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

    private func handle(_ event: MiaServerEvent) throws {
        switch event {
        case .hello(let id, let rate):
            handshakeTimeout?.cancel()
            handshakeTimeout = nil
            reconnectAttempts = 0
            errorMessage = nil
            sessionID = id
            sampleRate = rate
            codec = try MiaOpusCodec(inputSampleRate: 16_000, outputSampleRate: rate)
            state = .ready
            if startWhenConnected {
                startWhenConnected = false
                Task { await startListening() }
            }
        case .ttsStart:
            replyTimeout?.cancel()
            replyTimeout = nil
            recordingTimeout?.cancel()
            _ = audio?.takeFinalMicrophoneFrame()
            microphoneGeneration = nil
            sendTask?.cancel()
            pendingMicrophoneFrames.removeAll()
            state = .speaking
            speechEnded = false
        case .ttsSentence(let text):
            replyText = text
            captionTimeline.handle(event)
            caption = captionTimeline.visibleText
        case .ttsStop:
            guard state == .speaking else { break }
            speechEnded = true
            finishSpeechIfPlayed()
        case .userTranscript(let text):
            lastUserTranscript = text
        case .assistantText(let text):
            replyText = text
        case .serverError:
            fail(MiaConnectionError.upstreamError)
        case .emotion, .other:
            break
        }
    }

    private func handleAudio(_ payload: Data) throws {
        guard state == .speaking, let codec, let audio else { return }
        let samples = try codec.decode(payload)
        pendingPlaybackFrames += 1
        try audio.play(samples)
    }

    private func startListening() async {
        guard let transport, codec != nil else { return }
        let permission = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission {
                continuation.resume(returning: $0)
            }
        }
        guard self.transport === transport else { return }
        guard permission else {
            fail(MiaAudioError.microphoneDenied)
            return
        }
        do {
            if audio == nil {
                let audio = MiaAudioIO()
                let playback = playbackGeneration
                try audio.start(outputSampleRate: sampleRate,
                                onMicrophoneFrame: { [weak self] samples, generation in
                                    Task { @MainActor in self?.enqueueMicrophone(samples, generation: generation) }
                                },
                                onPlaybackFrame: { [weak self] duration, level in
                                    Task { @MainActor in
                                        guard let self, self.playbackGeneration == playback else { return }
                                        self.playbackAdvanced(duration, level: level)
                                    }
                                })
                self.audio = audio
            }
            try await transport.startListening(sessionID: sessionID)
            guard self.transport === transport else { return }
            audioLevel = 0
            microphoneGeneration = audio?.beginMicrophoneCapture()
            state = .listening
            recordingTimeout?.cancel()
            recordingTimeout = Task { [weak self] in
                do { try await Task.sleep(nanoseconds: 30_000_000_000) } catch { return }
                guard let self, self.state == .listening else { return }
                await self.stopListening()
            }
        } catch { if self.transport === transport { fail(error) } }
    }

    private func stopListening() async {
        guard let current = transport else { return }
        recordingTimeout?.cancel()
        recordingTimeout = nil
        let finalFrame = audio?.takeFinalMicrophoneFrame()
        microphoneGeneration = nil
        state = .waiting
        audioLevel = 0
        replyTimeout?.cancel()
        replyTimeout = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: 45_000_000_000) } catch { return }
            guard let self, self.state == .waiting else { return }
            self.fail(MiaConnectionError.responseTimeout)
        }
        do {
            await sendTask?.value
            guard transport === current else { return }
            if let finalFrame, let codec {
                try await current.sendOpus(codec.encode(finalFrame))
            }
            try await current.stopListening(sessionID: sessionID)
        } catch { if transport === current { fail(error) } }
    }

    private func enqueueMicrophone(_ samples: [Int16], generation: UUID) {
        guard state == .listening, microphoneGeneration == generation else { return }
        audioLevel = MiaAudioIO.level(for: samples)
        pendingMicrophoneFrames.append(samples)
        if pendingMicrophoneFrames.count > 10 {
            pendingMicrophoneFrames.removeFirst()
        }
        guard sendTask == nil else { return }
        let connection = connectionGeneration
        sendTask = Task { [weak self] in
            await self?.drainMicrophone(connection: connection)
        }
    }

    private func drainMicrophone(connection: UUID) async {
        while connection == connectionGeneration, !pendingMicrophoneFrames.isEmpty, !Task.isCancelled {
            let samples = pendingMicrophoneFrames.removeFirst()
            do {
                guard let codec, let transport else { break }
                try await transport.sendOpus(codec.encode(samples))
            } catch {
                if connection == connectionGeneration, !Task.isCancelled { fail(error) }
                break
            }
        }
        if connection == connectionGeneration { sendTask = nil }
    }

    private func playbackAdvanced(_ duration: Double, level: Float) {
        pendingPlaybackFrames = max(0, pendingPlaybackFrames - 1)
        guard state == .speaking else { return }
        audioLevel = level
        captionTimeline.advancePlayback(seconds: duration)
        caption = captionTimeline.visibleText
        finishSpeechIfPlayed()
    }

    private func finishSpeechIfPlayed() {
        guard speechEnded, pendingPlaybackFrames == 0 else { return }
        captionTimeline.finishSentence()
        caption = captionTimeline.visibleText
        audioLevel = 0
        state = .ready
    }

    nonisolated static func shouldReconnect(_ error: Error) -> Bool {
        if let error = error as? MiaConnectionError {
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
        let lastDiagnostics = transport?.diagnostics ?? diagnostics
        errorMessage = error.localizedDescription
        disconnect()
        diagnostics = lastDiagnostics
        if let error = error as? MiaConnectionError, case .unauthorized = error {
            authorizationRejected = true
        }
        guard Self.shouldReconnect(error), attempts < 3 else { return }
        reconnectAttempts = attempts + 1
        let generation = connectionGeneration
        let delay = UInt64(1 << attempts) * 1_000_000_000
        reconnectTask = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: delay) } catch { return }
            guard let self, self.connectionGeneration == generation else { return }
            await self.connect()
        }
    }
}
