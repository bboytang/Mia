import XCTest
@testable import Youmi

final class YoumiEmotionTests: XCTestCase {
    func testEightEmotionsHaveDistinctExpressionsAndCodableNames() throws {
        XCTAssertEqual(YoumiEmotion.allCases.count, 8)
        var expressions: [YoumiOrbExpression] = []
        for emotion in YoumiEmotion.allCases {
            let expression = YoumiOrbExpression(emotion: emotion, intensity: 1)
            XCTAssertFalse(expressions.contains(expression), emotion.rawValue)
            expressions.append(expression)
            let encoded = try JSONEncoder().encode(emotion)
            XCTAssertEqual(try JSONDecoder().decode(YoumiEmotion.self, from: encoded), emotion)
            XCTAssertFalse(emotion.displayName.isEmpty)
        }
    }

    func testZeroIntensityReturnsCalmAndStrengthIsBounded() {
        let calm = YoumiOrbExpression()
        for emotion in YoumiEmotion.allCases {
            XCTAssertEqual(YoumiOrbExpression(emotion: emotion, intensity: 0), calm)
            XCTAssertEqual(YoumiOrbExpression(emotion: emotion, intensity: -1), calm)
            XCTAssertEqual(YoumiOrbExpression(emotion: emotion, intensity: 2),
                           YoumiOrbExpression(emotion: emotion, intensity: 1))
        }
    }

    func testInvalidIntensityKeepsStableFiniteExpression() {
        for intensity in [Double.nan, .infinity, -.infinity] {
            XCTAssertEqual(YoumiOrbExpression(emotion: .happy, intensity: intensity),
                           YoumiOrbExpression(emotion: .happy, intensity: 0.5))
        }
    }

    func testStrongerEmotionIncreasesExpressionWithoutChangingIdentity() {
        let subtle = YoumiOrbExpression(emotion: .curious, intensity: 0.3)
        let strong = YoumiOrbExpression(emotion: .curious, intensity: 0.9)
        XCTAssertGreaterThan(strong.leftHeight, subtle.leftHeight)
        XCTAssertGreaterThan(strong.tilt, subtle.tilt)
        XCTAssertGreaterThan(strong.gazeX, subtle.gazeX)
        XCTAssertLessThan(strong.gazeY, subtle.gazeY)
    }

    func testFacialFeaturesDistinguishComfortSadnessAndSurprise() {
        let caring = YoumiOrbExpression(emotion: .caring, intensity: 0.65)
        let sad = YoumiOrbExpression(emotion: .sad, intensity: 0.65)
        let surprise = YoumiOrbExpression(emotion: .surprised, intensity: 0.65)
        XCTAssertGreaterThan(caring.mouthCurve, 0)
        XCTAssertLessThan(sad.mouthCurve, 0)
        XCTAssertGreaterThan(sad.browTilt, caring.browTilt)
        XCTAssertGreaterThan(surprise.eyeWidth, caring.eyeWidth)
        XCTAssertGreaterThan(surprise.mouthOpen, 0.04)
    }
}
