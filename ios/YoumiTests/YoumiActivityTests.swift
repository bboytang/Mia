import XCTest
@testable import Youmi

final class YoumiActivityTests: XCTestCase {
    func testStandbyDoesNotClaimYoumiIsListening() throws {
        XCTAssertEqual(MiaActivityAttributes.Phase.standby.title, "待呼叫")
        XCTAssertNotEqual(MiaActivityAttributes.Phase.standby.symbol, "mic.fill")
        let state = MiaActivityAttributes.ContentState(phase: .standby)
        let decoded = try JSONDecoder().decode(MiaActivityAttributes.ContentState.self,
                                              from: JSONEncoder().encode(state))
        XCTAssertEqual(decoded, state)
    }

    func testActivityRejectsUnknownOrUnboundedEmotion() {
        let state = MiaActivityAttributes.ContentState(phase: .speaking, emotion: "unknown", intensity: .nan)
        XCTAssertEqual(state.emotion, "calm")
        XCTAssertEqual(state.intensity, 0)
        XCTAssertEqual(MiaActivityAttributes.ContentState(phase: .speaking, intensity: 9).intensity, 1)
    }

    @MainActor
    func testStoppingIsIdempotentAndNeverRequestsMicrophone() {
        var permissionRequests = 0
        let controller = YoumiConversationController(requestRecordPermission: {
            permissionRequests += 1
            return true
        })
        controller.stop()
        controller.stop()
        XCTAssertEqual(permissionRequests, 0)
        XCTAssertFalse(controller.isStarting)
        XCTAssertFalse(controller.session.conversationActive)
        XCTAssertEqual(controller.session.state, .disconnected)
    }

    @MainActor
    func testStopCancelsStartWhilePermissionIsPending() async throws {
        var permission: CheckedContinuation<Bool, Never>?
        let controller = YoumiConversationController(requestRecordPermission: {
            await withCheckedContinuation { permission = $0 }
        })
        let starting = Task { try await controller.start() }
        for _ in 0..<100 {
            if permission != nil { break }
            try await Task.sleep(nanoseconds: 5_000_000)
        }
        let pending = try XCTUnwrap(permission)
        controller.stop()
        pending.resume(returning: true)
        do {
            try await starting.value
            XCTFail("A stopped pending start must not reopen the microphone")
        } catch is CancellationError { }
        XCTAssertFalse(controller.session.conversationActive)
        XCTAssertEqual(controller.session.state, .disconnected)
    }

    @MainActor
    func testRepeatedSystemActionDoesNotRestartPendingConversationAndRecordsItsTime() async throws {
        let suite = "YoumiShortcutTest." + UUID().uuidString
        let preferences = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { preferences.removePersistentDomain(forName: suite) }
        var permission: CheckedContinuation<Bool, Never>?
        var permissionRequests = 0
        let controller = YoumiConversationController(preferences: preferences, requestRecordPermission: {
            permissionRequests += 1
            return await withCheckedContinuation { permission = $0 }
        })
        let starting = Task { try await controller.start() }
        for _ in 0..<100 {
            if permission != nil { break }
            try await Task.sleep(nanoseconds: 5_000_000)
        }
        let pending = try XCTUnwrap(permission)
        try await controller.startFromSystemAction()
        XCTAssertEqual(permissionRequests, 1)
        XCTAssertTrue(controller.isStarting)
        XCTAssertEqual(controller.systemActionCount, 1)
        XCTAssertNotNil(controller.lastSystemActionAt)
        let restored = YoumiConversationController(preferences: preferences)
        XCTAssertEqual(restored.systemActionCount, 1)
        XCTAssertEqual(try XCTUnwrap(restored.lastSystemActionAt).timeIntervalSince1970,
                       try XCTUnwrap(controller.lastSystemActionAt).timeIntervalSince1970, accuracy: 0.001)
        controller.stop()
        pending.resume(returning: true)
        do { try await starting.value; XCTFail("Stopped start must be cancelled") }
        catch is CancellationError { }
    }
}
