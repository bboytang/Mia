import XCTest
@testable import Mia

final class MiaEmotionTests: XCTestCase {
    func testEightEmotionsHaveDistinctExpressionsAndCodableNames() throws {
        XCTAssertEqual(MiaEmotion.allCases.count, 8)
        var expressions: [MiaOrbExpression] = []
        for emotion in MiaEmotion.allCases {
            let expression = MiaOrbExpression(emotion: emotion, intensity: 1)
            XCTAssertFalse(expressions.contains(expression), emotion.rawValue)
            expressions.append(expression)
            let encoded = try JSONEncoder().encode(emotion)
            XCTAssertEqual(try JSONDecoder().decode(MiaEmotion.self, from: encoded), emotion)
            XCTAssertFalse(emotion.displayName.isEmpty)
        }
    }

    func testZeroIntensityReturnsCalmAndStrengthIsBounded() {
        let calm = MiaOrbExpression()
        for emotion in MiaEmotion.allCases {
            XCTAssertEqual(MiaOrbExpression(emotion: emotion, intensity: 0), calm)
            XCTAssertEqual(MiaOrbExpression(emotion: emotion, intensity: -1), calm)
            XCTAssertEqual(MiaOrbExpression(emotion: emotion, intensity: 2),
                           MiaOrbExpression(emotion: emotion, intensity: 1))
        }
    }

    func testInvalidIntensityKeepsStableFiniteExpression() {
        for intensity in [Double.nan, .infinity, -.infinity] {
            XCTAssertEqual(MiaOrbExpression(emotion: .happy, intensity: intensity),
                           MiaOrbExpression(emotion: .happy, intensity: 0.5))
        }
    }

    func testStrongerEmotionIncreasesExpressionWithoutChangingIdentity() {
        let subtle = MiaOrbExpression(emotion: .curious, intensity: 0.3)
        let strong = MiaOrbExpression(emotion: .curious, intensity: 0.9)
        XCTAssertGreaterThan(strong.leftHeight, subtle.leftHeight)
        XCTAssertGreaterThan(strong.tilt, subtle.tilt)
        XCTAssertGreaterThan(strong.gazeX, subtle.gazeX)
        XCTAssertLessThan(strong.gazeY, subtle.gazeY)
    }
}
