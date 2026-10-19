#include <array>
#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include "youmi_ui_draw.h"

using namespace youmi_ui;
static Model frame;
static std::array<uint16_t, 240 * 320> pixels;  // Host screenshot storage only.
static std::array<uint16_t, 240 * 20> strip;
static void Flush(lv_display_t* display, const lv_area_t* a, uint8_t* data) {
    auto source = reinterpret_cast<uint16_t*>(data);
    for (int y = a->y1; y <= a->y2; ++y)
        for (int x = a->x1; x <= a->x2; ++x)
            pixels[y * 240 + x] = *source++;
    lv_display_flush_ready(display);
}
int main(int argc, char** argv) {
    if (argc != 2)
        return 2;
    std::filesystem::create_directories(argv[1]);
    lv_init();
    auto display = lv_display_create(240, 320);
    lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(display, strip.data(), nullptr, sizeof(strip),
                           LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(display, Flush);
    auto screen = lv_display_get_screen_active(display);
    lv_obj_set_style_bg_color(screen, lv_color_black(), 0);
    auto scene = lv_obj_create(screen);
    lv_obj_remove_style_all(scene);
    lv_obj_remove_flag(scene, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_size(scene, 240, 320);
    lv_obj_add_event_cb(
        scene, [](lv_event_t* e) { Painter(lv_event_get_layer(e)).Render(frame); },
        LV_EVENT_DRAW_MAIN, nullptr);
    frame.tick = 1200;
    frame.battery = 82;
    frame.connected = true;
    Copy(frame.clock, "12:30");     // Explicit fixtures, never firmware defaults.
    Copy(frame.ssid, "Home_2.4G");  // ESP32-C3 cannot connect to a 5GHz-only AP.
    const Page pages[] = {Page::Boot,     Page::Face,       Page::Face,     Page::Face,
                          Page::Face,     Page::Emotions,   Page::Settings, Page::Wifi,
                          Page::Password, Page::Connecting, Page::Success,  Page::Ota};
    std::ofstream stats(std::filesystem::path(argv[1]) / "host-metrics.json");
    stats << "{\"hardware_tested\":false,\"pool_bytes\":32768,\"dma_strip_bytes\":" << sizeof(strip)
          << ",\"model_bytes\":" << sizeof(Model) << ",\"screens\":[";
    for (int i = 0; i < 12; ++i) {
        frame.page = pages[i];
        frame.activity = i == 2   ? Activity::Listening
                         : i == 3 ? Activity::Thinking
                         : i == 4 ? Activity::Speaking
                                  : Activity::Idle;
        frame.audio_active = true;
        frame.progress = 68;
        if (i == 8) {
            Copy(frame.password, "fixture");
            frame.bank = 0;
            frame.selected = 11;
        } else
            frame.selected = 0;
        frame.network_count = 5;
        const char* names[] = {"Home_2.4G", "YOUMI_2.4G", "Cafe_WiFi", "TP-Link_3F", "Xiaomi_88"};
        for (int n = 0; n < 5; ++n) {
            Copy(frame.networks[n].ssid, names[n]);
            frame.networks[n].auth = 3;
        }
        lv_obj_invalidate(scene);
        auto start = std::chrono::steady_clock::now();
        lv_refr_now(display);
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(
                      std::chrono::steady_clock::now() - start)
                      .count();
        lv_mem_monitor_t m{};
        lv_mem_monitor(&m);
        char name[16];
        std::snprintf(name, sizeof(name), "%02d.ppm", i + 1);
        std::ofstream out(std::filesystem::path(argv[1]) / name, std::ios::binary);
        out << "P6\n240 320\n255\n";
        for (uint16_t p : pixels) {
            const char rgb[] = {char((p >> 11) * 255 / 31), char(((p >> 5) & 63) * 255 / 63),
                                char((p & 31) * 255 / 31)};
            out.write(rgb, 3);
        }
        if (i)
            stats << ',';
        stats << "{\"screen\":" << i + 1 << ",\"host_refresh_us\":" << us
              << ",\"lv_used_bytes\":" << m.total_size - m.free_size
              << ",\"lv_peak_bytes\":" << m.max_used
              << ",\"lv_largest_bytes\":" << m.free_biggest_size << '}';
    }
    stats << "]";
    int animation_frames = 0;
    // Exercise blink, gaze and all three speaking mouths with the exact firmware renderer.
    for (auto mood : {mia_face::Mood::Neutral, mia_face::Mood::Happy, mia_face::Mood::Sad,
                      mia_face::Mood::Angry, mia_face::Mood::Surprised, mia_face::Mood::Confused,
                      mia_face::Mood::Loving}) {
        frame.page = Page::Face;
        frame.mood = mood;
        for (auto activity :
             {Activity::Idle, Activity::Listening, Activity::Thinking, Activity::Speaking}) {
            frame.activity = activity;
            for (uint32_t tick = 0; tick < 4200; tick += 80) {
                frame.tick = tick;
                lv_area_t face{20, 73, 219, 179};
                lv_obj_invalidate_area(scene, &face);
                lv_refr_now(display);
                ++animation_frames;
            }
        }
    }
    for (auto page : {Page::Info, Page::Error, Page::DisplaySettings}) {
        frame.page = page;
        Copy(frame.text, "授权码 042617");
        lv_obj_invalidate(scene);
        lv_refr_now(display);
    }
    lv_mem_monitor_t end{};
    lv_mem_monitor(&end);
    stats << ",\"animation_frames\":" << animation_frames
          << ",\"animation_peak_bytes\":" << end.max_used << "}\n";
    std::cout << "12 RGB565 LVGL screenshots; 32KB pool animation stress passed. Host only.\n";
    lv_deinit();
}
