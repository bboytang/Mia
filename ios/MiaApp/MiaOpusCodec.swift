import Foundation
import opus

enum MiaOpusError: Error {
    case invalidSampleRate
    case initializationFailed(Int32)
    case invalidInputFrame
    case encodeFailed(Int32)
    case decodeFailed(Int32)
}

final class MiaOpusCodec {
    private let encoder: OpaquePointer
    private let decoder: OpaquePointer
    private let inputFrameSamples: Int
    private let maxOutputSamples: Int

    init(inputSampleRate: Int, outputSampleRate: Int) throws {
        let supported = [8_000, 12_000, 16_000, 24_000, 48_000]
        guard supported.contains(inputSampleRate), supported.contains(outputSampleRate) else {
            throw MiaOpusError.invalidSampleRate
        }

        var error: Int32 = 0
        guard let encoder = opus_encoder_create(
            Int32(inputSampleRate), 1, OPUS_APPLICATION_VOIP, &error) else {
            throw MiaOpusError.initializationFailed(error)
        }
        guard let decoder = opus_decoder_create(Int32(outputSampleRate), 1, &error) else {
            opus_encoder_destroy(encoder)
            throw MiaOpusError.initializationFailed(error)
        }

        self.encoder = encoder
        self.decoder = decoder
        inputFrameSamples = inputSampleRate * 60 / 1_000
        maxOutputSamples = outputSampleRate * 120 / 1_000
    }

    deinit {
        opus_encoder_destroy(encoder)
        opus_decoder_destroy(decoder)
    }

    func encode(_ samples: [Int16]) throws -> Data {
        guard samples.count == inputFrameSamples else {
            throw MiaOpusError.invalidInputFrame
        }

        var payload = [UInt8](repeating: 0, count: 4_000)
        let length = samples.withUnsafeBufferPointer { pcm in
            payload.withUnsafeMutableBufferPointer { output in
                opus_encode(encoder, pcm.baseAddress, Int32(inputFrameSamples),
                            output.baseAddress, Int32(output.count))
            }
        }
        guard length > 0 else { throw MiaOpusError.encodeFailed(length) }
        return Data(payload.prefix(Int(length)))
    }

    func decode(_ payload: Data) throws -> [Int16] {
        guard !payload.isEmpty else { throw MiaOpusError.invalidInputFrame }
        var samples = [Int16](repeating: 0, count: maxOutputSamples)
        let count = payload.withUnsafeBytes { input in
            samples.withUnsafeMutableBufferPointer { output in
                opus_decode(decoder, input.bindMemory(to: UInt8.self).baseAddress,
                            Int32(payload.count), output.baseAddress,
                            Int32(maxOutputSamples), 0)
            }
        }
        guard count > 0 else { throw MiaOpusError.decodeFailed(count) }
        return Array(samples.prefix(Int(count)))
    }
}
