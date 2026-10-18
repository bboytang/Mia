#pragma once

#include "display/lcd_display.h"
#include "mia_face.h"

class MiaDisplay : public SpiLcdDisplay {
public:
    using SpiLcdDisplay::SpiLcdDisplay;
    ~MiaDisplay() override;
    void SetupUI() override;
    void SetEmotion(const char* emotion) override;
    void SetStatus(const char* status) override;
    void SetChatMessage(const char* role, const char* content) override;
    void SetPowerSaveMode(bool on) override;

private:
    void DrawFrame();  // Caller holds the LVGL lock (timer callbacks already do).
    lv_timer_t* animation_ = nullptr;
    lv_obj_t* eyes_[2] = {};
    lv_obj_t* mouth_ = nullptr;
    mia_face::Mood mood_ = mia_face::Mood::Neutral;
    mia_face::Activity activity_ = mia_face::Activity::Idle;
    uint32_t started_at_ = 0;
};
