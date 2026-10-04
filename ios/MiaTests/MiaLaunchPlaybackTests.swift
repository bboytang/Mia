import AVFoundation
import Combine
import SwiftUI
import XCTest
@testable import Mia

final class MiaLaunchPlaybackTests: XCTestCase {
    @MainActor
    func testCompletionRevealsHomeAndReleasesPlayback() async throws {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: try fixtureVideoURL(), reduceMotion: false)
        let player = launch.player
        XCTAssertTrue(launch.isShowing)
        XCTAssertNotNil(player)
        XCTAssertTrue(player?.isMuted == true)

        await assertDismisses(launch) {
            NotificationCenter.default.post(name: AVPlayerItem.didPlayToEndTimeNotification,
                                            object: player?.currentItem)
        }

        XCTAssertFalse(launch.isShowing)
        XCTAssertNil(launch.player)
        XCTAssertNil(player?.currentItem)
    }

    @MainActor
    func testSkipCannotReplayOnAnotherAppearance() {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: videoURL, reduceMotion: false)

        launch.skip()
        launch.start(videoURL: videoURL, reduceMotion: false)

        XCTAssertFalse(launch.isShowing)
        XCTAssertNil(launch.player)
    }

    @MainActor
    func testReduceMotionShowsHomeWithoutCreatingPlayer() {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: videoURL, reduceMotion: true)
        launch.start(videoURL: videoURL, reduceMotion: false)

        XCTAssertFalse(launch.isShowing)
        XCTAssertNil(launch.player)
    }

    @MainActor
    func testLeavingForegroundStopsPlaybackAndReturningDoesNotReplay() {
        for phase in [ScenePhase.inactive, .background] {
            let launch = MiaLaunchPlayback()
            launch.start(videoURL: videoURL, reduceMotion: false)
            let player = launch.player
            launch.sceneChanged(.active)
            XCTAssertTrue(launch.isShowing)

            launch.sceneChanged(phase)
            launch.sceneChanged(.active)
            launch.start(videoURL: videoURL, reduceMotion: false)

            XCTAssertFalse(launch.isShowing)
            XCTAssertNil(launch.player)
            XCTAssertNil(player?.currentItem)
        }
    }

    @MainActor
    func testMissingVideoImmediatelyShowsHomeAndCannotRetry() {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: nil, reduceMotion: false)
        launch.start(videoURL: videoURL, reduceMotion: false)

        XCTAssertFalse(launch.isShowing)
        XCTAssertNil(launch.player)
    }

    @MainActor
    func testHomeIsRevealedDuringFinalQuarterSecondOfMedia() {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: videoURL, reduceMotion: false)

        launch.playbackAdvanced(seconds: 9, duration: 10)
        XCTAssertEqual(launch.videoOpacity, 1)
        launch.playbackAdvanced(seconds: 9.875, duration: 10)
        XCTAssertEqual(launch.videoOpacity, 0.5)
        XCTAssertTrue(launch.isShowing)
        XCTAssertNotNil(launch.player)
        launch.playbackAdvanced(seconds: 10, duration: 10)
        XCTAssertEqual(launch.videoOpacity, 0)
        launch.finish()
    }

    @MainActor
    func testUnknownDurationDoesNotPrematurelyRevealHome() {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: videoURL, reduceMotion: false)

        launch.playbackAdvanced(seconds: 0, duration: .nan)
        XCTAssertEqual(launch.videoOpacity, 1)
        launch.playbackAdvanced(seconds: 0, duration: 0)
        XCTAssertEqual(launch.videoOpacity, 1)
        launch.finish()
    }

    @MainActor
    func testPlaybackFailureNotificationRevealsHome() async throws {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: try fixtureVideoURL(), reduceMotion: false)

        await assertDismisses(launch) {
            NotificationCenter.default.post(name: AVPlayerItem.failedToPlayToEndTimeNotification,
                                            object: launch.player?.currentItem)
        }
    }

    @MainActor
    func testUnreadableMediaRevealsHome() async {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: videoURL, reduceMotion: false)

        await assertDismisses(launch) {}
    }

    @MainActor
    func testStalledPlaybackCannotBlockHomeBeyondSevenSeconds() async throws {
        let launch = MiaLaunchPlayback()
        launch.start(videoURL: try fixtureVideoURL(), reduceMotion: false)

        await assertDismisses(launch, timeout: 8.5) {
            launch.player?.pause()
        }
    }

    @MainActor
    private func assertDismisses(_ launch: MiaLaunchPlayback, timeout: TimeInterval = 2,
                                 trigger: () -> Void) async {
        XCTAssertTrue(launch.isShowing)
        let dismissed = expectation(description: "启动动画结束，首页可用")
        let observation = launch.$isShowing.first(where: { !$0 }).sink { _ in dismissed.fulfill() }
        defer { observation.cancel() }

        trigger()
        await fulfillment(of: [dismissed], timeout: timeout)

        XCTAssertFalse(launch.isShowing)
        XCTAssertNil(launch.player)
    }

    private func fixtureVideoURL() throws -> URL {
        try XCTUnwrap(Bundle(for: MiaLaunchPlaybackTests.self)
            .url(forResource: "MiaLaunchFixture", withExtension: "mp4"))
    }

    private var videoURL: URL {
        URL(fileURLWithPath: "/MiaLaunch.mp4")
    }
}
