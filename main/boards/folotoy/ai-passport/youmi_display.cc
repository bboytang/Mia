#include "sdkconfig.h"

#if CONFIG_MIA_PASSPORT_DEVELOPMENT
#include <esp_app_desc.h>
#include <esp_heap_caps.h>
#include <esp_http_client.h>
#include <esp_timer.h>
#include <cJSON.h>
#include <wifi_manager.h>
#include <cstdlib>
#include <ctime>
#include <memory>
#include "application.h"
#include "assets/lang_config.h"
#include "audio_codec.h"
#include "board.h"
#include "lvgl_font.h"
#include "lvgl_theme.h"
#include "mia_simplified.h"
#include "ota.h"
#include "youmi_display.h"
#include "youmi_ui_draw.h"

using namespace youmi_ui;
namespace {
constexpr const char* kTag = "YoumiUI";
// Reuse the existing esp-wifi-connect 3.3.1 provisioning server. Never own
// scans or read/clear the driver's scan result list behind WifiManager.
std::unique_ptr<char[]> PortalRequest(const char* path, const char* body = nullptr) {
    char url[64];
    std::snprintf(url, sizeof(url), "http://127.0.0.1%s", path);
    esp_http_client_config_t cfg{};
    cfg.url = url;
    cfg.timeout_ms = body ? 60000 : 5000;
    cfg.disable_auto_redirect = true;
    auto client = esp_http_client_init(&cfg);
    if (!client)
        return nullptr;
    struct Cleanup {
        esp_http_client_handle_t client;
        ~Cleanup() { esp_http_client_cleanup(client); }
    } cleanup{client};
    if (body) {
        esp_http_client_set_method(client, HTTP_METHOD_POST);
        esp_http_client_set_header(client, "Content-Type", "application/json");
    }
    const int length = body ? std::strlen(body) : 0;
    if (esp_http_client_open(client, length) != ESP_OK)
        return nullptr;
    int written = 0;
    while (written < length) {
        int n = esp_http_client_write(client, body + written, length - written);
        if (n <= 0)
            return nullptr;
        written += n;
    }
    esp_http_client_fetch_headers(client);
    if (esp_http_client_get_status_code(client) != 200)
        return nullptr;
    constexpr int capacity = 4096;
    auto data = std::unique_ptr<char[]>(new (std::nothrow) char[capacity + 1]);
    if (!data)
        return nullptr;
    int used = 0;
    while (!esp_http_client_is_complete_data_received(client)) {
        if (used == capacity)
            return nullptr;
        int n = esp_http_client_read(client, data.get() + used, capacity - used);
        if (n < 0)
            return nullptr;
        if (n == 0) {
            if (!esp_http_client_is_complete_data_received(client))
                return nullptr;
            break;
        }
        used += n;
    }
    data[used] = 0;
    return data;
}
void Erase(char* value, size_t count) {
    volatile char* bytes = value;
    while (count--)
        *bytes++ = 0;
}
}  // namespace

YoumiDisplay::~YoumiDisplay() {
    DisplayLockGuard lock(this);
    if (animation_)
        lv_timer_delete(animation_);
    if (scene_)
        lv_obj_delete(scene_);
}

