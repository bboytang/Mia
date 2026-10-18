#pragma once

#include <algorithm>
#include <cstdint>
#include <cstring>

// Geometry only: no frame buffers, image assets or per-frame allocation.
namespace mia_face {
enum class Mood { Neutral, Happy, Sad, Angry, Surprised, Sleepy };
enum class Activity { Idle, Listening, Speaking, Connecting };
struct Frame {
    int gaze_x, gaze_y, eye_width, eye_height, mouth_width, mouth_height;
};
inline Mood ParseMood(const char* name) {
    if (!name)
        return Mood::Neutral;
    if (!strcmp(name, "happy") || !strcmp(name, "laughing") || !strcmp(name, "funny") ||
        !strcmp(name, "loving") || !strcmp(name, "confident"))
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
    const int beat = (elapsed_ms / 100) % 12;
    Frame f{0, 0, 40, 54, 20, 5};
    // A slow triangular gaze avoids abrupt jumps at the loop boundary.
    const int gaze = (elapsed_ms / 150) % 40;
    f.gaze_x = (gaze < 20 ? gaze : 40 - gaze) / 2 - 5;
    if (mood == Mood::Happy) {
        f.eye_height = 22;
        f.mouth_width = 32;
    }
    if (mood == Mood::Sad) {
        f.eye_height = 30;
        f.gaze_y = 8;
        f.mouth_width = 12;
    }
    if (mood == Mood::Angry) {
        f.eye_height = 18;
        f.eye_width = 46;
    }
    if (mood == Mood::Surprised) {
        f.eye_height = 66;
        f.mouth_width = 14;
        f.mouth_height = 20;
    }
    if (mood == Mood::Sleepy) {
        f.eye_height = 8;
        f.gaze_y = 8;
    }
    if (activity == Activity::Listening) {
        f.gaze_x = 0;
        f.eye_width += beat < 6 ? 2 : 0;
    }
    if (activity == Activity::Speaking) {
        f.mouth_height = 5 + (beat < 6 ? beat : 12 - beat) * 2;
    }
    if (activity == Activity::Connecting) {
        f.gaze_x = beat < 6 ? -7 : 7;
    }
    // Close and reopen both eyes over 200 ms, every four seconds.
    const int blink = elapsed_ms % 4000;
    if (blink < 200)
        f.eye_height = std::max(4, f.eye_height * (blink < 100 ? 100 - blink : blink - 100) / 100);
    return f;
}
}  // namespace mia_face
