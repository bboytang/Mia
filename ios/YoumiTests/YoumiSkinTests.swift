import XCTest
import UIKit
@testable import Youmi

final class YoumiSkinTests: XCTestCase {
    func testHolographicAssetsAreInTheAppBundle() {
        for name in ["YoumiHolographicShell", "YoumiHolographicEar"] {
            XCTAssertNotNil(UIImage(named: name), name)
        }
    }

    func testVoiceDrivesMouthAndOnlyUserCaptureDrivesEars() {
        let listening = YoumiHolographicMotion(time: 2, level: 0.36, state: .listening, reduceMotion: false)
        let speaking = YoumiHolographicMotion(time: 2, level: 0.36, state: .speaking, reduceMotion: false)
        let idle = YoumiHolographicMotion(time: 2, level: 0.36, state: .idle, reduceMotion: false)
        XCTAssertGreaterThan(listening.earResponse, 0)
        XCTAssertEqual(speaking.earResponse, 0)
        XCTAssertEqual(listening.mouthOpening, speaking.mouthOpening)
        XCTAssertGreaterThan(speaking.mouthOpening, 0)
        XCTAssertEqual(idle.mouthOpening, 0)
        XCTAssertEqual(idle.earResponse, 0)
        XCTAssertNotEqual(listening.yaw, 0)
        XCTAssertNotEqual(listening.pitch, 0)
    }

    func testBlinkAndReducedMotionKeepAudioFeedback() {
        let closed = YoumiHolographicMotion(time: 4.775, level: 1, state: .listening, reduceMotion: false)
        XCTAssertEqual(closed.blink, 0.08)
        let reduced = YoumiHolographicMotion(time: 4.775, level: 1, state: .listening, reduceMotion: true)
        XCTAssertEqual(reduced.blink, 1)
        XCTAssertEqual(reduced.time, 0)
        XCTAssertEqual(reduced.yaw, 0)
        XCTAssertEqual(reduced.pitch, 0)
        XCTAssertEqual(reduced.x, 0)
        XCTAssertEqual(reduced.y, 0)
        XCTAssertGreaterThan(reduced.mouthOpening, 0)
        XCTAssertEqual(reduced.earResponse, 1)
    }

    func testInvalidAndExtremeLevelsDoNotBreakAnimation() {
        for level in [Float.nan, .infinity, -.infinity, -1] {
            let motion = YoumiHolographicMotion(time: .nan, level: level, state: .listening, reduceMotion: false)
            XCTAssertEqual(motion.earResponse, 0)
            XCTAssertEqual(motion.mouthOpening, 0)
            XCTAssertEqual(motion.time, 0)
            XCTAssertEqual(motion.blink, 1)
        }
        let loud = YoumiHolographicMotion(time: 0, level: 10, state: .listening, reduceMotion: false)
        XCTAssertEqual(loud.earResponse, 1)
        XCTAssertEqual(loud.mouthOpening, 0.065)
    }
}
