#pragma once
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <vector>

#define ESP_LOGI(...) ((void)0)
#define ESP_ERROR_CHECK(value) assert((value) == 0)
#define pdMS_TO_TICKS(value) (value)
inline void vTaskDelay(int) {}
constexpr int ESP_TIMER_TASK = 0;
struct Timer {
    void (*callback)(void*);
    void* arg;
    bool enabled = false;
};
using esp_timer_handle_t = Timer*;
struct esp_timer_create_args_t {
    void (*callback)(void*);
    void* arg;
    int dispatch_method;
    const char* name;
    bool skip_unhandled_events;
};
inline std::vector<Timer*> timers;
inline int esp_timer_create(const esp_timer_create_args_t* args, Timer** timer) {
    *timer = new Timer{args->callback, args->arg};
    timers.push_back(*timer);
    return 0;
}
inline int esp_timer_start_periodic(Timer* timer, uint64_t period) {
    assert(period == 1000000);
    timer->enabled = true;
    return 0;
}
inline int esp_timer_stop(Timer* timer) {
    timer->enabled = false;
    return 0;
}
inline int esp_timer_delete(Timer* timer) {
    timers.erase(std::remove(timers.begin(), timers.end(), timer), timers.end());
    delete timer;
    return 0;
}
inline void Tick(int seconds) {
    while (seconds-- > 0) {
        for (auto* timer : timers)
            if (timer->enabled)
                timer->callback(timer->arg);
    }
}
struct esp_pm_config_t {
    int max_freq_mhz;
    int min_freq_mhz;
    bool light_sleep_enable;
};
inline int pm_calls = 0;
inline int esp_pm_configure(const esp_pm_config_t*) {
    ++pm_calls;
    return 0;
}
struct Codec {
    void EnableInput(bool) {}
};
class Board {
public:
    static Board& GetInstance() {
        static Board board;
        return board;
    }
    Codec* GetAudioCodec() { return &codec; }

private:
    Codec codec;
};
struct Audio {
    bool IsWakeWordRunning() { return false; }
    void EnableWakeWordDetection(bool) {}
};
class Application {
public:
    static Application& GetInstance() {
        static Application app;
        return app;
    }
    bool idle = true;
    bool CanEnterSleepMode() { return idle; }
    Audio& GetAudioService() { return audio; }

private:
    Audio audio;
};
inline bool sleep_enabled = true;
struct Settings {
    Settings(const char*, bool) {}
    bool GetBool(const char*, bool) { return sleep_enabled; }
};
