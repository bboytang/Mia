#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
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
    Error
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
    int progress = -1;
    bool connected = false;
    bool charging = false;
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
inline char Candidate(int bank, int cell) {
    int value = 32 + bank * 9 + cell;
    return cell >= 0 && cell < 9 && value <= 126 ? char(value) : 0;
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
