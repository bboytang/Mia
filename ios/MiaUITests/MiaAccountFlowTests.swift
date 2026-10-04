import XCTest

final class MiaAccountFlowTests: XCTestCase {
    private func launch() -> XCUIApplication {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.buttons["设置"].waitForExistence(timeout: 15))
        return app
    }

    private func capture(_ name: String, app: XCUIApplication) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testOrbOpensLoginAndRegistrationWithoutTokenEntry() {
        let app = launch()
        app.buttons["开始说话"].tap()
        XCTAssertTrue(app.navigationBars["登录 Mia"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.textFields["用户名"].exists)
        XCTAssertTrue(app.secureTextFields["密码"].exists)
        XCTAssertFalse(app.secureTextFields["网关访问令牌"].exists)
        capture("mia-account-login", app: app)
        app.buttons["没有账号，去注册"].tap()
        XCTAssertTrue(app.navigationBars["注册 Mia 账号"].exists)
        XCTAssertTrue(app.secureTextFields["再次输入密码"].exists)
        capture("mia-account-register", app: app)
        app.buttons["取消"].tap()
        XCTAssertTrue(app.buttons["设置"].waitForExistence(timeout: 5))
    }

    func testSettingsUsesAccountsAndHidesMaintenanceControls() {
        let app = launch()
        app.buttons["设置"].tap()
        XCTAssertTrue(app.buttons["登录或注册"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.secureTextFields["网关访问令牌"].exists)
        capture("mia-account-settings", app: app)
        app.buttons["登录或注册"].tap()
        XCTAssertTrue(app.navigationBars["登录 Mia"].waitForExistence(timeout: 5))
        app.buttons["取消"].tap()
        app.buttons["高级维护"].tap()
        XCTAssertTrue(app.switches["使用维护令牌"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.secureTextFields["网关访问令牌"].exists)
    }
}
