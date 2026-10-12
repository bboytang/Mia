import Foundation

enum MiaServerEvent: Equatable {
    case hello(sessionID: String?, sampleRate: Int)
    case ttsStart
    case ttsSentence(String)
    case ttsStop
    case userTranscript(String)
    case emotion(String)
    case assistantText(String)
    case serverError(String)
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
            let audio = object["audio_params"] as? [String: Any]
            guard let id = object["session_id"] as? String, !id.isEmpty, id.count <= 256,
                  let sampleRate = audio?["sample_rate"] as? Int,
                  [8_000, 12_000, 16_000, 24_000, 48_000].contains(sampleRate),
                  audio?["format"] as? String == "opus", audio?["channels"] as? Int == 1,
                  audio?["frame_duration"] as? Int == 60 else { throw MiaWireError.invalidMessage }
            return .hello(sessionID: id,
                          sampleRate: sampleRate)
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
            if let text = object["text"] as? String { return .assistantText(text) }
            if let emotion = object["emotion"] as? String {
                return .emotion(emotion)
            }
            return .other
        case "error":
            if let message = object["message"] as? String {
                return .serverError(message)
            }
            return .other
        default:
            return .other
        }
    }
}
