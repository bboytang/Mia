import Foundation

struct MiaCaptionTimeline {
    private let charactersPerSecond: Double
    private var characters: [Character] = []
    private var playedSeconds = 0.0
    private(set) var visibleText = ""

    init(charactersPerSecond: Double = 6) {
        self.charactersPerSecond = max(charactersPerSecond, 0.1)
    }

    mutating func handle(_ event: MiaServerEvent) {
        guard case .ttsSentence(let text) = event else { return }
        characters = Array(text)
        playedSeconds = 0
        visibleText = ""
    }

    mutating func advancePlayback(seconds: Double) {
        guard seconds > 0, !characters.isEmpty else { return }
        playedSeconds += seconds
        let count = min(characters.count, Int(playedSeconds * charactersPerSecond))
        visibleText = String(characters.prefix(count))
    }

    mutating func finishSentence() {
        visibleText = String(characters)
    }

    mutating func interrupt() {
        characters = []
        playedSeconds = 0
        visibleText = ""
    }
}
