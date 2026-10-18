#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <span>
#include <string>
#include <string_view>

namespace mia::passport {

inline constexpr size_t kCapsuleHeaderSize = 256;
inline constexpr size_t kSignedMetadataSize = 192;
inline constexpr size_t kSlotSize = 0x300000;
using Digest = std::array<uint8_t, 32>;

struct Manifest {
    uint32_t image_size = 0;
    uint32_t sequence = 0;
    std::string version;
    Digest image_hash{};
    Digest layout_hash{};
    Digest assets_hash{};
};

// Decode only canonical v1 metadata. Signature verification must precede any erase.
bool DecodeManifest(std::span<const uint8_t> header, uint32_t confirmed_sequence, Manifest& result);
bool VerifySignature(std::span<const uint8_t> header);
bool Sha256(std::span<const uint8_t> bytes, Digest& result);
bool IsNewerVersion(std::string_view candidate, std::string_view current);

// Read exactly one bounded signed image. A negative/zero read is a failed download.
// Both the actual ESP adapter and host fault tests use this streaming loop.
bool StreamImage(size_t size, const std::function<int(uint8_t*, size_t)>& read,
                 const std::function<bool(const uint8_t*, size_t)>& write,
                 const std::function<void(size_t)>& progress);

}  // namespace mia::passport
