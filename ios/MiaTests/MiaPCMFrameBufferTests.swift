import XCTest
@testable import Mia

final class MiaPCMFrameBufferTests: XCTestCase {
    func testCombinesPartialMicrophoneBuffersIntoFixedOpusFrames() {
        var buffer = MiaPCMFrameBuffer(frameSize: 4)

        XCTAssertTrue(buffer.append([1, 2, 3]).isEmpty)
        XCTAssertEqual(buffer.append([4, 5, 6, 7, 8, 9]), [[1, 2, 3, 4], [5, 6, 7, 8]])
        XCTAssertEqual(buffer.append([10, 11, 12]), [[9, 10, 11, 12]])
    }

    func testResetDropsUnsentSamplesAfterInterruption() {
        var buffer = MiaPCMFrameBuffer(frameSize: 4)
        XCTAssertTrue(buffer.append([1, 2]).isEmpty)
        buffer.reset()

        XCTAssertEqual(buffer.append([3, 4, 5, 6]), [[3, 4, 5, 6]])
    }

    func testPadsLastPartialFrameWhenUserStopsTalking() {
        var buffer = MiaPCMFrameBuffer(frameSize: 4)
        XCTAssertTrue(buffer.append([7, 8]).isEmpty)

        XCTAssertEqual(buffer.takePaddedFrame(), [7, 8, 0, 0])
        XCTAssertNil(buffer.takePaddedFrame())
    }
}
