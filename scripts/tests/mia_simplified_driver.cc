#include "mia_simplified.h"

#include <cassert>
#include <string>

int main() {
    using mia_text::Simplify;
    assert(Simplify(nullptr).empty());
    assert(Simplify("").empty());
    assert(Simplify("這是語音識別，妳現在聽得到嗎？") == "这是语音识别，妳现在听得到吗？");
    assert(Simplify("我會繼續陪著你，讓我們開始對話。") == "我会继续陪着你，让我们开始对话。");
    assert(Simplify("乾坤、乾淨、頭髮、發現、皇后、後來") == "乾坤、干净、头发、发现、皇后、后来");
    assert(Simplify("Mia 1.0.1 / Wi-Fi 😊 简体中文\n字幕") ==
           "Mia 1.0.1 / Wi-Fi 😊 简体中文\n字幕");
    assert(Simplify("陪著你讀著名的著作") == "陪着你读著名的著作");
    const std::string invalid = std::string("繁體") + "\xF0\x9F\x98";
    assert(Simplify(invalid.c_str()) == std::string("繁体") + "\xF0\x9F\x98");
    const std::string malformed = "\xED\xA0\x80\xC0\xAF\xF4\x90\x80\x80";
    assert(Simplify(malformed.c_str()) == malformed);
    // Every dictionary character is tested, including non-BMP output.
    for (const auto& item : mia_text::kCharacters) {
        std::string source, expected;
        mia_text::Append(source, item.from);
        mia_text::Append(expected, item.to);
        assert(mia_text::Convert(source.c_str(), mia_text::kCharacters, mia_text::kPhrases) ==
               expected);
    }
    // Contextual phrases must take precedence over individual characters.
    for (const auto& item : mia_text::kPhrases) {
        assert(mia_text::Convert(item.from, mia_text::kCharacters, mia_text::kPhrases) == item.to);
    }
    std::string long_text;
    for (int i = 0; i < 1000; ++i)
        long_text += "歡迎來到Mia！😊";
    const auto result = Simplify(long_text.c_str());
    assert(result.find("歡") == std::string::npos);
    assert(result.find("欢迎来到Mia！😊") == 0);
}
