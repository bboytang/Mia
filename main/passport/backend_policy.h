#pragma once

#include <string_view>

namespace mia::passport {

// The development profile trusts only explicitly configured endpoints. In particular,
// neither retained NVS nor a discovery response may redirect device credentials.
inline bool IsPinnedEndpoint(std::string_view url, std::string_view pin, std::string_view scheme) {
    if (url != pin || !url.starts_with(scheme)) {
        return false;
    }
    auto authority_end = url.find('/', scheme.size());
    if (authority_end == std::string_view::npos || authority_end == scheme.size()) {
        return false;
    }
    for (unsigned char ch : url) {
        if (ch <= 0x20 || ch >= 0x7f || ch == '\\' || ch == '@' || ch == '#' || ch == '?') {
            return false;
        }
    }
    return true;
}

}  // namespace mia::passport
