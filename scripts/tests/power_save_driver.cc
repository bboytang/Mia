#include <iostream>
#include "power_save_timer.h"
#include "runtime.h"

int main() {
    auto& app = Application::GetInstance();
    {
        int dim = 0, wake = 0, soft = 0;
        PowerSaveTimer timer(-1, 60, 120, true);
        timer.OnEnterSleepMode([&]() { ++dim; });
        timer.OnExitSleepMode([&]() { ++wake; });
        timer.OnShutdownRequest([&]() { ++soft; });
        timer.SetEnabled(true);
        Tick(59);
        assert(dim == 0);
        Tick(1);
        assert(dim == 1);
        Tick(59);
        assert(soft == 0);
        Tick(1);
        assert(soft == 1);

        // Conversation resumes after the screen-off deadline: wake it and keep
        // every timer callback suspended through a conversation longer than 30m.
        app.idle = false;
        Tick(1);
        assert(wake == 1);
        Tick(2000);
        assert(dim == 1 && soft == 1 && wake == 1);
        app.idle = true;
        Tick(59);
        assert(dim == 1);
        Tick(1);
        assert(dim == 2);
        Tick(59);
        assert(soft == 1);
        Tick(1);
        assert(soft == 2);

        timer.WakeUp();
        assert(wake == 2);
        Tick(60);
        assert(dim == 3);
        // Also cover activity beginning between dim and screen off.
        app.idle = false;
        Tick(1);
        assert(wake == 3);
        Tick(1800);
        assert(dim == 3 && soft == 2);
        app.idle = true;
        Tick(60);
        assert(dim == 4);
        timer.SetEnabled(false);
        assert(wake == 4);
        Tick(1800);
        assert(dim == 4 && soft == 2);
    }
    {
        // Existing callers retain their original behavior unless opted in.
        int dim = 0, wake = 0, shutdown = 0;
        PowerSaveTimer timer(-1, 60, 360);
        timer.OnEnterSleepMode([&]() { ++dim; });
        timer.OnExitSleepMode([&]() { ++wake; });
        timer.OnShutdownRequest([&]() { ++shutdown; });
        timer.SetEnabled(true);
        Tick(60);
        assert(dim == 1);
        app.idle = false;
        Tick(300);
        assert(wake == 0 && shutdown == 1);
        app.idle = true;
    }
    {
        int dim = 0;
        sleep_enabled = false;
        PowerSaveTimer timer(-1, 60, 120, true);
        timer.OnEnterSleepMode([&]() { ++dim; });
        timer.SetEnabled(true);
        Tick(1800);
        assert(dim == 0);
        sleep_enabled = true;
    }
    assert(timers.empty());
    assert(pm_calls == 0);  // Board owns CPU clocks; no generic light sleep.
    std::cout << "Actual power-save timer: deadlines, voice wake/reset, long activity, legacy "
                 "behavior and disabled settings passed\n";
}
