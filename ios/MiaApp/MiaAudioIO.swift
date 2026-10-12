import AVFoundation

enum MiaAudioError: LocalizedError {
    case microphoneDenied
    case unsupportedAudioFormat
    case voiceProcessingUnavailable
    case configurationChanged

    var errorDescription: String? {
        switch self {
        case .microphoneDenied: "请在系统设置中允许 Mia 使用麦克风"
        case .unsupportedAudioFormat: "当前设备无法建立语音格式"
        case .voiceProcessingUnavailable: "当前音频设备无法启用语音处理，请尝试 iPhone 内置麦克风"
        case .configurationChanged: "音频设备发生变化，正在恢复对话"
        }
    }
}

protocol MiaConversationAudio: AnyObject {
    func start(outputSampleRate: Int, onMicrophoneFrame: @escaping ([Int16], UUID) -> Void,
               onPlaybackFrame: @escaping (Double, Float, UUID) -> Void,
               onSpeechActivity: @escaping (UUID) -> Void,
               onAudioError: @escaping (Error) -> Void) throws
    func play(_ samples: [Int16], generation: UUID) throws
    func interruptPlayback()
    func stop()
    func takeFinalMicrophoneFrame() -> [Int16]?
    func beginMicrophoneCapture() -> UUID
}

final class MiaAudioIO: MiaConversationAudio {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var converter: AVAudioConverter?
    private var frameBuffer = MiaPCMFrameBuffer()
    private let inputLock = NSLock()
    private var captureEnabled = false
    private var captureGeneration = UUID()
    private var onMicrophoneFrame: (([Int16], UUID) -> Void)?
    private var onPlaybackFrame: ((Double, Float, UUID) -> Void)?
    private var onAudioError: ((Error) -> Void)?
    private var configurationObserver: NSObjectProtocol?
    private var outputSampleRate = 24_000.0
    private var running = false

    init() {
        engine.attach(player)
    }

    static func level(for samples: [Int16]) -> Float {
        guard !samples.isEmpty else { return 0 }
        let sumSquares = samples.reduce(0.0) { sum, sample in
            let value = Double(sample)
            return sum + value * value
        }
        return Float(sqrt(sumSquares / Double(samples.count)) / 32_768)
    }

    func start(outputSampleRate: Int,
               onMicrophoneFrame: @escaping ([Int16], UUID) -> Void,
               onPlaybackFrame: @escaping (Double, Float, UUID) -> Void,
               onSpeechActivity: @escaping (UUID) -> Void,
               onAudioError: @escaping (Error) -> Void) throws {
        guard !running else { return }
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .voiceChat,
                                     options: [.defaultToSpeaker, .allowBluetooth])
        try audioSession.setActive(true)

