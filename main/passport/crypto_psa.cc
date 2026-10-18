#include "capsule.h"
#include "release_public_key.h"

#include <psa/crypto.h>

namespace mia::passport {
bool Sha256(std::span<const uint8_t> bytes, Digest& result) {
    size_t length = 0;
    return psa_crypto_init() == PSA_SUCCESS &&
           psa_hash_compute(PSA_ALG_SHA_256, bytes.data(), bytes.size(), result.data(),
                            result.size(), &length) == PSA_SUCCESS &&
           length == result.size();
}

bool VerifySignature(std::span<const uint8_t> header) {
    Digest hash;
    if (header.size() != kCapsuleHeaderSize || !Sha256(header.first(kSignedMetadataSize), hash)) {
        return false;
    }
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attributes, PSA_KEY_TYPE_ECC_PUBLIC_KEY(PSA_ECC_FAMILY_SECP_R1));
    psa_set_key_bits(&attributes, 256);
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_VERIFY_HASH);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECDSA(PSA_ALG_SHA_256));
    psa_key_id_t key = PSA_KEY_ID_NULL;
    auto status =
        psa_import_key(&attributes, kReleasePublicKey.data(), kReleasePublicKey.size(), &key);
    psa_reset_key_attributes(&attributes);
    if (status != PSA_SUCCESS) {
        return false;
    }
    status = psa_verify_hash(key, PSA_ALG_ECDSA(PSA_ALG_SHA_256), hash.data(), hash.size(),
                             header.data() + kSignedMetadataSize, 64);
    psa_destroy_key(key);
    return status == PSA_SUCCESS;
}
}  // namespace mia::passport
