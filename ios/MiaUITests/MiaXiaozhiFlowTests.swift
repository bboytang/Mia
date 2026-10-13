import XCTest
import UIKit

final class MiaXiaozhiFlowTests: XCTestCase {
    private func startConversation(_ app: XCUIApplication) {
        app.buttons["开始说话"].coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        let permission = XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.buttons["Allow"]
        if permission.waitForExistence(timeout: 3) { permission.tap() }
    }

    private func launch(ota: String = "https://example.invalid/ota/",
                        websocket: String = "wss://example.invalid/xiaozhi/v1/") -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-MiaDisableAutomaticConversation",
                               "-mia.xiaozhi.otaURL", ota,
                               "-mia.xiaozhi.websocketURL", websocket]
        app.launch()
        XCTAssertTrue(app.buttons["设置"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.buttons["跳过启动动画"].exists)
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

    func testSkinSelectionAppliesAndSurvivesAppRelaunch() {
        let app = launch()
        app.buttons["设置"].tap()
        let entry = app.buttons["个性化皮肤"]
        for _ in 0..<3 {
            if entry.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(entry.waitForExistence(timeout: 5))
        entry.tap()
        XCTAssertTrue(app.navigationBars["个性化皮肤"].waitForExistence(timeout: 5))
        let skin = app.buttons["mia-skin-holographic"]
        XCTAssertTrue(skin.waitForExistence(timeout: 5))
        skin.tap()
        XCTAssertTrue(skin.isSelected)
        app.terminate()
        app.launch()
        let avatar = app.buttons["mia-avatar"]
        XCTAssertTrue(avatar.waitForExistence(timeout: 15))
        XCTAssertTrue((avatar.value as? String ?? "").contains("蓝金星环"))
        XCTAssertTrue(app.buttons["开始说话"].exists)
    }

    func testHomeWaitsForTapBeforeDeviceDiscoveryAndActivation() {
        let app = XCUIApplication()
        app.launchArguments = ["-mia.xiaozhi.otaURL", "http://127.0.0.1:8770/ota/?activation=1",
                               "-mia.xiaozhi.websocketURL", "ws://127.0.0.1:8769/xiaozhi/v1/"]
        app.launch()
        XCTAssertTrue(app.buttons["开始说话"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.textFields["OTA 地址"].waitForExistence(timeout: 2))
        XCTAssertFalse(app.descendants(matching: .any)["xiaozhi-activation-code"].exists)
        startConversation(app)
        XCTAssertTrue(app.textFields["OTA 地址"].waitForExistence(timeout: 20))
        let code = app.descendants(matching: .any)["xiaozhi-activation-code"]
        XCTAssertTrue(code.waitForExistence(timeout: 5))
        XCTAssertEqual(code.value as? String, "123456")
    }

    func testBindingRecheckSuccessDoesNotShowOldActivationAlertOnHome() {
        let app = launch(ota: "http://127.0.0.1:8770/ota/?activation_once=1",
                         websocket: "ws://127.0.0.1:8769/xiaozhi/v1/")
        startConversation(app)
        XCTAssertTrue(app.descendants(matching: .any)["xiaozhi-activation-code"].waitForExistence(timeout: 10))
        app.buttons["检查设备绑定"].tap()
        XCTAssertTrue(app.staticTexts["设备配置已就绪"].waitForExistence(timeout: 5))
        app.buttons["完成"].tap()
        XCTAssertTrue(app.buttons["开始说话"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.alerts["连接出错"].exists)
    }
}
