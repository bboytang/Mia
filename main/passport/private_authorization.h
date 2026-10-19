#pragma once

#include <optional>
#include <string>
#include <string_view>

namespace mia::passport {

inline constexpr char kPrivateVoiceUrl[] = "wss://43.143.230.174:8000/xiaozhi/v1/";

inline bool IsPrivateCredential(std::string_view value) {
    if (value.size() != 43)
        return false;
    for (unsigned char ch : value) {
        if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') ||
              ch == '-' || ch == '_'))
            return false;
    }
    return true;
}

inline bool IsHardwareDisplayCode(std::string_view value) {
    if (value.size() != 6)
        return false;
    for (unsigned char ch : value) {
        if (ch < '0' || ch > '9')
            return false;
    }
    return true;
}

// nullopt means not enrolled; an empty value means invalid/unreadable enrollment.
// Invalid enrollment must not cause a downgrade to the old unencrypted transport.
std::optional<std::string> ReadPrivateCredential();
// Runs on the existing activation task, after signed-OTA boot confirmation.
void EnsurePrivateAuthorization();

}  // namespace mia::passport
