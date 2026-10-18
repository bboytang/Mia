#pragma once

#include <functional>

#include <esp_timer.h>
#include <esp_pm.h>

class PowerSaveTimer {
public:
    // Opt in to restoring brightness/waking and resetting the idle deadline
    // whenever application activity resumes, including after the dim stage.
    PowerSaveTimer(int cpu_max_freq, int seconds_to_sleep = 20, int seconds_to_shutdown = -1,
                   bool wake_on_activity = false);
    ~PowerSaveTimer();

    void SetEnabled(bool enabled);
    void OnEnterSleepMode(std::function<void()> callback);
    void OnExitSleepMode(std::function<void()> callback);
    void OnShutdownRequest(std::function<void()> callback);
    void WakeUp();

private:
    void PowerSaveCheck();

    esp_timer_handle_t power_save_timer_ = nullptr;
    bool enabled_ = false;
    bool in_sleep_mode_ = false;
    bool is_wake_word_running_ = false;
    bool wake_on_activity_ = false;
    int ticks_ = 0;
    int cpu_max_freq_;
    int seconds_to_sleep_;
    int seconds_to_shutdown_;

    std::function<void()> on_enter_sleep_mode_;
    std::function<void()> on_exit_sleep_mode_;
    std::function<void()> on_shutdown_request_;
};
