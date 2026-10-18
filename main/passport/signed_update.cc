#include "signed_update.h"
#include "backend_policy.h"
#include "capsule.h"

#include <esp_app_desc.h>
#include <esp_app_format.h>
#include <esp_chip_info.h>
#include <esp_crt_bundle.h>
#include <esp_flash.h>
#include <esp_http_client.h>
#include <esp_log.h>
#include <esp_ota_ops.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <nvs.h>
#include <psa/crypto.h>
#include "board.h"

#include <algorithm>
#include <atomic>
#include <cstring>
#include <memory>
#include <new>

namespace mia::passport {
namespace {
constexpr const char* kTag = "PassportOTA";
std::atomic<bool> upgrading{false};
std::atomic<bool> trial_decided{false};
esp_timer_handle_t trial_timer = nullptr;

struct Store {
    nvs_handle_t handle = 0;
    Store() { nvs_open("mia_ota", NVS_READWRITE, &handle); }
    ~Store() {
        if (handle)
            nvs_close(handle);
    }
    uint32_t Get(const char* name) {
        uint32_t value = 0;
        if (handle)
            nvs_get_u32(handle, name, &value);
        return value;
    }
    bool Put(const char* name, uint32_t value) {
        return handle && nvs_set_u32(handle, name, value) == ESP_OK;
    }
    bool Status(const char* value) {
        return handle && nvs_set_str(handle, "status", value) == ESP_OK &&
               nvs_commit(handle) == ESP_OK;
    }
    std::string Status() {
        char value[32] = {};
        size_t length = sizeof(value);
        if (!handle || nvs_get_str(handle, "status", value, &length) != ESP_OK)
            return "unknown";
        return value;
    }
};

bool HashRegion(uint32_t address, size_t size, Digest& digest) {
    std::unique_ptr<uint8_t[]> buffer(new (std::nothrow) uint8_t[4096]);
    if (!buffer)
        return false;
    psa_hash_operation_t operation = PSA_HASH_OPERATION_INIT;
    if (psa_crypto_init() != PSA_SUCCESS ||
        psa_hash_setup(&operation, PSA_ALG_SHA_256) != PSA_SUCCESS)
        return false;
    bool ok = true;
    for (size_t offset = 0; ok && offset < size; offset += 4096) {
        size_t count = std::min(size_t(4096), size - offset);
        ok = esp_flash_read(esp_flash_default_chip, buffer.get(), address + offset, count) ==
                 ESP_OK &&
             psa_hash_update(&operation, buffer.get(), count) == PSA_SUCCESS;
    }
    size_t length = 0;
    ok = ok && psa_hash_finish(&operation, digest.data(), digest.size(), &length) == PSA_SUCCESS &&
         length == 32;
    psa_hash_abort(&operation);
    return ok;
}

bool ReadExact(esp_http_client_handle_t http, uint8_t* data, size_t size, int64_t total_deadline) {
    size_t done = 0;
    auto deadline = std::min(esp_timer_get_time() + 30000000, total_deadline);
    while (done < size) {
        if (esp_timer_get_time() > deadline)
            return false;
        int count = esp_http_client_read(http, reinterpret_cast<char*>(data + done), size - done);
        if (count <= 0)
            return false;
        done += count;
    }
    return true;
}

struct Download {
    esp_http_client_handle_t http = nullptr;
    esp_ota_handle_t ota = 0;
    bool writing = false;
    ~Download() {
        if (writing)
            esp_ota_abort(ota);
        if (http) {
            esp_http_client_close(http);
            esp_http_client_cleanup(http);
        }
    }
};
}  // namespace

bool IsTrialBoot() {
    esp_ota_img_states_t state;
    return esp_ota_get_state_partition(esp_ota_get_running_partition(), &state) == ESP_OK &&
           state == ESP_OTA_IMG_PENDING_VERIFY;
}

bool NeedsBootConfirmation() {
    esp_ota_img_states_t state;
    Store store;
    return esp_ota_get_state_partition(esp_ota_get_running_partition(), &state) != ESP_OK ||
           state != ESP_OTA_IMG_VALID ||
           store.Get("confirmed") < uint32_t(CONFIG_MIA_PASSPORT_RELEASE_SEQUENCE);
}

void RollbackBoot() {
    if (!IsTrialBoot() || trial_decided.exchange(true))
        return;
    Store store;
    store.Status("health_failed");
    ESP_LOGE(kTag, "Trial boot failed; restoring previous application");
    esp_ota_mark_app_invalid_rollback_and_reboot();
    esp_restart();
}

void StartBootGuard() {
    Store store;
    const auto* running = esp_ota_get_running_partition();
    if (IsTrialBoot()) {
        trial_decided = false;
        esp_timer_create_args_t args = {};
        args.callback = [](void*) { RollbackBoot(); };
        args.name = "mia_trial";
        ESP_ERROR_CHECK(esp_timer_create(&args, &trial_timer));
        ESP_ERROR_CHECK(esp_timer_start_once(trial_timer, 120ULL * 1000000));
        ESP_LOGI(kTag, "Trial boot: authenticated voice health check required within 120s");
    } else if ((store.Status() == "trial" || store.Status() == "health_failed") &&
               store.Get("target_addr") != running->address) {
        auto* other = esp_ota_get_next_update_partition(running);
        esp_ota_img_states_t state;
        bool rolled_back = store.Status() == "health_failed" ||
                           (other && other->address == store.Get("target_addr") &&
                            esp_ota_get_state_partition(other, &state) == ESP_OK &&
                            (state == ESP_OTA_IMG_ABORTED || state == ESP_OTA_IMG_INVALID));
        store.Status(rolled_back ? "rolled_back" : "interrupted");
    } else if (store.Status() == "trial" && store.Get("target_addr") == running->address) {
        // Recover a power loss after IDF confirmation and before the NVS result commit.
        esp_ota_img_states_t state;
        if (esp_ota_get_state_partition(running, &state) == ESP_OK && state == ESP_OTA_IMG_VALID) {
            store.Put("confirmed", store.Get("target_seq"));
            store.Status("confirmed");
        }
    } else if (store.Status() == "downloading") {
        store.Status("interrupted");
    }
}

bool ConfirmBoot() {
    if (!NeedsBootConfirmation())
        return true;
    bool trial = IsTrialBoot();
    if (trial && trial_decided.exchange(true))
        return false;
    // First USB installation has no OTA selection record yet. Establish a VALID
    // baseline only after the same authenticated voice health check as an update.
    if (!trial && esp_ota_set_boot_partition(esp_ota_get_running_partition()) != ESP_OK)
        return false;
    if (esp_ota_mark_app_valid_cancel_rollback() != ESP_OK) {
        if (trial) {
            trial_decided = false;
            RollbackBoot();
        }
        return false;
    }
    if (trial_timer)
        esp_timer_stop(trial_timer);
    Store store;
    auto sequence =
        std::max(store.Get("confirmed"), uint32_t(CONFIG_MIA_PASSPORT_RELEASE_SEQUENCE));
    if (trial)
        sequence = std::max(sequence, store.Get("target_seq"));
    return store.Put("confirmed", sequence) && store.Status("confirmed");
}

std::string UpgradeStatusJson() {
    Store store;
    auto status = store.Status();
    // NVS is persistent input. Emit only known labels; never echo raw data.
    if (status != "unknown" && status != "downloading" && status != "failed" && status != "trial" &&
        status != "confirmed" && status != "interrupted" && status != "health_failed" &&
        status != "rolled_back")
        status = "unknown";
    return "{\"status\":\"" + status +
           "\",\"confirmed_sequence\":" + std::to_string(store.Get("confirmed")) +
           ",\"target_sequence\":" + std::to_string(store.Get("target_seq")) +
           ",\"trial_boot\":" + (IsTrialBoot() ? "true}" : "false}");
}

bool Upgrade(const std::string& url, std::function<void(int, size_t)> progress) {
    if (upgrading.exchange(true))
        return false;
    struct Release {
        ~Release() { upgrading = false; }
    } release;
    Store store;
    auto fail = [&]() {
        store.Status("failed");
        return false;
    };
    if (NeedsBootConfirmation() || !store.handle ||
        !IsFirmwareEndpoint(url, CONFIG_MIA_PASSPORT_OTA_URL))
        return false;
    auto& board = Board::GetInstance();
    int level = 0;
    bool charging = false, discharging = false;
    if (board.GetBatteryLevel(level, charging, discharging) && discharging && level < 25)
        return false;
    const auto* running = esp_ota_get_running_partition();
    const auto* target = esp_ota_get_next_update_partition(nullptr);
    if (!target || target->address == running->address || target->size != kSlotSize ||
        (target->address != 0x20000 && target->address != 0x360000) ||
        (target->subtype != ESP_PARTITION_SUBTYPE_APP_OTA_0 &&
         target->subtype != ESP_PARTITION_SUBTYPE_APP_OTA_1))
        return false;

    Download download;
    auto deadline = esp_timer_get_time() + 300000000;
    esp_http_client_config_t config = {};
    config.url = url.c_str();
    config.timeout_ms = 15000;
    config.disable_auto_redirect = true;
    config.crt_bundle_attach = esp_crt_bundle_attach;
    download.http = esp_http_client_init(&config);
    if (!download.http || esp_http_client_open(download.http, 0) != ESP_OK)
        return fail();
    auto length = esp_http_client_fetch_headers(download.http);
    if (esp_http_client_get_status_code(download.http) != 200 ||
        length <= int64_t(kCapsuleHeaderSize) || length > int64_t(kSlotSize + kCapsuleHeaderSize))
        return fail();
    std::array<uint8_t, kCapsuleHeaderSize> header;
    Manifest manifest;
    if (!ReadExact(download.http, header.data(), header.size(), deadline) ||
        !DecodeManifest(
            header,
            std::max(store.Get("confirmed"), uint32_t(CONFIG_MIA_PASSPORT_RELEASE_SEQUENCE)),
            manifest) ||
        !VerifySignature(header) ||
        !IsNewerVersion(manifest.version, esp_app_get_description()->version) ||
        length != int64_t(header.size() + manifest.image_size))
        return fail();
    Digest layout, assets;
    if (!HashRegion(0x8000, 4096, layout) || layout != manifest.layout_hash ||
        !HashRegion(0x660000, 0xa0000, assets) || assets != manifest.assets_hash)
        return fail();

    // Check actual ESP metadata before esp_ota_begin erases any sector.
    std::array<uint8_t, 288> first;
    if (!ReadExact(download.http, first.data(), first.size(), deadline))
        return fail();
    esp_image_header_t image;
    esp_app_desc_t desc;
    std::memcpy(&image, first.data(), sizeof(image));
    std::memcpy(&desc, first.data() + sizeof(image) + sizeof(esp_image_segment_header_t),
                sizeof(desc));
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    auto minimum_revision = image.min_chip_rev_full ? image.min_chip_rev_full : image.min_chip_rev;
    if (image.magic != ESP_IMAGE_HEADER_MAGIC || image.chip_id != 5 || (first[3] >> 4) != 3 ||
        chip.revision < minimum_revision ||
        (image.max_chip_rev_full != 0 && image.max_chip_rev_full != 65535 &&
         chip.revision > image.max_chip_rev_full) ||
        desc.magic_word != ESP_APP_DESC_MAGIC_WORD ||
        strnlen(desc.version, sizeof(desc.version)) >= sizeof(desc.version) ||
        manifest.version != desc.version ||
        std::strncmp(desc.project_name, "xiaozhi", sizeof(desc.project_name)) != 0)
        return fail();
    if (!store.Put("target_seq", manifest.sequence) || !store.Put("target_addr", target->address) ||
        !store.Status("downloading"))
        return fail();
    if (esp_ota_begin(target, manifest.image_size, &download.ota) != ESP_OK)
        return fail();
    download.writing = true;
    size_t first_offset = 0;
    auto last_report = esp_timer_get_time();
    size_t recent = 0;
    bool ok = StreamImage(
        manifest.image_size,
        [&](uint8_t* data, size_t wanted) {
            if (esp_timer_get_time() > deadline)
                return -1;
            if (first_offset < first.size()) {
                size_t count = std::min(wanted, first.size() - first_offset);
                std::memcpy(data, first.data() + first_offset, count);
                first_offset += count;
                return int(count);
            }
            return esp_http_client_read(download.http, reinterpret_cast<char*>(data), wanted);
        },
        [&](const uint8_t* data, size_t count) {
            return esp_ota_write(download.ota, data, count) == ESP_OK;
        },
        [&](size_t done) {
            auto now = esp_timer_get_time();
            if (progress && (now - last_report >= 1000000 || done == manifest.image_size)) {
                progress(done * 100 / manifest.image_size,
                         (done - recent) * 1000000 / std::max(int64_t(1), now - last_report));
                last_report = now;
                recent = done;
            }
        });
    Digest actual;
    // Hash the bytes read back from the inactive slot, not just the network stream.
    if (!ok || !HashRegion(target->address, manifest.image_size, actual) ||
        actual != manifest.image_hash)
        return fail();
    auto result = esp_ota_end(download.ota);
    download.writing = false;  // esp_ota_end frees the handle on either result.
    if (result != ESP_OK || !store.Status("trial"))
        return fail();
    if (esp_ota_set_boot_partition(target) != ESP_OK)
        return fail();
    return true;
}
}  // namespace mia::passport
