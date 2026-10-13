import Foundation

struct MiaMemoryRecord: Decodable, Identifiable {
    let id: String
    let category: String
    let content: String
    let source: String
    let confirmed: Bool
}

struct MiaPersonality: Decodable {
    struct Trait: Decodable, Identifiable {
        let name: String
        let description: String
        let evidenceIDs: [String]
        var id: String { name }
        enum CodingKeys: String, CodingKey {
            case name, description
            case evidenceIDs = "evidence_ids"
        }
    }
    let version: Int
    let traits: [Trait]
}

struct MiaMemorySnapshot: Decodable {
    let memories: [MiaMemoryRecord]
    let paused: Bool
    let personality: MiaPersonality
}

enum MiaMemoryError: LocalizedError {
    case unavailable, busy, rejected
    var errorDescription: String? {
        switch self {
        case .unavailable: "当前服务端未响应记忆管理，请确认已安装 Mia 记忆扩展。"
        case .busy: "上一项记忆操作尚未完成，请稍后再试。"
        case .rejected: "服务端未完成这项记忆操作，请重试。"
        }
    }
}

struct MiaReplyExpression: Equatable {
    var emotion: MiaEmotion = .calm
    var intensity: Double = 0.5

    init(emotion: String = "calm", intensity: Double = 0.5) {
        let aliases = ["neutral": "calm", "thinking": "curious", "surprise": "surprised",
                       "confusion": "confused", "loving": "caring", "love": "caring",
                       "laughing": "happy", "funny": "playful", "winking": "playful"]
        self.emotion = MiaEmotion(rawValue: aliases[emotion] ?? emotion) ?? .calm
        self.intensity = intensity.isFinite ? min(max(intensity, 0), 1) : 0.5
    }
}
