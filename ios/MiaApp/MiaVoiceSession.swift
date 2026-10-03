import AVFoundation
import Foundation

@MainActor
final class MiaVoiceSession: ObservableObject {
    enum State: String {
        case disconnected = "未连接"
        case connecting = "正在连接"
        case ready = "点击开始说话"
        case listening = "正在聆听，点击结束"
        case speaking = "Mia 正在回答"
    }

    @Published private(set) var state: State = .disconnected
    @Published private(set) var caption = ""
    @Published private(set) var audioLevel: Float = 0
    @Published var errorMessage: String?

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

    func toggleTalk(endpoint: String, token: String?) async {
        switch state {
        case .disconnected:
            startWhenConnected = true
            await connect(endpoint: endpoint, token: token)
        case .ready:
            await startListening()
        case .listening:
            await stopListening()
        case .speaking:
            do {
                try await transport?.abort(sessionID: sessionID)
                audio?.stop()
                audio = nil
                pendingPlaybackFrames = 0
                speechEnded = false
                audioLevel = 0
                captionTimeline.interrupt()
                caption = ""
                await startListening()
            } catch { fail(error) }
        case .connecting:
            break
        }
    }

    func disconnect() {
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

    private func connect(endpoint: String, token: String?) async {
        state = .connecting
        do {
            let clientID = storedClientID()
            let config = try MiaWebSocketConfiguration(endpoint: endpoint,
                                                       clientID: clientID, token: token)
            let connection = MiaWebSocketTransport(configuration: config)
            let generation = connectionGeneration
            transport = connection
            connection.open()
            try await connection.sendHello()
            receiveTask = Task { [weak self] in
                await self?.receiveLoop(connection)
            }
            Task { [weak self] in
                try? await Task.sleep(nanoseconds: 10_000_000_000)
                guard let self, self.connectionGeneration == generation,
                      self.state == .connecting else { return }
                self.fail(MiaConnectionError.handshakeTimeout)
            }
        } catch { fail(error) }
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
            sessionID = id
            sampleRate = rate
            codec = try MiaOpusCodec(inputSampleRate: 16_000, outputSampleRate: rate)
            state = .ready
            if startWhenConnected {
                startWhenConnected = false
                Task { await startListening() }
            }
        case .ttsStart:
            state = .speaking
            speechEnded = false
        case .ttsSentence:
            captionTimeline.handle(event)
            caption = captionTimeline.visibleText
        case .ttsStop:
            guard state == .speaking else { break }
            speechEnded = true
            finishSpeechIfPlayed()
        case .userTranscript:
            break
        case .serverError(let message):
            errorMessage = message
            state = .ready
        case .emotion, .other:
            break
        }
    }

    private func handleAudio(_ payload: Data) throws {
        guard let codec, let audio else { return }
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
        guard permission else {
            errorMessage = MiaAudioError.microphoneDenied.localizedDescription
            return
        }
        guard self.transport === transport else { return }
        do {
            if audio == nil {
                let audio = MiaAudioIO()
                try audio.start(outputSampleRate: sampleRate,
                                onMicrophoneFrame: { [weak self] samples in
                                    Task { @MainActor in self?.enqueueMicrophone(samples) }
                                },
                                onPlaybackFrame: { [weak self] duration, level in
                                    Task { @MainActor in self?.playbackAdvanced(duration, level: level) }
                                })
                self.audio = audio
            }
            try await transport.startListening(sessionID: sessionID)
            state = .listening
        } catch { fail(error) }
    }

    private func stopListening() async {
        let finalFrame = audio?.takeFinalMicrophoneFrame()
        state = .ready
        do {
            await sendTask?.value
            if let finalFrame, let codec, let transport {
                try await transport.sendOpus(codec.encode(finalFrame))
            }
            try await transport?.stopListening(sessionID: sessionID)
        } catch { fail(error) }
    }

    private func enqueueMicrophone(_ samples: [Int16]) {
        guard state == .listening else { return }
        pendingMicrophoneFrames.append(samples)
        if pendingMicrophoneFrames.count > 10 {
            pendingMicrophoneFrames.removeFirst()
        }
        guard sendTask == nil else { return }
        sendTask = Task { [weak self] in
            await self?.drainMicrophone()
        }
    }

    private func drainMicrophone() async {
        while !pendingMicrophoneFrames.isEmpty, !Task.isCancelled {
            let samples = pendingMicrophoneFrames.removeFirst()
            do {
                guard let codec, let transport else { break }
                try await transport.sendOpus(codec.encode(samples))
            } catch {
                fail(error)
                break
            }
        }
        sendTask = nil
    }

    private func playbackAdvanced(_ duration: Double, level: Float) {
        pendingPlaybackFrames = max(0, pendingPlaybackFrames - 1)
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

    private func fail(_ error: Error) {
        errorMessage = error.localizedDescription
        disconnect()
    }

    private func storedClientID() -> UUID {
        let key = "mia.clientID"
        if let value = UserDefaults.standard.string(forKey: key),
           let id = UUID(uuidString: value) { return id }
        let id = UUID()
        UserDefaults.standard.set(id.uuidString, forKey: key)
        return id
    }
}
