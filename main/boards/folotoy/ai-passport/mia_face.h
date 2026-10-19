#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>

namespace mia_face {
enum class Mood { Neutral, Happy, Sad, Angry, Surprised, Sleepy, Confused, Loving };
enum class Activity { Idle, Listening, Speaking, Connecting, Thinking };
struct Frame {
    int gaze_x, gaze_y, eye_width, eye_height, mouth_width, mouth_height;
};
inline Mood ParseMood(const char* name) {
    if (!name)
        return Mood::Neutral;
    if (!strcmp(name, "loving"))
        return Mood::Loving;
    if (!strcmp(name, "confused") || !strcmp(name, "skeptical"))
        return Mood::Confused;
    if (!strcmp(name, "happy") || !strcmp(name, "laughing") || !strcmp(name, "funny") ||
        !strcmp(name, "confident"))
        return Mood::Happy;
    if (!strcmp(name, "sad") || !strcmp(name, "crying"))
        return Mood::Sad;
    if (!strcmp(name, "angry"))
        return Mood::Angry;
    if (!strcmp(name, "surprised") || !strcmp(name, "shocked"))
        return Mood::Surprised;
    if (!strcmp(name, "sleepy"))
        return Mood::Sleepy;
    return Mood::Neutral;
}
inline Frame Sample(Mood mood, Activity activity, uint32_t elapsed_ms) {
    Frame f{0, 0, 58, 50, 16, 3};
    const int gaze = (elapsed_ms / 300) % 24;
    f.gaze_x = (gaze < 12 ? gaze : 24 - gaze) / 3 - 2;
    if (mood == Mood::Happy || mood == Mood::Loving)
        f.eye_height = 8;
    if (mood == Mood::Sad) {
        f.eye_height = 32;
        f.mouth_width = 10;
    }
    if (mood == Mood::Angry)
        f.eye_height = 30;
    if (mood == Mood::Surprised) {
        f.eye_height = 58;
        f.mouth_width = 5;
        f.mouth_height = 5;
    }
    if (mood == Mood::Confused)
        f.eye_height = 40;
    if (mood == Mood::Sleepy)
        f.eye_height = 6;
    if (activity == Activity::Listening) {
        f.gaze_x = 0;
        f.mouth_width = f.mouth_height = 3;
    } else if (activity == Activity::Thinking) {
        f.mouth_width = 10;
        f.mouth_height = 2;
    } else if (activity == Activity::Speaking) {
        const int mouth = (elapsed_ms / 160) % 3;
        f.mouth_width = mouth == 0 ? 10 : mouth == 1 ? 8 : 14;
        f.mouth_height = mouth == 0 ? 2 : mouth == 1 ? 6 : 3;
    }
    // No blink at boot. Symmetric close/hold/open late in each four second cycle.
    const int blink = elapsed_ms % 4000;
    if (blink >= 3700) {
        const int amount = blink < 3800 ? 3800 - blink : blink < 3900 ? 0 : blink - 3900;
        f.eye_height = std::max(4, f.eye_height * amount / 100);
    }
    return f;
}
}  // namespace mia_face
