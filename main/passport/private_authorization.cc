#include "private_authorization.h"

#include "application.h"
#include "board.h"
#include "display.h"
#include "settings.h"
#include "system_info.h"

#include <esp_crt_bundle.h>
#include <esp_http_client.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_timer.h>
#include <cJSON.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <nvs.h>

#include <array>
#include <memory>

namespace mia::passport {
namespace {
constexpr char kTag[] = "MiaPrivate";
constexpr char kExchange[] = "https://43.143.230.174/xiaozhi/device/mia-auth/exchange";
constexpr char kRenew[] = "https://43.143.230.174/xiaozhi/device/mia-auth/renew";
using Json = std::unique_ptr<cJSON, decltype(&cJSON_Delete)>;

struct Response {
    std::string credential;
    std::string pending_code;
    bool denied = false;
};

bool TextEquals(const cJSON* object, const char* field, const std::string& expected) {
    const auto* item = cJSON_GetObjectItemCaseSensitive(object, field);
    return cJSON_IsString(item) && item->valuestring && expected == item->valuestring;
}

Response Request(bool renew, const std::string& proof) {
    const auto device = SystemInfo::GetMacAddress();
    const auto client = Board::GetInstance().GetUuid();
    Json body(cJSON_CreateObject(), cJSON_Delete);
    if (!body)
        return {};
    if (!renew)
        cJSON_AddBoolToObject(body.get(), "hardware_pairing", true);
    cJSON_AddStringToObject(body.get(), "device_id", device.c_str());
    cJSON_AddStringToObject(body.get(), "client_id", client.c_str());
    cJSON_AddStringToObject(body.get(), renew ? "private_credential" : "authorization_code",
                            proof.c_str());
    std::unique_ptr<char, decltype(&cJSON_free)> encoded(cJSON_PrintUnformatted(body.get()),
                                                         cJSON_free);
    if (!encoded)
        return {};
    const std::string payload(encoded.get());
    esp_http_client_config_t config = {};
    config.url = renew ? kRenew : kExchange;
    config.timeout_ms = 5000;
    config.disable_auto_redirect = true;
    config.crt_bundle_attach = esp_crt_bundle_attach;
    auto http = esp_http_client_init(&config);
    if (!http)
        return {};
    struct Close {
        esp_http_client_handle_t http;
        ~Close() {
            esp_http_client_close(http);
            esp_http_client_cleanup(http);
        }
    } close{http};
    esp_http_client_set_method(http, HTTP_METHOD_POST);
    esp_http_client_set_header(http, "Content-Type", "application/json");
    if (esp_http_client_open(http, payload.size()) != ESP_OK ||
        esp_http_client_write(http, payload.data(), payload.size()) != int(payload.size()))
        return {};
    esp_http_client_fetch_headers(http);
    if (esp_http_client_get_status_code(http) != 200)
        return {};
    std::string response;
    std::array<char, 512> buffer;
    const auto deadline = esp_timer_get_time() + 15000000;
    while (esp_timer_get_time() < deadline) {
        int count = esp_http_client_read(http, buffer.data(), buffer.size());
        if (count < 0 || response.size() + count > 4096)
            return {};
        if (count == 0)
            break;
        response.append(buffer.data(), count);
    }
    if (!esp_http_client_is_complete_data_received(http))
        return {};
    Json root(cJSON_Parse(response.c_str()), cJSON_Delete);
    const auto* code = cJSON_GetObjectItemCaseSensitive(root.get(), "code");
    if (!cJSON_IsNumber(code))
        return {};
    if (code->valuedouble != 0)
        return {.denied = true};
    const auto* data = cJSON_GetObjectItemCaseSensitive(root.get(), "data");
    const auto* pending = cJSON_GetObjectItemCaseSensitive(data, "pending_code");
    if (cJSON_IsString(pending) && pending->valuestring &&
        IsHardwareDisplayCode(pending->valuestring) && TextEquals(data, "device_id", device) &&
        TextEquals(data, "client_id", client))
        return {.pending_code = pending->valuestring};
    const auto* scope = cJSON_GetObjectItemCaseSensitive(data, "scope");
    const auto* credential = cJSON_GetObjectItemCaseSensitive(data, "private_credential");
    if (!cJSON_IsString(credential) || !credential->valuestring ||
        !IsPrivateCredential(credential->valuestring) || !TextEquals(scope, "device_id", device) ||
        !TextEquals(scope, "client_id", client) || !TextEquals(scope, "persona_id", "mia"))
        return {};
    return {.credential = credential->valuestring};
}

bool Store(const std::string& credential) {
    nvs_handle_t handle;
    if (!IsPrivateCredential(credential) ||
        nvs_open("mia_private", NVS_READWRITE, &handle) != ESP_OK)
        return false;
    auto error = nvs_set_str(handle, "credential", credential.c_str());
    if (error == ESP_OK) {
        nvs_erase_key(handle, "pending");
        error = nvs_commit(handle);
    }
    nvs_close(handle);
    return error == ESP_OK;
}

void Show(const std::string& message) {
    Application::GetInstance().Schedule([message]() {
        Board::GetInstance().GetDisplay()->SetChatMessage("system", message.c_str());
    });
}
}  // namespace

std::optional<std::string> ReadPrivateCredential() {
    nvs_handle_t handle;
    auto error = nvs_open("mia_private", NVS_READONLY, &handle);
    if (error == ESP_ERR_NVS_NOT_FOUND)
        return std::nullopt;
    if (error != ESP_OK)
        return std::string();
    std::array<char, 44> value{};
    size_t length = value.size();
    error = nvs_get_str(handle, "credential", value.data(), &length);
    nvs_close(handle);
    if (error == ESP_ERR_NVS_NOT_FOUND)
        return std::nullopt;
    if (error != ESP_OK || length != value.size() || !IsPrivateCredential(value.data()))
        return std::string();
    return std::string(value.data());
}

void EnsurePrivateAuthorization() {
    const auto existing = ReadPrivateCredential();
    if (existing && IsPrivateCredential(*existing)) {
        const auto renewal = Request(true, *existing);
        if (!renewal.credential.empty()) {
            if (!Store(renewal.credential))
                ESP_LOGE(kTag, "Cannot persist renewed authorization; reauthorization required");
            return;
        }
        if (!renewal.denied)
            return;  // Keep the prior credential on transport failure; no insecure fallback.
    }
    std::string code;
    {
        // Keep the device-only proof across a restart during the ten-minute flow.
        Settings settings("mia_private", true);
        code = settings.GetString("pending");
        bool valid = code.size() == 32;
        for (unsigned char ch : code)
            valid = valid && ((ch >= 'a' && ch <= 'f') || (ch >= '0' && ch <= '9'));
        if (!valid) {
            std::array<unsigned char, 16> bytes;
            esp_fill_random(bytes.data(), bytes.size());
            constexpr char hex[] = "0123456789abcdef";
            code.clear();
            for (auto byte : bytes) {
                code += hex[byte >> 4];
                code += hex[byte & 15];
            }
            settings.SetString("pending", code);
        }
    }
    Show("正在连接硬件授权服务");
    std::string displayed;
    const auto deadline = esp_timer_get_time() + 600000000;
    while (esp_timer_get_time() < deadline) {
        const auto result = Request(false, code);
        if (!result.pending_code.empty() && result.pending_code != displayed) {
            displayed = result.pending_code;
            Show("在后台点硬件授权\n" + displayed);
        }
        if (!result.credential.empty()) {
            if (Store(result.credential))
                Show("硬件授权已完成");
            else
                Show("授权保存失败，请重启后重新授权");
            return;
        }
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
    Show("硬件授权已超时，请重启后重试");
}
}  // namespace mia::passport
