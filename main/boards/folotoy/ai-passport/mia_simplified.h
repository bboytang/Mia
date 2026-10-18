#pragma once

#include "mia_simplified_dictionary.h"

#include <algorithm>
#include <cstring>
#include <iterator>
#include <string>

namespace mia_text {
// Invalid UTF-8 bytes are preserved individually; never read beyond a subtitle.
inline uint32_t Decode(const char* text, size_t remaining, size_t& length) {
    auto first = static_cast<unsigned char>(text[0]);
    length = 1;
    if (first < 0x80)
        return first;
    size_t count = first >= 0xC2 && first <= 0xDF   ? 2
                   : first >= 0xE0 && first <= 0xEF ? 3
                   : first >= 0xF0 && first <= 0xF4 ? 4
                                                    : 0;
    if (!count || count > remaining)
        return first;
    uint32_t value = first & (0x7F >> count);
    for (size_t i = 1; i < count; ++i) {
        auto byte = static_cast<unsigned char>(text[i]);
        if ((byte & 0xC0) != 0x80)
            return first;
        value = (value << 6) | (byte & 0x3F);
    }
    if ((count == 2 && value < 0x80) || (count == 3 && value < 0x800) ||
        (count == 4 && value < 0x10000) || value > 0x10FFFF || (value >= 0xD800 && value <= 0xDFFF))
        return first;
    length = count;
    return value;
}

inline void Append(std::string& output, uint32_t value) {
    if (value < 0x80)
        output += static_cast<char>(value);
    else {
        int shift = value < 0x800 ? 6 : value < 0x10000 ? 12 : 18;
        output += static_cast<char>((shift == 6    ? 0xC0
                                     : shift == 12 ? 0xE0
                                                   : 0xF0) |
                                    (value >> shift));
        for (shift -= 6; shift >= 0; shift -= 6)
            output += static_cast<char>(0x80 | ((value >> shift) & 0x3F));
    }
}

template <size_t CharacterCount, size_t PhraseCount>
inline std::string Convert(const char* text, const Character (&characters)[CharacterCount],
                           const Phrase (&phrases)[PhraseCount]) {
    std::string output;
    if (!text)
        return output;
    const size_t size = strlen(text);
    output.reserve(size);
    for (size_t offset = 0; offset < size;) {
        size_t count;
        const uint32_t code = Decode(text + offset, size - offset, count);
        // Longest phrase first preserves contextual forms such as 乾坤/乾淨.
        auto phrase =
            std::lower_bound(std::begin(phrases), std::end(phrases), code,
                             [](const Phrase& item, uint32_t key) { return item.first < key; });
        bool matched = false;
        for (; phrase != std::end(phrases) && phrase->first == code; ++phrase) {
            const size_t length = strlen(phrase->from);
            if (length <= size - offset && !memcmp(text + offset, phrase->from, length)) {
                output += phrase->to;
                offset += length;
                matched = true;
                break;
            }
        }
        if (matched)
            continue;
        auto character =
            std::lower_bound(std::begin(characters), std::end(characters), code,
                             [](const Character& item, uint32_t key) { return item.from < key; });
        if (count > 1 && character != std::end(characters) && character->from == code)
            Append(output, character->to);
        else
            output.append(text + offset, count);
        offset += count;
    }
    return output;
}
inline std::string Simplify(const char* text) {
    const auto normalized = Convert(text, kTaiwanCharacters, kTaiwanPhrases);
    return Convert(normalized.c_str(), kCharacters, kPhrases);
}
}  // namespace mia_text
