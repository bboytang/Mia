import XCTest
@testable import Mia

final class MiaOpusCodecTests: XCTestCase {
    func testEncodesAndDecodesOneSixtyMillisecondFrame() throws {
        let codec = try MiaOpusCodec(inputSampleRate: 16_000, outputSampleRate: 24_000)
        let input = (0..<960).map { index in
            Int16(sin(Double(index) * .pi / 20) * 9_000)
        }

        let encoded = try codec.encode(input)
        XCTAssertFalse(encoded.isEmpty)

        let output = try codec.decode(encoded)
        XCTAssertFalse(output.isEmpty)
        XCTAssertLessThanOrEqual(output.count, 2_880)
        XCTAssertTrue(output.contains { $0 != 0 })
    }

    func testRejectsWrongInputFrameLength() throws {
        let codec = try MiaOpusCodec(inputSampleRate: 16_000, outputSampleRate: 24_000)

        XCTAssertThrowsError(try codec.encode([Int16](repeating: 0, count: 100)))
        XCTAssertThrowsError(try codec.decode(Data()))
    }
}