void YoumiDisplay::SetupUI() {
    if (setup_ui_called_)
        return;
    DisplayLockGuard lock(this);
    if (!lock)
        return;
    Display::SetupUI();
    auto screen = lv_display_get_screen_active(display_);
    lv_obj_set_style_bg_color(screen, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);
    scene_ = lv_obj_create(screen);
    lv_obj_remove_style_all(scene_);
    lv_obj_remove_flag(scene_, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_size(scene_, 240, 320);
    lv_obj_add_event_cb(
        scene_,
        [](lv_event_t* e) {
            auto self = static_cast<YoumiDisplay*>(lv_event_get_user_data(e));
            self->DrawFrame(lv_event_get_layer(e));
        },
        LV_EVENT_DRAW_MAIN, this);
    lv_display_add_event_cb(
        display_,
        [](lv_event_t* e) {
            auto self = static_cast<YoumiDisplay*>(lv_event_get_user_data(e));
            if (lv_event_get_code(e) == LV_EVENT_REFR_START)
                self->refresh_start_us_ = esp_timer_get_time();
            else if (self->refresh_start_us_)
                self->max_refresh_us_ =
                    std::max(self->max_refresh_us_,
                             uint32_t(esp_timer_get_time() - self->refresh_start_us_));
        },
        LV_EVENT_REFR_START, this);
    lv_display_add_event_cb(
        display_,
        [](lv_event_t* e) {
            auto self = static_cast<YoumiDisplay*>(lv_event_get_user_data(e));
            if (self->refresh_start_us_)
                self->max_refresh_us_ =
                    std::max(self->max_refresh_us_,
                             uint32_t(esp_timer_get_time() - self->refresh_start_us_));
        },
        LV_EVENT_REFR_READY, this);
    animation_ = lv_timer_create(
        [](lv_timer_t* t) { static_cast<YoumiDisplay*>(lv_timer_get_user_data(t))->Tick(); }, 200,
        this);
    lv_display_set_theme(display_, nullptr);
}

void YoumiDisplay::DrawFrame(lv_layer_t* layer) {
    auto start = esp_timer_get_time();
    const lv_font_t* font = &youmi_ui_font;
    if (current_theme_) {
        auto owner = current_theme_->GetTextFont();
        if (owner && owner->font())
            font = owner->font();
    }
    Painter(layer, font).Render(frame_);
    max_draw_us_ = std::max(max_draw_us_, uint32_t(esp_timer_get_time() - start));
}

void YoumiDisplay::Tick() {
    if (sleeping_)
        return;
    std::unique_lock<std::mutex> lock(mutex_, std::try_to_lock);
    if (!lock.owns_lock())
        return;
    const uint32_t now = lv_tick_get();
    pending_.tick = now;
    if (notice_until_ && int32_t(now - notice_until_) >= 0) {
        notice_until_ = 0;
        pending_.notice[0] = 0;
        dirty_ = true;
    }
    const bool animated = pending_.page == Page::Face || pending_.page == Page::Connecting ||
                          pending_.page == Page::Success;
    const bool active = pending_.page == Page::Connecting ||
                        (pending_.page == Page::Face && pending_.activity != Activity::Idle &&
                         pending_.activity != Activity::Offline);
    lv_timer_set_period(animation_, active ? 80 : 200);
    const bool page_changed = frame_.page != pending_.page;
    frame_ = pending_;
    if (dirty_ || page_changed)
        lv_obj_invalidate(scene_);
    else if (animated) {
        // Invalidate only the face/waveform or spinner, never a full-screen animation.
        lv_area_t face{20, 73, 219, 179};
        lv_area_t motion{48, 205, 192, 254};
        if (frame_.page == Page::Connecting)
            face = {42, 70, 198, 226};
        lv_obj_invalidate_area(scene_, &face);
        if (frame_.activity != Activity::Idle)
            lv_obj_invalidate_area(scene_, &motion);
    }
    dirty_ = false;
    lock.unlock();
    if (now - last_metrics_ >= 10000) {
        last_metrics_ = now;
        lv_mem_monitor_t monitor{};
        lv_mem_monitor(&monitor);
        ESP_LOGI(kTag,
                 "heap=%u largest=%u min=%u lv_used=%u lv_largest=%u draw_enqueue_max_us=%u "
                 "refresh_max_us=%u ui_stack_free=%u",
                 unsigned(heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)),
                 unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)),
                 unsigned(esp_get_minimum_free_heap_size()),
                 unsigned(monitor.total_size - monitor.free_size),
                 unsigned(monitor.free_biggest_size), unsigned(max_draw_us_),
                 unsigned(max_refresh_us_), unsigned(uxTaskGetStackHighWaterMark(nullptr)));
    }
}

