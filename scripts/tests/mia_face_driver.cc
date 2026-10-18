#include "mia_face.h"

#include <cassert>
#include <cstdint>

int main() {
    using namespace mia_face;
    assert(ParseMood(nullptr) == Mood::Neutral);
    assert(ParseMood("unrecognized-server-emotion") == Mood::Neutral);
    assert(ParseMood("laughing") == Mood::Happy);
    assert(ParseMood("crying") == Mood::Sad);
    assert(ParseMood("shocked") == Mood::Surprised);
    for (auto mood :
         {Mood::Neutral, Mood::Happy, Mood::Sad, Mood::Angry, Mood::Surprised, Mood::Sleepy}) {
        for (auto activity :
             {Activity::Idle, Activity::Listening, Activity::Speaking, Activity::Connecting}) {
            for (uint32_t ms = 0; ms < 12000; ms += 25) {
                auto f = Sample(mood, activity, ms);
                // Both eyes and the mouth must fit the actual 216x178 face region.
                for (int center : {-46, 46}) {
                    assert(108 + center + f.gaze_x - f.eye_width / 2 >= 0);
                    assert(108 + center + f.gaze_x + f.eye_width / 2 <= 216);
                }
                assert(f.eye_height >= 4 && f.eye_height <= 66);
                assert(89 - 12 + f.gaze_y - f.eye_height / 2 >= 0);
                assert(89 + 44 + f.mouth_height / 2 <= 178);
                assert(f.mouth_width > 0 && f.mouth_height > 0);
            }
        }
    }
    assert(Sample(Mood::Neutral, Activity::Idle, 100).eye_height == 4);
    assert(Sample(Mood::Neutral, Activity::Idle, 200).eye_height == 54);
    assert(Sample(Mood::Neutral, Activity::Idle, 4100).eye_height == 4);
    assert(Sample(Mood::Neutral, Activity::Speaking, 600).mouth_height >
           Sample(Mood::Neutral, Activity::Speaking, 0).mouth_height);
    assert(Sample(Mood::Neutral, Activity::Listening, 500).gaze_x == 0);
    assert(Sample(Mood::Neutral, Activity::Idle, UINT32_MAX).eye_height >= 4);
}
