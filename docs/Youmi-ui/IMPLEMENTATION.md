# YOUMI AI Passport UI implementation and verification

## Ownership and constraints

Worktree `/root/projects/Youmi-ui`, branch `feature/youmi-passport-ui`, based on
released firmware `e967eae73a6678be2306bc703e508ad177cf4037`. The server/persona
worktree is independent. No firmware is flashed, OTA published, partition changed,
or provisioning/backend implementation replaced by this work.

Authoritative hardware: `main/boards/folotoy/ai-passport/config.h`, `config.json`,
board README and the published signed-OTA implementation. ESP32-C3, single core,
8MB Flash, no PSRAM; ST7789P3 240×320 RGB565, SPI 40MHz; three ADC ladder buttons
on GPIO0; ES8311 full-duplex I2S 24kHz. The GPIO map and voltage windows are kept.
ESP-IDF >=6.0.1 (CI 6.1), LVGL ~9.5.0, esp_lvgl_port ~2.9.0. Audio input/output/
Opus priorities remain 8/4/2; LVGL remains 1. Key wake suppression and power-save
shutdown remain board owned. Long OK now opens/backtracks the UI instead of
jumping directly into provisioning; its existing five-second hold threshold remains.

The release uses `partitions/mia-passport-8m-candidate.csv`, not the generic 8MB
layout: OTA slots 0x20000/0x360000, each 0x300000; assets 0x660000/0xa0000;
cardid 0x356000/0x4000 and recovery 0x700000/0x100000. This file is unchanged.
The name "candidate" is historical; this is the existing release's layout.

## Architecture and interaction

Extend the existing board `YoumiDisplay`, retaining `SpiLcdDisplay` initialization,
its single 240×20 RGB565 DMA strip (9,600 bytes), partial rendering and its 32KB
no-PSRAM LVGL pool. A custom LVGL draw object replaces stock chat objects. Eyes,
brows, tiny mouths, rings, lists and progress bars use draw primitives. There is
no screenshot background, canvas, blur, full-frame animation or secondary firmware.
The only added bitmap data is a flash-resident 16px/2bpp font subset. Draw descriptors
are stack values. LVGL itself manages transient draw tasks inside its existing pool.

Main/network callbacks publish bounded model changes; the LVGL timer copies the
model with a nonblocking try-lock. Project UI code performs no per-frame heap
allocation. Timer targets: idle 200ms (5Hz), interaction 80ms (12.5Hz); these are
requested rates, not measured device FPS. Only face/waveform/spinner regions animate.
Static pages refresh on events. Sleep suppresses redraw. Actual STT submission
enters thinking; existing status events enter idle/listening/speaking; backend
emotion messages select the six design moods (plus neutral/sleepy). The waveform
is a lightweight activity visualization gated by actual VAD/playback state, not an
amplitude oscilloscope. Audio capture/encode/playback implementations are unchanged.

On the face: OK retains voice behavior, up/down retain volume. Long OK opens the
menu. In menus: up/down select, OK confirms, long OK goes back. Password input uses
nine character cells plus delete / `aA#` (next bank) / confirm; eleven banks cover
all 95 printable ASCII characters including space, quotes and backslash. WPA
passphrases are 8–63 characters or 64 hexadecimal digits. Scanned UTF-8 SSIDs are
preserved, bounded at 32 bytes. Enterprise/WEP/WPA3-only networks are rejected
because the existing build does not enable those modes. Existing browser provisioning
remains available for other credential/SSID input needs.

Wi-Fi UI deliberately uses the existing esp-wifi-connect 3.3.1 localhost HTTP
`/scan` and `/submit` interfaces. A background task waits for the existing config
AP, reads a bounded 4KB response and displays up to 12 distinct SSIDs sorted by RSSI.
It does not interfere with the driver's scan-result ownership. The existing AP
handler validates credentials and saves them. The existing `WifiBoard` takes over
station reconnection after config exit. Only its real connected event for the
requested SSID displays success. Wrong passwords/HTTP errors/timeouts display an
error. No success screen is entered just because credentials were submitted.

