#include "capsule.h"

#include <algorithm>
#include <cstring>

namespace mia::passport {
namespace {
uint32_t U32(const uint8_t* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

bool Text(std::span<const uint8_t> data, std::string& value) {
    auto end = std::find(data.begin(), data.end(), 0);
    if (end == data.begin() || end == data.end() ||
        !std::all_of(end, data.end(), [](uint8_t ch) { return ch == 0; })) {
        return false;
    }
    value.assign(data.begin(), end);
    return true;
}
}  // namespace

bool DecodeManifest(std::span<const uint8_t> header, uint32_t confirmed_sequence,
                    Manifest& result) {
    if (header.size() != kCapsuleHeaderSize || std::memcmp(header.data(), "MIAOTA1\0", 8) != 0 ||
        U32(header.data() + 8) != 1 || U32(header.data() + 20) != 0x800000 ||
        U32(header.data() + 24) != 5 || U32(header.data() + 28) != 0) {
        return false;
    }
    Manifest parsed;
    parsed.image_size = U32(header.data() + 12);
    parsed.sequence = U32(header.data() + 16);
    std::string board;
    if (parsed.image_size < 288 || parsed.image_size > kSlotSize ||
        parsed.sequence <= confirmed_sequence || !Text(header.subspan(32, 32), board) ||
        board != "mia-ai-passport" || !Text(header.subspan(64, 32), parsed.version)) {
        return false;
    }
    bool digit = false;
    for (char ch : parsed.version) {
        if (ch >= '0' && ch <= '9') {
            digit = true;
        } else if (ch == '.' && digit) {
            digit = false;
        } else {
            return false;
        }
    }
    if (!digit) {
        return false;
    }
    std::copy_n(header.data() + 96, 32, parsed.image_hash.begin());
    std::copy_n(header.data() + 128, 32, parsed.layout_hash.begin());
    std::copy_n(header.data() + 160, 32, parsed.assets_hash.begin());
    result = parsed;
    return true;
}

bool IsNewerVersion(std::string_view candidate, std::string_view current) {
    auto next = [](std::string_view& value) {
        auto end = value.find('.');
        auto part = value.substr(0, end);
        value = end == std::string_view::npos ? std::string_view{} : value.substr(end + 1);
        while (part.size() > 1 && part.front() == '0')
            part.remove_prefix(1);
        return part.empty() ? std::string_view("0") : part;
    };
    while (!candidate.empty() || !current.empty()) {
        auto a = next(candidate);
        auto b = next(current);
        if (a.size() != b.size())
            return a.size() > b.size();
        if (a != b)
            return a > b;
    }
    return false;
}

bool StreamImage(size_t size, const std::function<int(uint8_t*, size_t)>& read,
                 const std::function<bool(const uint8_t*, size_t)>& write,
                 const std::function<void(size_t)>& progress) {
    if (!size || size > kSlotSize) {
        return false;
    }
    std::array<uint8_t, 4096> buffer;
    size_t done = 0;
    while (done < size) {
        size_t wanted = std::min(buffer.size(), size - done);
        int count = read(buffer.data(), wanted);
        if (count <= 0 || size_t(count) > wanted || !write(buffer.data(), count)) {
            return false;
        }
        done += count;
        if (progress) {
            progress(done);
        }
    }
    uint8_t extra;
    return read(&extra, 1) == 0;
}
}  // namespace mia::passport
