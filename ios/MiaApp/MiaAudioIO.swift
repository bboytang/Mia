import AVFoundation

enum MiaAudioError: LocalizedError {
    case microphoneDenied
    case unsupportedAudioFormat

    var errorDescription: String? {
        switch self {
        case .microphoneDenied: "请在系统设置中允许 Mia 使用麦克风"
        case .unsupportedAudioFormat: "当前设备无法建立语音格式"
        }
    }
}

final class MiaAudioIO {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var converter: AVAudioConverter?
    private var frameBuffer = MiaPCMFrameBuffer()
    private let inputLock = NSLock()
    private var captureEnabled = false
    private var onMicrophoneFrame: (([Int16]) -> Void)?
    private var onPlaybackFrame: ((Double, Float) -> Void)?
    private var outputSampleRate = 24_000.0
    private var running = false

    init() {
        engine.attach(player)
    }

    func start(outputSampleRate: Int,
               onMicrophoneFrame: @escaping ([Int16]) -> Void,
               onPlaybackFrame: @escaping (Double, Float) -> Void) throws {
        guard !running else { return }
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .voiceChat,
                                     options: [.defaultToSpeaker, .allowBluetooth])
        try audioSession.setActive(true)

        let input = engine.inputNode
        let inputFormat = input.outputFormat(forBus: 0)
        guard let captureFormat = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                                sampleRate: 16_000, channels: 1,
                                                interleaved: true),
              let outputFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                               sampleRate: Double(outputSampleRate), channels: 1,
                                               interleaved: false),
              let converter = AVAudioConverter(from: inputFormat, to: captureFormat) else {
            throw MiaAudioError.unsupportedAudioFormat
        }

        self.converter = converter
        self.outputSampleRate = Double(outputSampleRate)
        self.onMicrophoneFrame = onMicrophoneFrame
        self.onPlaybackFrame = onPlaybackFrame
        engine.connect(player, to: engine.mainMixerNode, format: outputFormat)
        input.installTap(onBus: 0, bufferSize: 1_024, format: inputFormat) { [weak self] buffer, _ in
            self?.handleMicrophone(buffer, captureFormat: captureFormat)
        }
        do {
            try engine.start()
            player.play()
            running = true
        } catch {
            input.removeTap(onBus: 0)
            self.converter = nil
            throw error
        }
    }

    func play(_ samples: [Int16]) throws {
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
        player.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { [weak self] _ in
            self?.onPlaybackFrame?(duration, rms)
        }
    }

    func stop() {
        guard running else { return }
        engine.inputNode.removeTap(onBus: 0)
        player.stop()
        engine.stop()
        inputLock.lock()
        captureEnabled = false
        frameBuffer.reset()
        inputLock.unlock()
        converter = nil
        onMicrophoneFrame = nil
        onPlaybackFrame = nil
        running = false
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    func takeFinalMicrophoneFrame() -> [Int16]? {
        inputLock.lock()
        defer { inputLock.unlock() }
        captureEnabled = false
        return frameBuffer.takePaddedFrame()
    }

    func beginMicrophoneCapture() {
        inputLock.lock()
        frameBuffer.reset()
        captureEnabled = true
        inputLock.unlock()
    }

    private func handleMicrophone(_ input: AVAudioPCMBuffer, captureFormat: AVAudioFormat) {
        guard let converter else { return }
        let capacity = AVAudioFrameCount(Double(input.frameLength) * 16_000 /
                                         input.format.sampleRate + 128)
        guard let output = AVAudioPCMBuffer(pcmFormat: captureFormat,
                                            frameCapacity: max(capacity, 256)) else { return }
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
        guard conversionError == nil, output.frameLength > 0,
              let data = output.int16ChannelData?[0] else { return }
        let samples = Array(UnsafeBufferPointer(start: data, count: Int(output.frameLength)))
        inputLock.lock()
        let frames = captureEnabled ? frameBuffer.append(samples) : []
        inputLock.unlock()
        for frame in frames { onMicrophoneFrame?(frame) }
    }
}
