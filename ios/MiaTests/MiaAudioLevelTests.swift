import XCTest
@testable import Mia

final class MiaAudioLevelTests: XCTestCase {
    func testEmptyAndSilentPCMHaveNoLevel() {
        XCTAssertEqual(MiaAudioIO.level(for: []), 0)
        XCTAssertEqual(MiaAudioIO.level(for: [0, 0, 0, 0]), 0)
    }

    func testPositiveAndNegativePCMExtremesStayWithinUnitLevel() {
        XCTAssertEqual(MiaAudioIO.level(for: [.min]), 1, accuracy: 0.0001)
        XCTAssertEqual(MiaAudioIO.level(for: [.max]), 1, accuracy: 0.0001)
    }

    func testLevelMeasuresEnergyRatherThanSignedAverage() {
        XCTAssertEqual(MiaAudioIO.level(for: [16_384, -16_384]), 0.5, accuracy: 0.0001)
        XCTAssertEqual(MiaAudioIO.level(for: [8_192, -8_192]), 0.25, accuracy: 0.0001)
        XCTAssertEqual(MiaAudioIO.level(for: [16_384, 0, 0, 0]), 0.25, accuracy: 0.0001)
    }
}