void YoumiDisplay::SetEmotion(const char* emotion) {
    std::lock_guard<std::mutex> lock(mutex_);
    pending_.mood = mia_face::ParseMood(emotion);
    dirty_ = true;
}
void YoumiDisplay::SetStatus(const char* status) {
    if (!status)
        return;
    std::lock_guard<std::mutex> lock(mutex_);
    if (!std::strcmp(status, Lang::Strings::OTA_UPGRADE)) {
        pending_.page = Page::Ota;
        pending_.progress = -1;
    } else if (!std::strcmp(status, Lang::Strings::WIFI_CONFIG_MODE)) {
        // Keep the existing hotspot/browser instructions readable on an unconfigured device.
        if (pending_.page == Page::Boot || pending_.page == Page::Face)
            pending_.page = Page::Info;
    } else if (!std::strcmp(status, Lang::Strings::ERROR)) {
        pending_.page = Page::Error;
        Copy(pending_.text, status);
    } else if (!std::strcmp(status, Lang::Strings::LISTENING) ||
               !std::strcmp(status, Lang::Strings::SPEAKING) ||
               !std::strcmp(status, Lang::Strings::STANDBY)) {
        pending_.activity = !std::strcmp(status, Lang::Strings::LISTENING)  ? Activity::Listening
                            : !std::strcmp(status, Lang::Strings::SPEAKING) ? Activity::Speaking
                                                                            : Activity::Idle;
        if (pending_.activity != Activity::Idle || pending_.page == Page::Boot ||
            pending_.page == Page::Error || pending_.page == Page::Info)
            pending_.page = Page::Face;
    } else if (pending_.page == Page::Boot) {
        Copy(pending_.text, status);
    }
    dirty_ = true;
}
void YoumiDisplay::SetChatMessage(const char* role, const char* content) {
    const auto text = mia_text::Simplify(content);
    std::lock_guard<std::mutex> lock(mutex_);
    ApplyMessage(pending_, role, text.c_str());
    dirty_ = true;
}
void YoumiDisplay::ClearChatMessages() {
    std::lock_guard<std::mutex> lock(mutex_);
    pending_.text[0] = 0;
    dirty_ = true;
}
void YoumiDisplay::ShowNotification(const char* text, int duration_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    Copy(pending_.notice, text);
    notice_until_ = lv_tick_get() + std::max(1, duration_ms);
    dirty_ = true;
}
void YoumiDisplay::SetTheme(Theme* theme) {
    DisplayLockGuard display_lock(this);
    if (!display_lock)
        return;
    std::lock_guard<std::mutex> lock(mutex_);
    current_theme_ = theme;
    dirty_ = true;
}
void YoumiDisplay::SetHideSubtitle(bool hide) { hide_subtitle_ = hide; }
void YoumiDisplay::SetPreviewImage(std::unique_ptr<LvglImage> image) {
    // This board has no camera; accepting a frame must not allocate a full-screen buffer.
}
void YoumiDisplay::SetPowerSaveMode(bool on) { sleeping_ = on; }
void YoumiDisplay::UpdateStatusBar(bool) {
    auto& board = Board::GetInstance();
    int battery = -1;
    bool charging = false, discharging = false;
    board.GetBatteryLevel(battery, charging, discharging);
    time_t now = std::time(nullptr);
    struct tm local{};
    localtime_r(&now, &local);
    auto& app = Application::GetInstance();
    const bool active = app.GetDeviceState() == kDeviceStateSpeaking ||
                                app.GetDeviceState() == kDeviceStateNotifying
                            ? !app.GetAudioService().IsPlaybackIdle()
                            : app.IsVoiceDetected();
    std::unique_lock<std::mutex> lock(mutex_);
    char clock[6] = "--:--";
    if (local.tm_year >= 125)
        std::strftime(clock, sizeof(clock), "%H:%M", &local);
    if (std::strcmp(clock, pending_.clock) || battery != pending_.battery ||
        charging != pending_.charging)
        dirty_ = true;
    Copy(pending_.clock, clock);
    pending_.battery = battery;
    pending_.charging = charging;
    pending_.audio_active = active;
    auto codec = board.GetAudioCodec();
    const bool muted = codec && codec->output_volume() == 0;
    if (pending_.muted != muted)
        dirty_ = true;
    pending_.muted = muted;
    const bool low = battery == 0 && discharging;
    const bool announce =
        low && !low_battery_warned_ && app.GetDeviceState() != kDeviceStateUpgrading;
    low_battery_warned_ = low;
    if (announce) {
        Copy(pending_.notice, "电量低，请充电");
        notice_until_ = lv_tick_get() + 8000;
        dirty_ = true;
    }
    lock.unlock();
    if (announce)
        app.Schedule([&app]() { app.PlaySound(Lang::Sounds::OGG_LOW_BATTERY); });
}
void YoumiDisplay::NetworkChanged(bool connected, const char* ssid, bool config_mode) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (ApplyConnection(pending_, connected, ssid, config_mode))
        restore_station_ = false;
    dirty_ = true;
}
void YoumiDisplay::Fail(const char* message) {
    std::lock_guard<std::mutex> lock(mutex_);
    Copy(pending_.text, message);
    pending_.page = Page::Error;
    pending_.busy = false;
    Erase(pending_.password, sizeof(pending_.password));
    dirty_ = true;
}
void YoumiDisplay::OpenWifi() {
    const bool was_connected = WifiManager::GetInstance().IsConnected();
    {
        std::lock_guard<std::mutex> lock(mutex_);
        restore_station_ = restore_station_ || was_connected;
        pending_.page = Page::Wifi;
        pending_.selected = 0;
        pending_.network_count = 0;
        Copy(pending_.notice, "正在扫描...");
        notice_until_ = lv_tick_get() + 4000;
        dirty_ = true;
    }
    if (!WifiManager::GetInstance().IsConfigMode() && provision_)
        provision_();
    StartWork(Work::Scan);
}
bool YoumiDisplay::HandleKey(Key key) {
    auto state = Application::GetInstance().GetDeviceState();
    if (state != kDeviceStateIdle && state != kDeviceStateWifiConfiguring &&
        state != kDeviceStateActivating && state != kDeviceStateUpgrading)
        return false;
    std::unique_lock<std::mutex> lock(mutex_);
    auto& m = pending_;
    dirty_ = true;
    if (m.page == Page::Face || m.page == Page::Boot) {
        if (key != Key::Back)
            return false;
        m.page = Page::Settings;
        m.selected = 0;
        return true;
    }
    if (m.busy || worker_busy_ || state == kDeviceStateUpgrading)
        return true;
    if (key == Key::Back) {
        Erase(m.password, sizeof(m.password));
        if (m.page == Page::Password) {
            m.page = Page::Wifi;
            m.selected = 0;
        } else if (m.page == Page::Settings || m.page == Page::Success) {
            m.page = Page::Face;
            if (restore_station_) {
                restore_station_ = false;
                lock.unlock();
                StartWork(Work::Restore);
            }
        } else {
            m.page = Page::Settings;
            m.selected = 0;
        }
        return true;
    }
    if (m.page == Page::DisplaySettings) {
        if (key == Key::Up || key == Key::Down) {
            m.brightness = std::clamp(m.brightness + (key == Key::Up ? 10 : -10), 10, 100);
            const int brightness = m.brightness;
            lock.unlock();
            if (auto backlight = Board::GetInstance().GetBacklight())
                backlight->SetBrightness(brightness, true);
        } else if (key == Key::Ok)
            m.page = Page::Emotions;
        return true;
    }
    const int count = m.page == Page::Settings   ? 6
                      : m.page == Page::Wifi     ? m.network_count + 1
                      : m.page == Page::Password ? 12
                                                 : 1;
    if (key == Key::Up || key == Key::Down) {
        m.selected = (m.selected + (key == Key::Up ? count - 1 : 1)) % count;
        return true;
    }
    if (m.page == Page::Settings) {
        const int selected = m.selected;
        if (selected == 0) {
            lock.unlock();
            OpenWifi();
        } else if (selected == 4) {
            m.page = Page::Ota;
            m.progress = -1;
            lock.unlock();
            StartWork(Work::Update);
        } else if (selected == 5) {
            m.page = Page::Face;
            if (restore_station_) {
                restore_station_ = false;
                lock.unlock();
                StartWork(Work::Restore);
            }
        } else if (selected == 2) {
            m.page = Page::DisplaySettings;
            if (auto backlight = Board::GetInstance().GetBacklight())
                m.brightness = backlight->brightness();
        } else {
            m.page = Page::Info;
            if (selected == 1)
                std::snprintf(m.text, sizeof(m.text),
                              "ESP32-C3\n240 × 320 RGB565\n8MB Flash · 无 PSRAM\n固件 %s",
                              esp_app_get_description()->version);
            else
                Copy(m.text, "YOUMI\n让 AI 陪伴更温暖\n长按确认打开菜单\n上 / 下调节音量");
        }
    } else if (m.page == Page::Wifi) {
        m.editing_ssid = m.selected == m.network_count;
        m.allow_open = m.editing_ssid;
        if (!m.editing_ssid) {
            auto& ap = m.networks[m.selected];
            // This build disables WPA3 SAE; enterprise credentials require a different UX.
            if (ap.auth != 0 && ap.auth != 2 && ap.auth != 3 && ap.auth != 4) {
                Copy(m.text, "此网络认证方式不受支持");
                m.page = Page::Error;
                return true;
            }
            Copy(m.ssid, ap.ssid);
            if (ap.auth == 0) {
                m.password[0] = 0;
                m.page = Page::Connecting;
                lock.unlock();
                StartWork(Work::Connect);
                return true;
            }
        } else
            m.ssid[0] = 0;
        m.page = Page::Password;
        m.password[0] = 0;
        m.selected = 0;
        m.bank = 0;
    } else if (m.page == Page::Password) {
        char* field = m.editing_ssid ? m.ssid : m.password;
        const size_t max = m.editing_ssid ? 32 : 64, length = std::strlen(field);
        if (m.selected < 9) {
            char candidate = Candidate(m.bank, m.selected);
            if (candidate && length < max) {
                field[length] = candidate;
                field[length + 1] = 0;
            }
        } else if (m.selected == 9) {
            if (length)
                field[length - 1] = 0;
        } else if (m.selected == 10)
            m.bank = (m.bank + 1) % 11;
        else if (m.editing_ssid && length) {
            m.editing_ssid = false;
            m.selected = 0;
        } else if (!m.editing_ssid &&
                   (ValidPassword(m.password) || (m.allow_open && !m.password[0]))) {
            m.page = Page::Connecting;
            lock.unlock();
            StartWork(Work::Connect);
        } else {
            Copy(m.notice, "需 8–63 字符或 64 位十六进制");
            notice_until_ = lv_tick_get() + 4000;
        }
    } else {
        m.page = Page::Settings;
        m.selected = 0;
    }
    return true;
}

