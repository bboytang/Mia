import XCTest
@testable import Youmi

final class YoumiCaptionTimelineTests: XCTestCase {
    func testOnlyYoumiSentenceAppearsWhenItsOwnAudioPlays() throws {
        var captions = YoumiCaptionTimeline()
        captions.handle(.userTranscript("用户说的话"))
        XCTAssertEqual(captions.visibleText, "")

        captions.handle(.ttsSentence("你好，Youmi。"))
        XCTAssertEqual(captions.visibleText, "")
        captions.advancePlayback(sentenceID: try XCTUnwrap(captions.receivingSentenceID))
        XCTAssertEqual(captions.visibleText, "你好，Youmi。")
    }

    func testPrefetchedSentenceDoesNotReplacePlayingSentenceOrRegress() throws {
        var captions = YoumiCaptionTimeline()
        captions.handle(.ttsSentence("第一句"))
        let first = try XCTUnwrap(captions.receivingSentenceID)
        captions.advancePlayback(sentenceID: first)
        XCTAssertEqual(captions.visibleText, "第一句")

        captions.handle(.ttsSentence("下一句"))
        let second = try XCTUnwrap(captions.receivingSentenceID)
        XCTAssertEqual(captions.visibleText, "第一句")
        captions.advancePlayback(sentenceID: first)
        XCTAssertEqual(captions.visibleText, "第一句")
        captions.advancePlayback(sentenceID: second)
        XCTAssertEqual(captions.visibleText, "下一句")
        captions.advancePlayback(sentenceID: first)
        XCTAssertEqual(captions.visibleText, "下一句")
    }

    func testInterruptionDiscardsCaptionAndOldSentenceIDs() throws {
        var captions = YoumiCaptionTimeline()
        captions.handle(.ttsSentence("旧回复"))
        let old = try XCTUnwrap(captions.receivingSentenceID)
        captions.advancePlayback(sentenceID: old)
        captions.interrupt()
        XCTAssertEqual(captions.visibleText, "")
        XCTAssertNil(captions.receivingSentenceID)
        captions.handle(.ttsSentence("新回复"))
        captions.advancePlayback(sentenceID: old)
        XCTAssertEqual(captions.visibleText, "")
        captions.advancePlayback(sentenceID: try XCTUnwrap(captions.receivingSentenceID))
        XCTAssertEqual(captions.visibleText, "新回复")
    }

    func testFullSentencePreservesComposedCharacters() throws {
        var captions = YoumiCaptionTimeline()
        captions.handle(.ttsSentence("你👩‍🚀好"))
        captions.advancePlayback(sentenceID: try XCTUnwrap(captions.receivingSentenceID))
        XCTAssertEqual(captions.visibleText, "你👩‍🚀好")
    }

    func testSentenceWithoutAudioNeverFlashesItsCaption() throws {
        var captions = YoumiCaptionTimeline()
        captions.handle(.ttsSentence("没有音频的句子"))
        captions.handle(.ttsSentence("有音频的句子"))
        XCTAssertEqual(captions.visibleText, "")
        captions.advancePlayback(sentenceID: try XCTUnwrap(captions.receivingSentenceID))
        XCTAssertEqual(captions.visibleText, "有音频的句子")
    }
}
