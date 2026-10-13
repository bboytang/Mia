import Foundation

struct MiaCaptionTimeline {
    private var sentences: [Int: String] = [:]
    private var nextSentenceID = 0
    private var playingSentenceID = -1
    private(set) var receivingSentenceID: Int?
    private(set) var visibleText = ""

    mutating func handle(_ event: MiaServerEvent) {
        let text: String
        switch event {
        case .ttsSentence(let value), .expressiveSentence(let value, _, _): text = value
        default: return
        }
        receivingSentenceID = nextSentenceID
        sentences[nextSentenceID] = text
        nextSentenceID += 1
    }

    mutating func advancePlayback(sentenceID: Int) {
        guard sentenceID > playingSentenceID, let text = sentences[sentenceID] else { return }
        playingSentenceID = sentenceID
        visibleText = text
        sentences = sentences.filter { $0.key >= sentenceID }
    }

    mutating func interrupt() {
        sentences.removeAll()
        receivingSentenceID = nil
        playingSentenceID = -1
        visibleText = ""
    }
}