The OTA menu checks the existing discovery service, then calls the existing
`Application::UpgradeFirmware`. Signed header/board/version/sequence/layout/assets
checks, inactive-slot writes and readback hash, boot selection, failed-update audio
restart and trial rollback are retained. The progress bar reads real byte progress;
100% means "verifying firmware", not installation success. It never generates a
release/signature or changes version/sequence. An accepted update retains the
existing deliberate audio stop/restart policy.

## Reproduce screenshots

Use CMake, a C++17 compiler and LVGL v9.5.0 at commit
`85aa60d18b3d5e5588d7b247abf90198f07c8a63`:

```sh
git clone --depth 1 --branch v9.5.0 https://github.com/lvgl/lvgl.git /tmp/lvgl-ui
cmake -S scripts/ui -B /tmp/ui-build -DLVGL_SOURCE=/tmp/lvgl-ui -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/ui-build -j 4
/tmp/ui-build/youmi-ui-preview /tmp/ui-renders
python3 scripts/ui/compare.py /tmp/ui-renders docs/Youmi-ui /tmp/ui-comparison
```

The preview uses the production `Painter` and font through real LVGL software
rendering, RGB565 and the same 20-row strip with a 32KB pool. The host alone stores
a full output frame to write PPM files. Fixture time, network names, battery and OTA
percentage are explicit in the preview executable; none are firmware defaults.
All 12 native-size comparisons and source hashes are in `verification/`.
The reference emotion montage is a gallery/preview target, not six simultaneous
runtime emotions. The "display settings" menu opens this gallery.

Current visual result is an adaptation, not pixel-identical: device bezel/cropped
borders, starfield and simulated glow are omitted; eyes use concentric primitives;
text uses the bundled readable subset. Screen 09 deliberately differs for complete
password entry; the 5GHz fixture name is changed to 2.4GHz to avoid implying C3
5GHz support. Review each comparison; pixel MAE is descriptive and is not an
acceptance score. No 1:1 claim is made from compilation or metrics.

Font: NotoSansCJKsc-Regular.otf from notofonts/noto-cjk, SIL OFL 1.1 (see
`FONT-LICENSE.txt`), converted with lv_font_conv 1.5.3. Regenerate with
`scripts/ui/generate_font.py <source.otf> <lv_font_conv>`; source SHA256
`2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b` must be checked
against the downloaded source before comparing reproducibility.

## Validation boundaries

Host tests cover all printable password characters, WPA length/PSK rules, UTF-8
truncation, deterministic blink/gaze/small mouth geometry and existing signed OTA
fault scenarios. The preview renders 12 screens and exercises repeated expression
changes in the 32KB pool. Actual host figures are in `verification/comparison.json`;
these exclude the SPI bus, FreeRTOS, networking, audio and ESP allocator overhead.
They must not be reported as C3 performance or incremental firmware heap usage.

Firmware logs `YoumiUI` every ten seconds when awake: internal free heap, largest
contiguous block, lifetime heap minimum, LVGL usage/largest block, maximum draw
submission time, full LVGL refresh-cycle duration, and LVGL task free stack. Draw
submission duration is not the raster/SPI duration; refresh-cycle duration includes
software rendering and port flush handoff and needs logic-analyzer corroboration
for physical bus completion. Task CPU occupancy needs a board trace/runtime stats.
Wi-Fi uses a transient 6KB worker stack, OTA checks use the existing updater's 12KB
stack budget; bounded HTTP/JSON buffers are additional transient heap allocations.
The incremental <30KB target is not yet measured on hardware.

**No developer board is connected.** Not verified: localhost provisioning over the
real AP interface, key ergonomics/ADC behavior, panel orientation/colors/tearing,
actual FPS and refresh times, free heap/largest block with Wi-Fi+voice, task CPU
occupancy, Wi-Fi failure/cancel/recovery on device, audio interruption/reconnect,
OTA forward/trial rollback/power loss, current draw or continuous voice stability.
Do not ship based solely on host screenshots and builds. No destructive flashing
or partition migration is authorized by these verification instructions.
