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

inline bool IsDiscoveryEndpoint(std::string_view url, std::string_view pin) {
    return IsPinnedEndpoint(url, pin, "http://") || IsPinnedEndpoint(url, pin, "https://");
}

inline bool IsVoiceEndpoint(std::string_view url, std::string_view pin) {
    return IsPinnedEndpoint(url, pin, "ws://") || IsPinnedEndpoint(url, pin, "wss://");
}

inline bool IsFirmwareEndpoint(std::string_view url, std::string_view discovery) {
    if (!IsDiscoveryEndpoint(discovery, discovery) || !IsDiscoveryEndpoint(url, url)) {
        return false;
    }
    auto origin_end = discovery.find('/', discovery.find("://") + 3);
    auto origin = discovery.substr(0, origin_end);
    if (!url.starts_with(origin) || url.size() <= origin.size() || url[origin.size()] != '/') {
        return false;
    }
    auto path = url.substr(origin.size());
    constexpr std::string_view manager = "/xiaozhi/otaMag/download/";
    constexpr std::string_view standalone = "/xiaozhi/ota/download/";
    size_t prefix = path.starts_with(manager)      ? manager.size()
                    : path.starts_with(standalone) ? standalone.size()
                                                   : 0;
    if (!prefix || path.size() == prefix) {
        return false;
    }
    for (char ch : path.substr(prefix)) {
        if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') ||
              ch == '-' || ch == '_' || ch == '.')) {
            return false;
        }
    }
    return path.substr(prefix) != "." && path.substr(prefix) != "..";
}

}  // namespace mia::passport
