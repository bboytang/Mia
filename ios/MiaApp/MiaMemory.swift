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
    let management: MiaMemoryManagement?
}


struct MiaMemoryManagement: Decodable {
    let version: Int
    let actions: [String]
    func supports(_ action: String) -> Bool { version == 1 && actions.contains(action) }
}

struct MiaEventList: Decodable {
    struct Event: Decodable, Identifiable {
        let id: String
        let eventType: String
        let state: String
        let version: Int
        let userExcerpt: String?
        let assistantExcerpt: String?
        enum CodingKeys: String, CodingKey {
            case id, state, version
            case eventType = "event_type"
            case userExcerpt = "user_excerpt", assistantExcerpt = "assistant_excerpt"
        }
        var title: String {
            switch eventType {
            case "continuity": "记忆连续性"
            case "boundary": "互动边界"
            case "reflection": "交流中的看法"
            default: "互动记录"
            }
        }
        var stateLabel: String {
            switch state {
            case "active": "已确认"
            case "invalidated": "依据已失效"
            default: "待实际交流确认"
            }
        }
    }
    let events: [Event]
}

struct MiaEmotionTracking: Decodable {
    struct Consent: Decodable {
        let enabled: Int
        let version: Int
    }
    struct Observation: Decodable, Identifiable {
        let id: String
        let tendency: String
        let sourceKind: String
        let sourceExcerpt: String
        let confidence: Double
        let observedAt: Double
        let version: Int?
        enum CodingKeys: String, CodingKey {
            case id, tendency, confidence, version
            case sourceKind = "source_kind", sourceExcerpt = "source_excerpt", observedAt = "observed_at"
        }
    }
    struct Trend: Decodable {
        struct Group: Decodable {
            let count: Int
            let sessions: Int
            let distribution: [String: Int]
        }
        let status: String
        let groups: [String: Group]?
    }
    let consent: Consent
    let trend: Trend
    let observations: [Observation]?

    static func tendencyLabel(_ tendency: String) -> String {
        ["positive": "愉快", "negative": "低落", "neutral": "平静", "mixed": "复杂"][tendency] ?? "未分类"
    }
}

struct MiaMemoryTask: Decodable, Equatable {
    let id: String?
    let state: String?
    let status: String?
    let confirmationRequired: Bool?
    enum CodingKeys: String, CodingKey {
        case id, state, status
        case confirmationRequired = "confirmation_required"
    }
    var label: String {
        switch state ?? status ?? "" {
        case "committed": confirmationRequired == true ? "已整理，有内容等待你确认" : "已保存"
        case "accepted", "pending", "extracting", "validated", "running", "retry_wait": "已接收，正在整理，尚未确认保存"
        case "empty": "本次没有需要保存的内容"
        case "cancelled": "整理已取消，未保存本次内容"
        case "failed", "queue_full", "unavailable": "本次整理失败，未确认保存"
        default: "本次整理未完成，请稍后查看或重试"
        }
    }
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
