#pragma once

#include <lvgl.h>
#include <cmath>
#include "youmi_ui_model.h"

extern const lv_font_t youmi_ui_font;

namespace youmi_ui {
// One custom LVGL object, fixed draw descriptors, no canvas or image decode buffers.
class Painter {
public:
    explicit Painter(lv_layer_t* layer, const lv_font_t* subtitle = &youmi_ui_font)
        : layer_(layer), subtitle_(subtitle) {}
    void Box(int x, int y, int w, int h, uint32_t color, int radius = 0, uint32_t border = 0,
             int border_width = 0, uint32_t bottom = 0) {
        lv_draw_rect_dsc_t d;
        lv_draw_rect_dsc_init(&d);
        d.bg_color = lv_color_hex(color);
        d.radius = radius;
        d.border_color = lv_color_hex(border);
        d.border_width = border_width;
        if (bottom) {
            d.bg_grad.dir = LV_GRAD_DIR_VER;
            d.bg_grad.stops[0].color = lv_color_hex(color);
            d.bg_grad.stops[1].color = lv_color_hex(bottom);
            d.bg_grad.stops[0].opa = d.bg_grad.stops[1].opa = LV_OPA_COVER;
        }
        lv_area_t a{x, y, x + w - 1, y + h - 1};
        lv_draw_rect(layer_, &d, &a);
    }
    void Line(int x, int y, int x2, int y2, uint32_t color, int width = 1) {
        lv_draw_line_dsc_t d;
        lv_draw_line_dsc_init(&d);
        d.p1 = {lv_value_precise_t(x), lv_value_precise_t(y)};
        d.p2 = {lv_value_precise_t(x2), lv_value_precise_t(y2)};
        d.color = lv_color_hex(color);
        d.width = width;
        d.round_start = d.round_end = 1;
        lv_draw_line(layer_, &d);
    }
    void Arc(int x, int y, int r, int start, int end, uint32_t color, int width = 1) {
        lv_draw_arc_dsc_t d;
        lv_draw_arc_dsc_init(&d);
        d.center = {x, y};
        d.radius = r;
        d.start_angle = start;
        d.end_angle = end;
        d.color = lv_color_hex(color);
        d.width = width;
        d.rounded = 1;
        lv_draw_arc(layer_, &d);
    }
    void Curve(int x, int y, int w, int rise, uint32_t color, int width = 1) {
        int px = x, py = y;
        const int count = w > 100 ? 48 : 16;
        for (int i = 1; i <= count; ++i) {
            int nx = x + w * i / count;
            int ny = y - 4 * rise * i * (count - i) / (count * count);
            Line(px, py, nx, ny, color, width);
            px = nx;
            py = ny;
        }
    }
    void Text(int x, int y, int w, const char* text, uint32_t color = 0xE8EDFF, bool center = true,
              bool subtitle = false, int height = 20) {
        lv_draw_label_dsc_t d;
        lv_draw_label_dsc_init(&d);
        d.text = text;
        d.font = subtitle ? subtitle_ : &youmi_ui_font;
        d.color = lv_color_hex(color);
        d.align = center ? LV_TEXT_ALIGN_CENTER : LV_TEXT_ALIGN_LEFT;
        lv_area_t a{x, y, x + w - 1, y + height - 1};
        lv_draw_label(layer_, &d, &a);
    }
    void Wifi(int x, int y, uint32_t color = 0xA3E7FF) {
        Arc(x, y + 15, 14, 225, 315, color, 2);
        Arc(x, y + 15, 9, 225, 315, color, 2);
        Box(x - 2, y + 12, 4, 4, color, 2);
    }
    void Header(const Model& m) {
        Text(16, 10, 62, m.clock, 0xE8EDFF, false);
        if (m.muted)
            Text(150, 10, 20, "M", 0x88A8CB);
        Wifi(185, 7, m.connected ? 0xE8EDFF : 0x455269);
        Box(211, 13, 23, 11, 0, 2, 0xCED6ED, 1);
        Box(234, 16, 2, 5, 0xCED6ED, 1);
        if (m.battery >= 0)
            Box(214, 16, std::max(1, 17 * m.battery / 100), 5, m.charging ? 0x71D9FF : 0xD9DFF8, 1);
    }
    void Title(const char* title) {
        Line(19, 51, 30, 51, 0xDDE6FF, 2);
        Line(19, 51, 24, 46, 0xDDE6FF, 2);
        Line(19, 51, 24, 56, 0xDDE6FF, 2);
        Text(40, 42, 170, title);
    }
    void Face(mia_face::Mood mood, Activity activity, uint32_t tick, int cx = 120, int cy = 138,
              int scale = 100) {
        const auto f =
            mia_face::Sample(mood,
                             activity == Activity::Listening  ? mia_face::Activity::Listening
                             : activity == Activity::Speaking ? mia_face::Activity::Speaking
                             : activity == Activity::Thinking ? mia_face::Activity::Thinking
                                                              : mia_face::Activity::Idle,
                             tick);
        auto sx = [&](int v) { return cx + v * scale / 100; };
        auto sy = [&](int v) { return cy + v * scale / 100; };
        auto box = [&](int x, int y, int w, int h, uint32_t c, uint32_t b = 0) {
            Box(sx(x), sy(y), std::max(1, w * scale / 100), std::max(1, h * scale / 100), c,
                std::max(1, std::min(w, h) * scale / 200), 0, 0, b);
        };
        const bool cheerful = mood == mia_face::Mood::Happy || mood == mia_face::Mood::Loving;
        const uint32_t accent = mood == mia_face::Mood::Angry ? 0xFF84AE : 0xB69BFF;
        for (int side : {-1, 1}) {
            const int x = side * 58;
            const int brow_rise = mood == mia_face::Mood::Sad     ? -4
                                  : mood == mia_face::Mood::Angry ? 1
                                                                  : 5;
            Curve(sx(x - 15), sy(-49 + (mood == mia_face::Mood::Surprised ? -7 : 0)),
                  30 * scale / 100, brow_rise * scale / 100, side < 0 ? 0x90DCFF : accent,
                  std::max(1, 2 * scale / 100));
            if (cheerful || f.eye_height <= 8 || (mood == mia_face::Mood::Confused && side > 0)) {
                Curve(sx(x - 27), sy(2), 54 * scale / 100, (cheerful ? 12 : -4) * scale / 100,
                      0x211A45, std::max(1, 7 * scale / 100));
                Curve(sx(x - 26), sy(0), 52 * scale / 100, (cheerful ? 12 : -4) * scale / 100,
                      0xECE7FF, std::max(1, 3 * scale / 100));
                continue;
            }
            const int h = f.eye_height;
            box(x - 33, -h / 2 - 2, 66, h + 6, 0x0C1224);
            box(x - 31, -h / 2, 62, h + 2, 0x3C3068, 0x19162C);
            box(x - 29, -h / 2 + 2, 58, h - 2, 0xD9D6FF, 0xB48BFF);
            box(x - 24, -h / 2 + 3, 48, h - 6, 0xF6F3FF);
            const int gaze = f.gaze_x;
            const int iris = x + gaze - side * 4;
            box(iris - 22, -h / 2 + 1, 44, h - 1, 0x102546, 0x6EDBFF);
            box(iris - 19, -h / 2 + 2, 38, h - 7, 0x0A1329, 0x2864AF);
            box(iris - 15, -h / 2 + 2, 30, h - 13, 0x020611);
            box(iris - 13, -h / 2 + 7, 8, 8, 0xF1F4FF);
            box(iris + 8, h / 2 - 12, 4, 4, 0x74CFFF);
            Curve(sx(x - 30), sy(-h / 2 - 5), 60 * scale / 100, 11 * scale / 100, accent,
                  std::max(1, 2 * scale / 100));
            if (mood == mia_face::Mood::Angry) {
                Line(sx(x - 25), sy(-32 - side * 8), sx(x + 25), sy(-32 + side * 8), 0xFF90BD,
                     std::max(1, 3 * scale / 100));
            }
        }
        if (mood == mia_face::Mood::Loving)
            Text(sx(52), sy(-53), 22, "♥", 0xFFA5CD);
        if (mood == mia_face::Mood::Confused)
            Text(sx(51), sy(-55), 22, "?", 0xD4A3EB);
        const int mw = f.mouth_width, mh = f.mouth_height;
        const uint32_t lip = activity == Activity::Speaking || cheerful ? 0xFFC3E8 : 0xD9D6FF;
        if (activity == Activity::Listening || f.mouth_height > 5) {
            box(-mw / 2, 31, mw, mh, lip);
            if (mw > 5 && mh > 4)
                box(-mw / 2 + 2, 33, mw - 4, mh - 4, 0x231328);
        } else if (activity == Activity::Thinking || (activity == Activity::Speaking && mh == 2)) {
            Line(sx(-5), sy(33), sx(5), sy(33), lip, std::max(1, 2 * scale / 100));
        } else {
            Curve(sx(-mw / 2), sy(32), mw * scale / 100,
                  (mood == mia_face::Mood::Sad ? 3 : -3) * scale / 100, lip,
                  std::max(1, 2 * scale / 100));
        }
    }
    void Render(const Model& m) {
        Box(0, 0, 240, 320, 0);
        if (m.page != Page::Boot)
            Header(m);
        switch (m.page) {
            case Page::Boot:
                Arc(120, 155, 89, 0, 360, 0x050E24, 8);
                Arc(120, 155, 86, 0, 360, 0x15244D, 6);
                Arc(120, 155, 84, 190, 350, 0x72DCFF, 2);
                Arc(120, 155, 84, 10, 185, 0xB39CFF, 2);
                // Vector-style wordmark, fixed strokes rather than a full-screen logo bitmap.
                Line(47, 141, 59, 153, 0xD8E3FF, 3);
                Line(71, 141, 59, 153, 0xD8E3FF, 3);
                Line(59, 153, 59, 168, 0xD8E3FF, 3);
                Arc(91, 155, 14, 0, 360, 0xD8D4FF, 3);
                Line(116, 141, 116, 158, 0xC2CFFF, 3);
                Arc(127, 158, 12, 0, 180, 0xC2CFFF, 3);
                Line(138, 141, 138, 158, 0xC2CFFF, 3);
                Line(150, 168, 150, 141, 0xD6D1FF, 3);
                Line(150, 141, 163, 155, 0xD6D1FF, 3);
                Line(163, 155, 176, 141, 0xD6D1FF, 3);
                Line(176, 141, 176, 168, 0xD6D1FF, 3);
                Line(190, 141, 190, 168, 0xACDEFF, 3);
                Line(120, 191, 120, 201, 0x8EDCFF, 2);
                Line(115, 196, 125, 196, 0x8EDCFF, 2);
                Text(20, 267, 200, "让 AI 陪伴更温暖", 0xAAB8DC);
                Box(75, 299, 90, 3, 0x14213A, 2);
                break;
            case Page::Face: {
                Face(m.activity == Activity::Speaking && m.mood == mia_face::Mood::Neutral
                         ? mia_face::Mood::Happy
                         : m.mood,
                     m.activity, m.tick);
                if (m.activity == Activity::Idle) {
                    Curve(5, 248, 230, 37, 0x071B35, 6);
                    Curve(5, 248, 230, 37, 0x287DC5, 1);
                    Text(18, 263, 204, "我在这里");
                    Text(104, 292, 32, "♥", 0x68BFFF);
                } else if (m.activity == Activity::Listening || m.activity == Activity::Speaking) {
                    const bool playing = m.audio_active;
                    for (int i = 0; i < 17; ++i) {
                        const int shape = 22 - std::abs(i - 8) * 2;
                        const int h =
                            playing ? 3 + shape * (3 + (m.tick / 80 + i * 7) % 8) / 10 : 2;
                        Box(53 + i * 8, 232 - h / 2, 3, h, i < 8 ? 0x7CCEFF : 0xA5A4FF, 2);
                    }
                    Text(12, 271, 216,
                         m.activity == Activity::Listening ? "我在听..." : "我在说话...");
                } else if (m.activity == Activity::Thinking) {
                    for (int i = 0; i < 3; ++i)
                        Box(87 + i * 28, 220, 9, 9,
                            i == int(m.tick / 400 % 3) ? 0xC0B2FF : 0x345878, 5);
                    Text(12, 265, 216, "让我想一想...");
                } else
                    Text(12, 265, 216, "网络已断开", 0xA4B9DB);
                if (m.text[0] && m.activity != Activity::Idle)
                    Text(12, 297, 216, m.text, 0x8EA9C8, true, true);
                break;
            }
            case Page::Emotions: {
                const mia_face::Mood moods[] = {mia_face::Mood::Happy,    mia_face::Mood::Surprised,
                                                mia_face::Mood::Confused, mia_face::Mood::Sad,
                                                mia_face::Mood::Angry,    mia_face::Mood::Loving};
                const char* labels[] = {"开心", "惊讶", "疑惑", "难过", "生气", "喜悦"};
                for (int i = 0; i < 6; ++i) {
                    int x = 12 + i % 2 * 112, y = 39 + i / 2 * 91;
                    Box(x, y, 104, 85, 0, 13, 0x142A37, 1);
                    Face(moods[i], Activity::Idle, 1200, x + 52, y + 36, 43);
                    Text(x, y + 62, 104, labels[i]);
                }
                break;
            }
            case Page::Settings: {
                const char* rows[] = {"Wi-Fi 设置", "设备信息", "显示设置",
                                      "关于 YOUMI", "系统升级", "返回"};
                for (int i = 0; i < 6; ++i) {
                    int y = 42 + i * 42;
                    Box(16, y, 208, 36, i == m.selected ? 0x174783 : 0x0D1520, 12,
                        i == m.selected ? 0x59BFFF : 0x182238, 1, i == m.selected ? 0x18234F : 0);
                    if (i == 0)
                        Wifi(34, y + 7);
                    else
                        Text(24, y + 8, 26,
                             i == 1   ? "i"
                             : i == 2 ? "O"
                             : i == 3 ? "♥"
                             : i == 4 ? "↑"
                                      : "‹",
                             0xA6D9FF);
                    Text(57, y + 8, 153, rows[i]);
                    Text(202, y + 8, 16, "›");
                }
                break;
            }
            case Page::Wifi: {
                Title("Wi-Fi 设置");
                const int first = m.selected / 5 * 5;
                for (int i = 0; i < 5; ++i) {
                    const int n = first + i, y = 78 + i * 39;
                    if (n > m.network_count)
                        break;
                    const bool chosen = n == m.selected;
                    Box(14, y, 212, 35, chosen ? 0x103F6B : 0x0B121B, 11,
                        chosen ? 0x20B8FF : 0x112132, 1, chosen ? 0x142447 : 0);
                    if (n == m.network_count)
                        Text(22, y + 8, 194, "其他网络 / 隐藏网络");
                    else {
                        Wifi(31, y + 6);
                        Text(51, y + 8, 145, m.networks[n].ssid, 0xE8EDFF, false, true);
                        if (m.networks[n].auth)
                            Text(201, y + 8, 20, "*");
                    }
                }
                Text(10, 287, 220, "长按确认返回 · 仅 2.4GHz", 0x8CA5C5);
                break;
            }
            case Page::Password: {
                Title(m.editing_ssid ? "输入网络名称" : "输入密码");
                Box(16, 76, 208, 44, 0x101B2A, 12);
                char mask[30];
                const size_t n = std::strlen(m.password);
                std::memset(mask, '*', std::min(n, sizeof(mask) - 1));
                mask[std::min(n, sizeof(mask) - 1)] = 0;
                Text(25, 88, 186, m.editing_ssid ? m.ssid : mask, 0xDBE3FF, false);
                for (int i = 0; i < 12; ++i) {
                    int x = 16 + i % 3 * 71, y = 130 + i / 3 * 38;
                    Box(x, y, 65, 32, i == m.selected ? 0x245DCA : 0x101B2A, 9,
                        i == m.selected ? 0x7ECFFF : 0, i == m.selected ? 1 : 0);
                    char label[8]{};
                    const char c = Candidate(m.bank, i);
                    if (i < 9) {
                        label[0] = c;
                        if (c == ' ')
                            Copy(label, "空格");
                    } else
                        Copy(label, i == 9 ? "删除" : i == 10 ? "aA#" : "确认");
                    Text(x, y + 6, 65, label);
                }
                char hint[64];
                std::snprintf(hint, sizeof(hint), "%d/11  %u 字符 · 长按返回", m.bank + 1,
                              unsigned(std::strlen(m.editing_ssid ? m.ssid : m.password)));
                Text(5, 287, 230, hint, 0x8CA5C5);
                break;
            }
            case Page::Connecting:
                Arc(120, 148, 76, 0, 360, 0x0F2444, 2);
                Arc(120, 148, 64, 0, 360, 0x152B55, 4);
                Arc(120, 148, 64, m.tick / 8 % 360, (m.tick / 8 + 245) % 360, 0x7DADFF, 3);
                Arc(120, 148, 42, 0, 360, 0x1D3B60, 1);
                Wifi(120, 130, 0x68C7FF);
                Text(12, 238, 216, "正在连接...", 0x75D7FF);
                Text(12, 268, 216, m.ssid, 0xC5D9EE, true, true);
                Text(12, 292, 216, "请稍候...", 0x91A5C2);
                break;
            case Page::Success:
                Face(mia_face::Mood::Happy, Activity::Idle, m.tick, 120, 126);
                Text(12, 206, 216, "连接成功!", 0x74E3FF);
                Text(12, 238, 216, m.ssid, 0xC0EAFF, true, true);
                Text(12, 262, 216, "现在可以开始聊天了", 0x98D9F2);
                Box(22, 288, 196, 29, 0x15315D, 14, 0x518FEE, 1);
                Text(22, 293, 196, "好的");
                break;
            case Page::Ota: {
                Title("系统升级");
                Face(mia_face::Mood::Sleepy, Activity::Thinking, m.tick, 120, 142, 80);
                Text(12, 210, 216,
                     m.progress < 0      ? "正在检查更新..."
                     : m.progress == 100 ? "正在校验固件..."
                                         : "正在升级...");
                Text(12, 242, 216, "请保持电量充足", 0xA5CFF2);
                Text(12, 264, 216, "升级过程中请勿断电", 0xA5CFF2);
                Box(20, 292, 162, 9, 0x071421, 5, 0x17324E, 1);
                if (m.progress >= 0) {
                    Box(20, 292, std::max(1, 162 * m.progress / 100), 9, 0x8DE5FF, 5, 0, 0,
                        0x7D9EFF);
                    char pct[8];
                    std::snprintf(pct, sizeof(pct), "%d%%", m.progress);
                    Text(186, 286, 50, pct);
                }
                break;
            }
            case Page::DisplaySettings: {
                Title("显示设置");
                char brightness[32];
                std::snprintf(brightness, sizeof(brightness), "亮度 %d%%", m.brightness);
                Text(20, 110, 200, brightness);
                Box(30, 151, 180, 8, 0x12213A, 4);
                Box(30, 151, std::max(1, 180 * m.brightness / 100), 8, 0x71CEFF, 4);
                Text(10, 211, 220, "上 / 下调整亮度", 0xA1C9E8);
                Text(10, 241, 220, "确认预览表情", 0xA1C9E8);
                Text(10, 285, 220, "长按确认返回", 0xA1C9E8);
                break;
            }
            case Page::Info:
            case Page::Error:
                Title(m.page == Page::Error ? "提示" : "YOUMI");
                Text(20, 101, 200, m.text, m.page == Page::Error ? 0xFFBDD4 : 0xA4D4F5, true, false,
                     160);
                Text(12, 286, 216, "确认返回", 0x809DC3);
                break;
        }
        if (m.notice[0]) {
            Box(10, 35, 220, 37, 0x152137, 10, 0x3C638B, 1);
            Text(16, 43, 208, m.notice, 0xD9EDFF, true, true);
        }
    }

private:
    lv_layer_t* layer_;
    const lv_font_t* subtitle_;
};
}  // namespace youmi_ui
