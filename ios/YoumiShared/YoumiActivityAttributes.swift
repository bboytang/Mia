import ActivityKit
import Foundation

struct MiaActivityAttributes: ActivityAttributes {
    enum Phase: String, Codable, Hashable {
        case standby, connecting, listening, thinking, speaking

        var title: String {
            switch self {
            case .standby: "待呼叫"
            case .connecting: "正在连接"
            case .listening: "正在聆听"
            case .thinking: "正在思考"
            case .speaking: "正在回答"
            }
        }

        var symbol: String {
            switch self {
            case .standby: "moon.zzz.fill"
            case .connecting: "network"
            case .listening: "mic.fill"
            case .thinking: "ellipsis"
            case .speaking: "waveform"
            }
        }
    }

    struct ContentState: Codable, Hashable {
        var phase: Phase
        var emotion: String
        var intensity: Double

        init(phase: Phase, emotion: String = "calm", intensity: Double = 0) {
            self.phase = phase
            self.emotion = ["calm", "happy", "curious", "surprised", "confused", "caring", "sad", "playful"]
                .contains(emotion) ? emotion : "calm"
            self.intensity = intensity.isFinite ? min(1, max(0, intensity)) : 0
        }
    }

    var name: String = "Youmi"
}
