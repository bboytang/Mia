import XCTest
import AVFoundation
@testable import Youmi

final class YoumiAudioLevelTests: XCTestCase {
    func testConnectedHeadsetIsPreferredWhenOutputStayedOnPhone() {
        XCTAssertEqual(YoumiAudioIO.preferredBluetoothInputIndex(
            available: [.builtInMic, .bluetoothHFP], outputs: [.builtInSpeaker]), 1)
        XCTAssertEqual(YoumiAudioIO.preferredBluetoothInputIndex(
            available: [.bluetoothLE, .builtInMic], outputs: [.builtInReceiver]), 0)
        XCTAssertNil(YoumiAudioIO.preferredBluetoothInputIndex(
            available: [.builtInMic], outputs: [.builtInReceiver]))
    }

    func testSelectedAccessoryRouteIsPreserved() {
        for output in [AVAudioSession.Port.bluetoothA2DP, .bluetoothHFP, .headphones, .usbAudio] {
            XCTAssertNil(YoumiAudioIO.preferredBluetoothInputIndex(
                available: [.builtInMic, .bluetoothHFP], outputs: [output]))
        }
        XCTAssertNil(YoumiAudioIO.preferredBluetoothInputIndex(
            available: [.bluetoothHFP], outputs: []))
    }

    func testNativeConversionTracksChangingCaptureFormatsAndProducesAudibleOpus() throws {
        let audio = YoumiAudioIO()
        let target = try XCTUnwrap(AVAudioFormat(commonFormat: .pcmFormatInt16,
                                               sampleRate: 16_000, channels: 1, interleaved: true))
        let codec = try YoumiOpusCodec(inputSampleRate: 16_000, outputSampleRate: 16_000)
        for (rate, channels) in [(48_000.0, 1), (44_100.0, 2), (8_000.0, 1), (24_000.0, 1), (16_000.0, 1), (48_000.0, 1)] {
            let format = try XCTUnwrap(AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                                   sampleRate: rate, channels: AVAudioChannelCount(channels),
                                                   interleaved: false))
            let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format,
                                                       frameCapacity: AVAudioFrameCount(rate * 0.12)))
            buffer.frameLength = buffer.frameCapacity
            let data = try XCTUnwrap(buffer.floatChannelData)
            for channel in 0..<channels {
                for frame in 0..<Int(buffer.frameLength) {
                    data[channel][frame] = Float(sin(Double(frame) * .pi * 2 * 440 / rate) * 0.2)
                }
            }
            let samples = try audio.microphoneSamples(from: buffer, captureFormat: target)
            XCTAssertGreaterThan(samples.count, 960)
            XCTAssertGreaterThan(YoumiAudioIO.level(for: samples), 0.05)
            var frames = YoumiPCMFrameBuffer()
            let frame = try XCTUnwrap(frames.append(samples).first)
            let decoded = try codec.decode(codec.encode(frame))
            XCTAssertEqual(decoded.count, 960)
            XCTAssertGreaterThan(YoumiAudioIO.level(for: decoded), 0.03)
        }
    }

    func testCaptureRoundsHaveDifferentEpochsAndStopHasNoResidualFrame() {
        let audio = YoumiAudioIO()
        let first = audio.beginMicrophoneCapture()
        XCTAssertNil(audio.takeFinalMicrophoneFrame())
        let second = audio.beginMicrophoneCapture()
        XCTAssertNotEqual(first, second)
        XCTAssertNil(audio.takeFinalMicrophoneFrame())
    }
    func testEmptyAndSilentPCMHaveNoLevel() {
        XCTAssertEqual(YoumiAudioIO.level(for: []), 0)
        XCTAssertEqual(YoumiAudioIO.level(for: [0, 0, 0, 0]), 0)
    }

    func testPositiveAndNegativePCMExtremesStayWithinUnitLevel() {
        XCTAssertEqual(YoumiAudioIO.level(for: [.min]), 1, accuracy: 0.0001)
        XCTAssertEqual(YoumiAudioIO.level(for: [.max]), 1, accuracy: 0.0001)
    }

    func testLevelMeasuresEnergyRatherThanSignedAverage() {
        XCTAssertEqual(YoumiAudioIO.level(for: [16_384, -16_384]), 0.5, accuracy: 0.0001)
        XCTAssertEqual(YoumiAudioIO.level(for: [8_192, -8_192]), 0.25, accuracy: 0.0001)
        XCTAssertEqual(YoumiAudioIO.level(for: [16_384, 0, 0, 0]), 0.25, accuracy: 0.0001)
    }
}
