import XCTest
@testable import Mia

final class MiaCaptionTimelineTests: XCTestCase {
    func testOnlyMiaSpeechAppearsAsPlaybackAdvances() {
        var captions = MiaCaptionTimeline(charactersPerSecond: 5)
        captions.handle(.userTranscript("用户说的话"))
        XCTAssertEqual(captions.visibleText, "")

        captions.handle(.ttsSentence("你好，Mia"))
        XCTAssertEqual(captions.visibleText, "")
        captions.advancePlayback(seconds: 0.2)
        XCTAssertEqual(captions.visibleText, "你")
        captions.advancePlayback(seconds: 0.4)
        XCTAssertEqual(captions.visibleText, "你好，")
    }

    func testNewSentenceAndInterruptionDiscardOldCaption() {
        var captions = MiaCaptionTimeline(charactersPerSecond: 10)
        captions.handle(.ttsSentence("第一句"))
        captions.advancePlayback(seconds: 0.2)
        XCTAssertEqual(captions.visibleText, "第一")

        captions.handle(.ttsSentence("下一句"))
        XCTAssertEqual(captions.visibleText, "")
        captions.advancePlayback(seconds: 0.1)
        XCTAssertEqual(captions.visibleText, "下")
        captions.interrupt()
        XCTAssertEqual(captions.visibleText, "")
    }

    func testComposedCharacterIsRevealedAsOneUnit() {
        var captions = MiaCaptionTimeline(charactersPerSecond: 1)
        captions.handle(.ttsSentence("你👩‍🚀好"))
        captions.advancePlayback(seconds: 2)

        XCTAssertEqual(captions.visibleText, "你👩‍🚀")
    }
}
