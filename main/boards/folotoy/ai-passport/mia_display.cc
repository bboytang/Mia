#include "sdkconfig.h"

#if CONFIG_MIA_PASSPORT_DEVELOPMENT
#include "mia_display.h"

#include "assets/lang_config.h"

MiaDisplay::~MiaDisplay() {
    DisplayLockGuard lock(this);
    if (animation_)
        lv_timer_delete(animation_);
}

void MiaDisplay::SetupUI() {
    if (setup_ui_called_)
        return;
    SpiLcdDisplay::SetupUI();
    DisplayLockGuard lock(this);
    lv_obj_add_flag(emoji_label_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(emoji_image_, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_size(emoji_box_, 216, 178);
    lv_obj_align(emoji_box_, LV_ALIGN_CENTER, 0, -12);
    lv_obj_set_style_bg_color(emoji_box_, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(emoji_box_, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(emoji_box_, 32, 0);
    lv_obj_remove_flag(emoji_box_, LV_OBJ_FLAG_SCROLLABLE);
    for (auto& eye : eyes_) {
        eye = lv_obj_create(emoji_box_);
        lv_obj_remove_style_all(eye);
        lv_obj_set_style_bg_color(eye, lv_color_hex(0x8FE9FF), 0);
        lv_obj_set_style_bg_opa(eye, LV_OPA_COVER, 0);
        lv_obj_set_style_radius(eye, LV_RADIUS_CIRCLE, 0);
    }
    mouth_ = lv_obj_create(emoji_box_);
    lv_obj_remove_style_all(mouth_);
    lv_obj_set_style_bg_color(mouth_, lv_color_hex(0x8FE9FF), 0);
    lv_obj_set_style_bg_opa(mouth_, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(mouth_, LV_RADIUS_CIRCLE, 0);
    started_at_ = lv_tick_get();
    DrawFrame();
    animation_ = lv_timer_create(
        [](lv_timer_t* timer) {
            auto self = static_cast<MiaDisplay*>(lv_timer_get_user_data(timer));
            if (!lv_obj_has_flag(self->emoji_box_, LV_OBJ_FLAG_HIDDEN))
                self->DrawFrame();
        },
        50, this);
}

void MiaDisplay::DrawFrame() {
    const auto f = mia_face::Sample(mood_, activity_, lv_tick_get() - started_at_);
    for (int i = 0; i < 2; ++i) {
        lv_obj_set_size(eyes_[i], f.eye_width, f.eye_height);
        lv_obj_align(eyes_[i], LV_ALIGN_CENTER, (i == 0 ? -46 : 46) + f.gaze_x, -12 + f.gaze_y);
    }
    lv_obj_set_size(mouth_, f.mouth_width, f.mouth_height);
    lv_obj_align(mouth_, LV_ALIGN_CENTER, f.gaze_x / 2, 44);
}

void MiaDisplay::SetEmotion(const char* emotion) {
    DisplayLockGuard lock(this);
    mood_ = mia_face::ParseMood(emotion);
    if (mouth_)
        DrawFrame();
}

void MiaDisplay::SetStatus(const char* status) {
    SpiLcdDisplay::SetStatus(status);
    if (!status)
        return;
    DisplayLockGuard lock(this);
    // Use existing application notifications; no new core/board coupling.
    if (!strcmp(status, Lang::Strings::LISTENING))
        activity_ = mia_face::Activity::Listening;
    else if (!strcmp(status, Lang::Strings::SPEAKING))
        activity_ = mia_face::Activity::Speaking;
    else if (!strcmp(status, Lang::Strings::CONNECTING))
        activity_ = mia_face::Activity::Connecting;
    else
        activity_ = mia_face::Activity::Idle;
}

void MiaDisplay::SetPowerSaveMode(bool on) {
    DisplayLockGuard lock(this);
    if (!animation_)
        return;
    if (on)
        lv_timer_pause(animation_);
    else {
        started_at_ = lv_tick_get();
        lv_timer_resume(animation_);
        DrawFrame();
    }
}
#endif
