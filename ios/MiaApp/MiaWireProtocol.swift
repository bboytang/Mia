import Foundation

enum MiaServerEvent: Equatable {
    case hello(sessionID: String?)
    case ttsStart
    case ttsSentence(String)
    case ttsStop
    case userTranscript(String)
    case emotion(String)
    case other
}

enum MiaWireError: Error {
    case invalidMessage
    case invalidTransport
}

enum MiaWireProtocol {
    static func startListening(sessionID: String?) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "session_id": sessionID ?? "",
            "type": "listen",
            "state": "start",
            "mode": "manual",
        ])
    }

    static func stopListening(sessionID: String?) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "session_id": sessionID ?? "",
            "type": "listen",
            "state": "stop",
        ])
    }

    static func abort(sessionID: String?) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "session_id": sessionID ?? "",
            "type": "abort",
        ])
    }

    static func hello() throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "type": "hello",
            "version": 1,
            "transport": "websocket",
            "audio_params": [
                "format": "opus",
                "sample_rate": 16_000,
                "channels": 1,
                "frame_duration": 60,
            ],
        ])
    }

    static func parseServerEvent(_ data: Data) throws -> MiaServerEvent {
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = object["type"] as? String else {
            throw MiaWireError.invalidMessage
        }

        switch type {
        case "hello":
            guard object["transport"] as? String == "websocket" else {
                throw MiaWireError.invalidTransport
            }
            return .hello(sessionID: object["session_id"] as? String)
        case "tts":
            switch object["state"] as? String {
            case "start":
                return .ttsStart
            case "stop":
                return .ttsStop
            case "sentence_start":
                if let text = object["text"] as? String {
                    return .ttsSentence(text)
                }
            default:
                break
            }
            return .other
        case "stt":
            if let text = object["text"] as? String {
                return .userTranscript(text)
            }
            return .other
        case "llm":
            if let emotion = object["emotion"] as? String {
                return .emotion(emotion)
            }
            return .other
        default:
            return .other
        }
    }
}
