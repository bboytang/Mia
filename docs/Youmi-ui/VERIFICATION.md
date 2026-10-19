# Twelve-screen visual review

Every pair contains the original 240×320 reference on the left and a real LVGL
RGB565 render from the shared firmware drawing code on the right. No reference
pixels are embedded in firmware. These are host fixtures, not device captures.

[All twelve comparisons](verification/all-12-comparison.png).

| Screen | Implemented and reviewed | Remaining visual / business boundary |
| --- | --- | --- |
| [01 Boot](verification/01-comparison.png) | Vector wordmark, cyan/violet ring, tagline, black background | No starfield or raster glow. Boot is event driven; the bottom line is not fake loading progress. |
| [02 Idle](verification/02-comparison.png) | Large symmetric eyes, tiny curved mouth, horizon, state label and heart | Concentric eye primitives approximate the painted iris; font and light falloff differ. Blink and small gaze shifts are deterministic. |
| [03 Listening](verification/03-comparison.png) | Large eyes, 3×3 mouth dot, lightweight waveform and listening label | Waveform uses VAD/activity, not PCM amplitude. Real audio timing remains a hardware check. |
| [04 Thinking](verification/04-comparison.png) | Short 10px mouth line, three discrete dots and thinking label | Brows/eye shading differ; enters only on a real STT user message while awaiting TTS. |
| [05 Speaking](verification/05-comparison.png) | Soft closed-eye expression, waveform, only closed/small oval/small smile mouth states | No tongue or large open mouth. Backend emotion can override the default cheerful eyes. |
| [06 Emotions](verification/06-comparison.png) | Happy, surprised, confused, sad, angry and loving; compact two-column gallery | Painted facial contours/glow differ. Extra sleepy/neutral states support idle and OTA. |
| [07 Settings](verification/07-comparison.png) | Three-key selection, cyan/blue focus, Wi-Fi/info/display/about/back | Six rows add a real system-update entry. Display settings control the real backlight and offer the emotion gallery. |
| [08 Wi-Fi](verification/08-comparison.png) | Real bounded scan data, highlight, protected/open indication and hidden SSID entry | Displays at most 12 distinct APs; no canned list. RSSI sorting, 2.4GHz-only C3. Local portal exchange needs device validation. |
| [09 Credentials](verification/09-comparison.png) | Masked password, 3×4 controls, readable focused confirm key | Eleven banks cover all 95 printable ASCII characters. Layout deliberately changes to support full credentials, deletion and bank selection. |
| [10 Connecting](verification/10-comparison.png) | Indeterminate ring, target SSID, actual pending-connection text | No invented percentage. Failed credentials and timeout return an error; cancel can restore the previous station. |
| [11 Success](verification/11-comparison.png) | Small smile, cheerful eyes, cyan confirmation and OK control | Reached only on a real connected event for the requested SSID. Fixture name uses 2.4GHz rather than the concept's Home_5G. |
| [12 OTA](verification/12-comparison.png) | Sleepy eyes, tiny mouth, warning labels and byte-progress bar | Actual signed updater drives progress; 100% means validation pending. Host fixture is explicitly 68%, never a runtime default. |

This review does **not** certify 1:1 visual equivalence. The reference crops contain
uneven bezel positions and simulated glow. All twelve are adapted to the actual
usable 240×320 panel; see the pairs for exact geometry/color/text differences.
The resource and voice constraints take precedence over adding those effects.

Host screenshots use a 32KB LVGL pool and a 9,600-byte single line-strip buffer;
`verification/comparison.json` contains measured **host-only** timing, pool usage,
source hashes and 1,484 animation refreshes across seven moods and four activities.
It also records that no hardware was tested. The host frame storage is excluded
from firmware and is not part of the ESP32 rendering architecture.

Run the firmware CI for the exact final source commit. Its capacity reports and
build logs are the source for image size, assets capacity and static RAM. Runtime
free heap, maximum contiguous heap, task occupancy, refresh duration and voice
coexistence cannot be accepted until measured on the actual development board.

## Final build evidence (2026-10-19)

Tested code `f19a144ddb69286122305993755fbd8fc192abf1`:
[CI 39326192375](https://github.com/bboytang/Youmi/actions/runs/39326192375) is
successful: 127 host tests, all five firmware variants, native UI screenshots and
the existing Android inspection checks. Downloaded CI captures match all twelve
committed implementation PNGs pixel for pixel. This verifies reproducibility,
not pixel equivalence to the artwork.

| Production `mia-ai-passport` measurement | Result |
| --- | --- |
| Application image / A/B slot | 2,363,392 / 3,145,728 bytes (75.13%) |
| Free application slot capacity | 782,336 bytes |
| Flash increase over release 1.0.4 | 38,496 bytes |
| Resources / assets partition | 307,037 / 655,360 bytes |
| Static DRAM, including resident code | 109,756 bytes |
| Static RTC SLOW | 96 bytes |
| Actual device free heap / largest block / UI incremental heap | Not measured |
| Actual task CPU occupancy / FPS / refresh duration / voice coexistence | Not measured |

The production partition-table binary and generated asset bytes exactly match
release `e967eae`. Do not use the development variant's asset hash for this
comparison: its board name intentionally differs. No source file in the audio,
protocol, application, signed-update or partition implementation changed.

See [raw IDF size output](verification/firmware-size.txt),
[structured sizes](verification/firmware-size.json),
[production capacity](verification/production-capacity.json) and
[validation provenance](verification/build-results.json).
These final evidence files document the tested code commit; they make no new
firmware changes. No device was flashed and no OTA was published.
