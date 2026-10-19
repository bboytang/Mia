#pragma once

#include <atomic>
#include <functional>
#include <mutex>
#include "display/lcd_display.h"
#include "youmi_ui_model.h"

class YoumiDisplay : public SpiLcdDisplay {
public:
    using SpiLcdDisplay::SpiLcdDisplay;
    ~YoumiDisplay() override;
    void SetupUI() override;
    void SetEmotion(const char* emotion) override;
    void SetStatus(const char* status) override;
    void SetChatMessage(const char* role, const char* content) override;
    void ClearChatMessages() override;
    void ShowNotification(const char* text, int duration_ms = 3000) override;
    void ShowNotification(const std::string& text, int duration_ms = 3000) override {
        ShowNotification(text.c_str(), duration_ms);
    }
    void UpdateStatusBar(bool update_all = false) override;
    void SetPowerSaveMode(bool on) override;
    void SetTheme(Theme* theme) override;
    void SetHideSubtitle(bool hide) override;
    void SetPreviewImage(std::unique_ptr<LvglImage> image) override;
    bool HandleKey(youmi_ui::Key key);
    void NetworkChanged(bool connected, const char* ssid, bool config_mode);
    void SetProvisioningAction(std::function<void()> action) { provision_ = std::move(action); }

private:
    enum class Work { Scan, Connect, Update, Restore };
    void Tick();
    void StartWork(Work work);
    void RunWork(Work work);
    void Fail(const char* message);
    void OpenWifi();
    void DrawFrame(lv_layer_t* layer);
    std::mutex mutex_;
    youmi_ui::Model pending_, frame_;
    lv_timer_t* animation_ = nullptr;
    lv_obj_t* scene_ = nullptr;
    std::atomic<bool> sleeping_{false};
    std::atomic<bool> worker_busy_{false};
    std::function<void()> provision_;
    uint32_t notice_until_ = 0;
    uint32_t last_metrics_ = 0;
    uint32_t max_draw_us_ = 0;
    uint32_t max_refresh_us_ = 0;
    int64_t refresh_start_us_ = 0;
    bool dirty_ = true;
    bool restore_station_ = false;
    bool low_battery_warned_ = false;
};
