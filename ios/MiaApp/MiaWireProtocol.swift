import Foundation

enum MiaServerEvent: Equatable {
    case hello(sessionID: String?)
    case ttsSentence(String)
    case other
}

enum MiaWireError: Error {
    case invalidMessage
    case invalidTransport
}

enum MiaWireProtocol {
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
            if object["state"] as? String == "sentence_start",
               let text = object["text"] as? String {
                return .ttsSentence(text)
            }
            return .other
        default:
            return .other
        }
    }
}