void YoumiDisplay::StartWork(Work work) {
    if (worker_busy_.exchange(true))
        return;
    struct Job {
        YoumiDisplay* display;
        Work work;
    };
    auto* job = new (std::nothrow) Job{this, work};
    if (!job ||
        xTaskCreate(
            [](void* arg) {
                auto* job = static_cast<Job*>(arg);
                auto self = job->display;
                auto work = job->work;
                delete job;
                self->RunWork(work);
                self->worker_busy_ = false;
                vTaskDelete(nullptr);
            },
            "youmi_ui_work", work == Work::Update ? 12288 : 6144, job, 1, nullptr) != pdPASS) {
        delete job;
        worker_busy_ = false;
        Fail("内存不足，请重试");
    }
}
void YoumiDisplay::RunWork(Work work) {
    if (work == Work::Restore) {
        auto& wifi = WifiManager::GetInstance();
        if (wifi.IsConfigMode())
            wifi.StopConfigAp();
        return;
    }
    if (work == Work::Update) {
        Ota ota;
        auto result = ota.CheckVersion();
        if (!result) {
            Fail("检查更新失败，请重试");
            return;
        }
        if (!ota.HasNewVersion()) {
            std::lock_guard<std::mutex> lock(mutex_);
            Copy(pending_.text, "当前已是最新版本");
            pending_.page = Page::Info;
            dirty_ = true;
        } else if (!Application::GetInstance().UpgradeFirmware(ota.GetFirmwareUrl(),
                                                               ota.GetFirmwareVersion()))
            Fail("更新未完成，已保留原固件\n请检查网络和电量后重试");
        return;
    }
    auto& wifi = WifiManager::GetInstance();
    int attempts = 0;
    while (!wifi.IsConfigMode() && attempts++ < 30)
        vTaskDelay(pdMS_TO_TICKS(100));
    if (!wifi.IsConfigMode()) {
        Fail("配网服务尚未就绪，请重试");
        return;
    }
    if (work == Work::Scan) {
        // The existing AP manager scans asynchronously. Empty results are legitimate.
        vTaskDelay(pdMS_TO_TICKS(1800));
        auto data = PortalRequest("/scan");
        auto json = data ? cJSON_Parse(data.get()) : nullptr;
        auto aps = json ? cJSON_GetObjectItemCaseSensitive(json, "aps") : nullptr;
        if (!cJSON_IsArray(aps)) {
            cJSON_Delete(json);
            Fail("读取网络列表失败\n可使用现有热点配网页面");
            return;
        }
        std::lock_guard<std::mutex> lock(mutex_);
        pending_.network_count = 0;
        cJSON* item;
        cJSON_ArrayForEach (item, aps) {
            auto ssid = cJSON_GetObjectItemCaseSensitive(item, "ssid");
            auto auth = cJSON_GetObjectItemCaseSensitive(item, "authmode");
            auto rssi = cJSON_GetObjectItemCaseSensitive(item, "rssi");
            if (!cJSON_IsString(ssid) || !ssid->valuestring[0] ||
                std::strlen(ssid->valuestring) > 32 || !cJSON_IsNumber(auth) ||
                !cJSON_IsNumber(rssi))
                continue;
            bool duplicate = false;
            for (int i = 0; i < pending_.network_count; ++i)
                duplicate |= !std::strcmp(pending_.networks[i].ssid, ssid->valuestring);
            if (duplicate || pending_.network_count == int(pending_.networks.size()))
                continue;
            auto& ap = pending_.networks[pending_.network_count++];
            Copy(ap.ssid, ssid->valuestring);
            ap.auth = auth->valueint;
            ap.rssi = rssi->valueint;
        }
        std::sort(pending_.networks.begin(), pending_.networks.begin() + pending_.network_count,
                  [](const Network& a, const Network& b) { return a.rssi > b.rssi; });
        pending_.selected = 0;
        pending_.notice[0] = 0;
        dirty_ = true;
        cJSON_Delete(json);
    } else {
        char ssid[33], password[65];
        {
            std::lock_guard<std::mutex> lock(mutex_);
            Copy(ssid, pending_.ssid);
            Copy(password, pending_.password);
            pending_.busy = true;
        }
        auto request = cJSON_CreateObject();
        cJSON_AddStringToObject(request, "ssid", ssid);
        cJSON_AddStringToObject(request, "password", password);
        char* body = cJSON_PrintUnformatted(request);
        cJSON_Delete(request);
        Erase(password, sizeof(password));
        auto data = body ? PortalRequest("/submit", body) : nullptr;
        if (body) {
            Erase(body, std::strlen(body));
            cJSON_free(body);
        }
        auto response = data ? cJSON_Parse(data.get()) : nullptr;
        const bool accepted =
            response && cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(response, "success"));
        cJSON_Delete(response);
        if (!accepted) {
            Fail("连接失败，请检查密码后重试");
            return;
        }
        // StopConfigAp emits ConfigModeExit. WifiBoard owns restarting the station,
        // its timeout and subsequent network events. The HTTP test is not success.
        wifi.StopConfigAp();
        for (int i = 0; i < 600; ++i) {
            if (wifi.IsConnected() && wifi.GetSsid() == ssid)
                return;
            vTaskDelay(pdMS_TO_TICKS(100));
        }
        Fail("连接超时，请重试");
    }
}
#endif
