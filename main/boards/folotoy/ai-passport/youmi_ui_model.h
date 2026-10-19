#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "mia_face.h"

namespace youmi_ui {
enum class Page {
    Boot,
    Face,
    Emotions,
    Settings,
    Wifi,
    Password,
    Connecting,
    Success,
    Ota,
    Info,
    Error,
    DisplaySettings
};
enum class Activity { Idle, Listening, Thinking, Speaking, Offline };
enum class Key { Up, Down, Ok, Back };
struct Network {
    char ssid[33]{};
    int rssi = -100;
    int auth = 0;
};
struct Model {
    Page page = Page::Boot;
    Activity activity = Activity::Idle;
    mia_face::Mood mood = mia_face::Mood::Neutral;
    char clock[6] = "--:--";
    char text[193]{};
    char notice[129]{};
    char ssid[33]{};
    char password[65]{};
    std::array<Network, 12> networks{};
    int network_count = 0;
    int selected = 0;
    int bank = 0;
    int battery = -1;
    int brightness = 100;
    int progress = -1;
    bool connected = false;
    bool charging = false;
    bool muted = false;
    bool editing_ssid = false;
    bool allow_open = false;
    bool audio_active = false;
    bool busy = false;
    uint32_t tick = 0;
};
template <size_t N>
inline void Copy(char (&to)[N], const char* from) {
    std::snprintf(to, N, "%s", from ? from : "");
    // Do not leave a partial UTF-8 code point at the end of a bounded label.
    size_t n = std::strlen(to);
    if (n == N - 1) {
        size_t start = n;
        while (start && (static_cast<unsigned char>(to[start - 1]) & 0xC0) == 0x80)
            --start;
        if (start && static_cast<unsigned char>(to[start - 1]) >= 0xC0) {
            const auto lead = static_cast<unsigned char>(to[start - 1]);
            const size_t expected = lead < 0xE0 ? 2 : lead < 0xF0 ? 3 : 4;
            if (n - start + 1 < expected)
                to[start - 1] = 0;
        }
    }
}
// Business messages and network events share these transitions in firmware and host tests.
inline void ApplyMessage(Model& m, const char* role, const char* content, bool activating = false) {
    Copy(m.text, content);
    if (role && !std::strcmp(role, "system") && content && *content &&
        (m.page == Page::Boot || (m.page == Page::Face && m.activity == Activity::Idle) ||
         (activating && m.page != Page::Ota && m.page != Page::Connecting && m.page != Page::Wifi &&
          m.page != Page::Password)))
        m.page = Page::Info;
    if (role && !std::strcmp(role, "user") && content && *content) {
        m.activity = Activity::Thinking;
        m.page = Page::Face;
    }
    if (m.page == Page::Ota && content) {
        char* end = nullptr;
        const long progress = std::strtol(content, &end, 10);
        if (end != content && *end == '%' && progress >= 0 && progress <= 100)
            m.progress = int(progress);
    }
}
inline bool ApplyConnection(Model& m, bool connected, const char* ssid, bool config_mode) {
    m.connected = connected;
    if (connected && m.page == Page::Connecting && ssid && !std::strcmp(m.ssid, ssid)) {
        m.page = Page::Success;
        m.busy = false;
        std::fill(std::begin(m.password), std::end(m.password), 0);
        return true;
    }
    if (connected && m.activity == Activity::Offline)
        m.activity = Activity::Idle;
    else if (!connected && !config_mode && m.page == Page::Face)
        m.activity = Activity::Offline;
    return false;
}
inline char Candidate(int bank, int cell) {
    if (bank < 0 || bank > 10 || cell < 0 || cell >= 9)
        return 0;
    const int index = bank * 9 + cell;
    if (index < 9)
        return char('1' + index);
    if (index == 9)
        return '0';
    if (index < 36)
        return char('a' + index - 10);
    if (index < 62)
        return char('A' + index - 36);
    const int symbol = index - 62;
    if (symbol < 16)
        return char(32 + symbol);
    if (symbol < 23)
        return char(58 + symbol - 16);
    if (symbol < 29)
        return char(91 + symbol - 23);
    return symbol < 33 ? char(123 + symbol - 29) : 0;
}
inline bool ValidPassword(const char* password) {
    const size_t n = std::strlen(password);
    if (n < 8 || n > 64)
        return false;
    for (size_t i = 0; i < n; ++i) {
        const auto c = static_cast<unsigned char>(password[i]);
        if (n == 64 ? !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))
                    : c < 32 || c > 126)
            return false;
    }
    return true;
}
}  // namespace youmi_ui