        let input = engine.inputNode
        do {
            try input.setVoiceProcessingEnabled(true)
            guard input.isVoiceProcessingEnabled,
                  input.setMutedSpeechActivityEventListener({ [weak self] event in
                      guard event == .started, let self else { return }
                      self.inputLock.lock()
                      let generation = self.captureGeneration
                      self.inputLock.unlock()
                      onSpeechActivity(generation)
                  }) else { throw MiaAudioError.voiceProcessingUnavailable }
        } catch {
            input.setMutedSpeechActivityEventListener(nil)
            try? audioSession.setActive(false)
            throw error
        }
        guard let captureFormat = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                                sampleRate: 16_000, channels: 1,
                                                interleaved: true),
              let outputFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                               sampleRate: Double(outputSampleRate), channels: 1,
                                               interleaved: false) else {
            input.setMutedSpeechActivityEventListener(nil)
            try? audioSession.setActive(false)
            throw MiaAudioError.unsupportedAudioFormat
        }

        self.outputSampleRate = Double(outputSampleRate)
        self.onMicrophoneFrame = onMicrophoneFrame
        self.onPlaybackFrame = onPlaybackFrame
        self.onAudioError = onAudioError
        engine.connect(player, to: engine.mainMixerNode, format: outputFormat)
        input.installTap(onBus: 0, bufferSize: 1_024, format: nil) { [weak self] buffer, _ in
            self?.handleMicrophone(buffer, captureFormat: captureFormat)
        }
        configurationObserver = NotificationCenter.default.addObserver(
            forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main
        ) { [weak self] _ in
            guard let self, self.running, !self.engine.isRunning else { return }
            onAudioError(MiaAudioError.configurationChanged)
        }
        do {
            engine.prepare()
            try engine.start()
            player.play()
            running = true
        } catch {
            input.removeTap(onBus: 0)
            input.setMutedSpeechActivityEventListener(nil)
            self.converter = nil
            self.onMicrophoneFrame = nil
            self.onPlaybackFrame = nil
            self.onAudioError = nil
            if let configurationObserver { NotificationCenter.default.removeObserver(configurationObserver) }
            configurationObserver = nil
            player.stop()
            engine.stop()
            try? audioSession.setActive(false)
            throw error
        }
    }

    func play(_ samples: [Int16], generation: UUID) throws {
        guard running, !samples.isEmpty,
              let format = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                         sampleRate: outputSampleRate, channels: 1,
                                         interleaved: false),
              let buffer = AVAudioPCMBuffer(pcmFormat: format,
                                            frameCapacity: AVAudioFrameCount(samples.count)),
              let destination = buffer.floatChannelData?[0] else {
            throw MiaAudioError.unsupportedAudioFormat
        }
        buffer.frameLength = AVAudioFrameCount(samples.count)
        var sumSquares = 0.0
        for (index, sample) in samples.enumerated() {
            let value = Float(sample) / Float(Int16.max)
            destination[index] = value
            sumSquares += Double(value * value)
        }
        let rms = Float(sqrt(sumSquares / Double(samples.count)))
        let duration = Double(samples.count) / outputSampleRate
        let callback = onPlaybackFrame
        player.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { _ in
            callback?(duration, rms, generation)
        }
    }

    func interruptPlayback() {
        guard running else { return }
        player.stop()
        player.play()
    }

    func stop() {
        guard running else { return }
        if let configurationObserver { NotificationCenter.default.removeObserver(configurationObserver) }
        configurationObserver = nil
        engine.inputNode.removeTap(onBus: 0)
        engine.inputNode.setMutedSpeechActivityEventListener(nil)
        player.stop()
        engine.stop()
        inputLock.lock()
        captureEnabled = false
        frameBuffer.reset()
        inputLock.unlock()
        converter = nil
        onMicrophoneFrame = nil
        onPlaybackFrame = nil
        onAudioError = nil
        running = false
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    func takeFinalMicrophoneFrame() -> [Int16]? {
        inputLock.lock()
        captureEnabled = false
        let frame = frameBuffer.takePaddedFrame()
        inputLock.unlock()
        if running { engine.inputNode.isVoiceProcessingInputMuted = true }
        return frame
    }

    @discardableResult
    func beginMicrophoneCapture() -> UUID {
        if running { engine.inputNode.isVoiceProcessingInputMuted = false }
        inputLock.lock()
        defer { inputLock.unlock() }
        frameBuffer.reset()
        captureGeneration = UUID()
        captureEnabled = true
        return captureGeneration
    }

    func microphoneSamples(from input: AVAudioPCMBuffer, captureFormat: AVAudioFormat) throws -> [Int16] {
        guard input.format.sampleRate > 0, input.format.channelCount > 0 else {
            throw MiaAudioError.unsupportedAudioFormat
        }
        // Voice Processing can renegotiate the format after graph setup.
        if converter?.inputFormat != input.format {
            converter = AVAudioConverter(from: input.format, to: captureFormat)
        }
        guard let converter else { throw MiaAudioError.unsupportedAudioFormat }
        let capacity = AVAudioFrameCount(Double(input.frameLength) * 16_000 /
                                         input.format.sampleRate + 128)
        guard let output = AVAudioPCMBuffer(pcmFormat: captureFormat,
                                            frameCapacity: max(capacity, 256)) else {
            throw MiaAudioError.unsupportedAudioFormat
        }
        var consumed = false
        var conversionError: NSError?
        converter.convert(to: output, error: &conversionError) { _, status in
            if consumed {
                status.pointee = .noDataNow
                return nil
            }
            consumed = true
            status.pointee = .haveData
            return input
        }
        if let conversionError { throw conversionError }
        guard output.frameLength > 0 else { return [] }
        guard let data = output.int16ChannelData?[0] else { throw MiaAudioError.unsupportedAudioFormat }
        return Array(UnsafeBufferPointer(start: data, count: Int(output.frameLength)))
    }

    private func handleMicrophone(_ input: AVAudioPCMBuffer, captureFormat: AVAudioFormat) {
        let samples: [Int16]
        do { samples = try microphoneSamples(from: input, captureFormat: captureFormat) }
        catch { onAudioError?(error); return }
        inputLock.lock()
        let frames = captureEnabled ? frameBuffer.append(samples) : []
        let generation = captureGeneration
        inputLock.unlock()
        for frame in frames { onMicrophoneFrame?(frame, generation) }
    }

    deinit {
        if let configurationObserver { NotificationCenter.default.removeObserver(configurationObserver) }
    }
}
