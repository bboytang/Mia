import XCTest
import UIKit

final class MiaXiaozhiFlowTests: XCTestCase {
    private func launch() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-MiaDisableAutomaticConversation",
                               "-mia.xiaozhi.otaURL", "https://example.invalid/ota/",
                               "-mia.xiaozhi.websocketURL", "wss://example.invalid/xiaozhi/v1/"]
        app.launch()
        XCTAssertTrue(app.buttons["设置"].waitForExistence(timeout: 15))
        let ready = expectation(for: NSPredicate(format: "isHittable == true"),
                                evaluatedWith: app.buttons["设置"])
        wait(for: [ready], timeout: 15)
        return app
    }

    func testHomeUsesDirectVoiceWithoutAccountLogin() {
        let app = launch()
        XCTAssertTrue(app.buttons["开始说话"].exists)
        XCTAssertFalse(app.buttons["登录或注册"].exists)
        XCTAssertFalse(app.navigationBars["登录 Mia"].exists)
    }

    func testSettingsProvidesDiscoveryAndBindingWithoutAccountOrTokenEntry() {
        let app = launch()
        // This fixed overlay button needs no AX scroll-to-visible action.
        app.buttons["设置"].coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        XCTAssertTrue(app.textFields["WebSocket 地址"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.textFields["OTA 地址"].exists)
        XCTAssertTrue(app.buttons["检查设备绑定"].exists)
        XCTAssertFalse(app.buttons["登录或注册"].exists)
        XCTAssertFalse(app.secureTextFields["网关访问令牌"].exists)
    }

    func testLaunchAutomaticallyDiscoversAndShowsDeviceActivation() {
        let app = XCUIApplication()
        app.launchArguments = ["-mia.xiaozhi.otaURL", "http://127.0.0.1:8770/ota/?activation=1",
                               "-mia.xiaozhi.websocketURL", "ws://127.0.0.1:8769/xiaozhi/v1/"]
        app.launch()
        XCTAssertTrue(app.textFields["OTA 地址"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.staticTexts["123456"].exists)
    }
}
