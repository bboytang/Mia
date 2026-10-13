import Foundation

enum MiaEmotion: String, Codable, CaseIterable {
    case calm, happy, curious, surprised, confused, caring, sad, playful

    var displayName: String {
        switch self {
        case .calm: return "平静"
        case .happy: return "开心"
        case .curious: return "好奇"
        case .surprised: return "惊讶"
        case .confused: return "疑惑"
        case .caring: return "关心"
        case .sad: return "失落"
        case .playful: return "俏皮"
        }
    }
}

enum MiaOrbState: String {
    case idle, listening, thinking, speaking
}

struct MiaOrbExpression: Equatable {
    var leftHeight = 0.12
    var rightHeight = 0.12
    var leftCurve = 0.0
    var rightCurve = 0.0
    var gazeX = 0.0
    var gazeY = 0.0
    var tilt = 0.0
    var warmth = 0.3

    init(emotion: MiaEmotion = .calm, intensity: Double = 0.5) {
        let strength = intensity.isFinite ? min(max(intensity, 0), 1) : 0.5
        switch emotion {
        case .calm: break
        case .happy:
            leftCurve = 1; rightCurve = 1; tilt = -2; warmth = 0.8
        case .curious:
            leftHeight = 0.15; rightHeight = 0.11
            gazeX = 0.035; gazeY = -0.025; tilt = 8; warmth = 0.45
        case .surprised:
            leftHeight = 0.18; rightHeight = 0.18
            gazeY = -0.025; warmth = 0.55
        case .confused:
            leftHeight = 0.075; rightHeight = 0.14
            gazeX = -0.02; tilt = -10; warmth = 0.25
        case .caring:
            leftHeight = 0.10; rightHeight = 0.10
            leftCurve = 0.45; rightCurve = 0.45
            gazeY = 0.025; tilt = -3; warmth = 0.75
        case .sad:
            leftHeight = 0.10; rightHeight = 0.10
            leftCurve = -0.8; rightCurve = -0.8
            gazeY = 0.035; tilt = 5; warmth = 0.18
        case .playful:
            leftHeight = 0.09; rightHeight = 0.13; leftCurve = 1
            gazeX = 0.02; gazeY = -0.015; tilt = 10; warmth = 0.9
        }
        leftHeight = 0.12 + (leftHeight - 0.12) * strength
        rightHeight = 0.12 + (rightHeight - 0.12) * strength
        leftCurve *= strength; rightCurve *= strength
        gazeX *= strength; gazeY *= strength; tilt *= strength
        warmth = 0.3 + (warmth - 0.3) * strength
    }
}
