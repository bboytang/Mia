# FoloToy AI Passport (ai-passport)

## Mia firmware variants

`mia-ai-passport` and `mia-ai-passport-dev` reuse this board's pins and drivers with a distinct release
identity. First installation requires device layout/security review and explicit owner confirmation. See
[Mia architecture, protected flash regions, staged implementation and OTA design](../../../../docs/firmware/mia-ai-passport-release.md).
This variant pins the current Mia HTTP/WS endpoints, uses the existing Wi-Fi
hotspot/browser provisioning, and blocks legacy unsigned firmware/asset updates.

Board definition that lets the XiaoZhi voice assistant run on the
[FoloToy AI Passport](https://github.com/FoloToy/ai-passport) wearable.

## Hardware

- MCU: ESP32-C3, 8 MB flash, **no PSRAM**, USB Serial/JTAG console
- Audio: ES8311 codec (I2C 0x18) on the shared I2C bus, I2S full-duplex
  (amplifier enable not wired, treated as always on)
- Display: ST7789 (ST7789P3) 240x320 portrait, 4-line SPI
- Battery: CW2017 fuel gauge (I2C 0x63, optional)
- Buttons: UP / DOWN / OK share GPIO0 (ADC1_CH0) through a resistor ladder

Pin mapping follows `ai-passport/components/bsp/include/bsp_pins.h`:

| Function | Pin |
| --- | --- |
| LCD MOSI / SCLK / CS / DC | 9 / 8 / 1 / 20 |
| LCD backlight (PWM) | 21 |
| I2S MCLK / BCLK / WS / DOUT / DIN | 6 / 5 / 3 / 2 / 4 |
| I2C SDA / SCL | 10 / 7 |
| Buttons (ADC ladder) | GPIO0 |

## Build

```sh
python scripts/build.py folotoy/ai-passport --name ai-passport
```

Outputs `build/merged-binary.bin` (8 MB flash, USB Serial/JTAG console).

## Controls

The three physical keys map to XiaoZhi's voice-assistant actions:

- **OK** — single click: toggle the chat state (or enter Wi-Fi config mode
  while starting up); on Mia, hold for 5 seconds while idle to start the
  Wi-Fi provisioning hotspot
- **UP** — single click: volume +10; long press: max volume
- **DOWN** — single click: volume -10; long press: mute

Because the ladder shares one ADC pin, XiaoZhi reads it as three
independent ADC buttons (the same pattern as the ESP-BOX-Lite).

The Mia five-second OK action also works from the dimmed or screen-off idle
stages: the hold wakes the device and continues into provisioning. It is ignored
during listening, speaking, notifications, activation and OTA. Connect the phone
to the hotspot named on the Passport screen, then open the HTTP address shown
there in a browser and enter the target 2.4 GHz Wi-Fi SSID and password. Stay
connected if the phone warns that this hotspot has no Internet access. A
successful connection is saved alongside existing SSIDs. Mia explicitly enables
hotspot provisioning and disables BluFi; no Mia iPhone app change is required.

## Power management

The Mia 1.0.1 OTA update uses 60 seconds to dim to 10%, 120 seconds to turn the
screen off and down-clock while retaining Wi-Fi, and 1800 seconds to enter deep
sleep. Voice activity restores normal brightness, suspends the idle deadlines,
and starts a fresh countdown when idle resumes. The owner has requested a signed
1.0.1 trial OTA package; the new power stages still need device verification.

The original `ai-passport` variant retains the following existing policy:

The Passport is a battery wearable, so the board gives up power in three stages,
all counted from the last key press:

| Idle | Stage | What happens |
| --- | --- | --- |
| 60 s | Dim | Backlight drops to 10%; nothing else changes |
| 360 s | Soft sleep | Panel Sleep In, backlight off, codec off, CPU down-clocked to 40 MHz |
| 2160 s | Deep sleep | Entered from the soft-sleep stage; any key wakes the device through GPIO0 and restarts the application |

`kDimSeconds`, `kSoftSleepSeconds`, `kDeepSleepSeconds`, `kDimBrightness` and
`kStandbyCpuMinFreq` at the top of `ai_passport_board.cc` tune the policy. Three
properties of this shape are deliberate:

- **The soft-sleep stage is shallow on purpose.** It draws roughly 20 mA, which
  over half an hour is about 10 mAh of the 520 mAh cell - around 2% of a charge.
  The CPU keeps running, so a key press brings the whole device back in about a
  second with the conversation, the page and the session intact, instead of
  rebooting into a fresh idle state.
- **The deep-sleep fallback is what makes that affordable.** Because it is
  reached from the soft-sleep stage rather than directly, a Passport left alone
  still ends up at deep-sleep current within 36 minutes. An unbounded
  "soft sleep only" policy would look better for half an hour and then flatten
  the cell overnight.
- **Automatic light sleep is deliberately not enabled**, even though it would take
  the soft-sleep stage below 1 mA in the same window. The countdown behind all
  three deadlines runs on an `esp_timer` created with
  `skip_unhandled_events = true`, and such a timer does not wake the chip out of
  light sleep - so switching light sleep on would silently stretch 60 / 360 /
  2160 into wall-clock times nobody asked for. `SetStandbyClock()` only scales
  the CPU frequency, which has no such effect. `CONFIG_PM_ENABLE` in `config.json`
  is what makes that call work.

Every stage is gated by `Application::CanEnterSleepMode()`, so an ongoing
conversation or playback pushes the deadline back instead of being interrupted.
Any key press cancels the countdown (`OnPressDown`, so a long press counts too)
and, from the soft-sleep stage, brings the device back. The NVS `sleep_mode` flag
the provisioning page writes disables all three stages at once.

That gate has two consequences worth knowing about:

- A board that never reaches `kDeviceStateIdle` keeps the screen lit
  indefinitely. The common case is an unprovisioned board sitting in Wi-Fi config
  mode, which the state machine only lets move to activating or audio testing.
  Sleeping outside the idle state would be a framework change affecting every
  board, so it is not done here - a Passport delivered unconfigured should be
  configured, not left on a shelf.
- `PowerSaveTimer` stops checking that gate once it is past its sleep deadline,
  so the board re-checks `CanEnterSleepMode()` itself in both stage transitions.
  A conversation started by the wake word presses no key and therefore never
  resets the tick counter; without the re-check the deep-sleep fallback would cut
  it off mid-conversation.

### Turning the screen and audio off

Closing the audio path is the part that is easy to get wrong. The audio input
task re-enables the codec on every read it starts, so calling
`EnableInput(false)` from the board would be undone immediately. The stage instead
switches the wake word off (`AudioService::EnableWakeWordDetection(false)`) and
leaves the codec to `AudioService`, which closes the PCM path on its own once the
input has been idle for `AUDIO_POWER_TIMEOUT_MS` (15 s). The wake path has to
switch the wake word back on explicitly: the idle branch of the application state
machine does not run again on its own, so without that the device would never
hear its wake word again for the rest of the boot.

The radio stays up. `WifiManager::StopStation()` is worth about 10 mA, but it was
measured on hardware to cost more than the current it saves: with the station
stopped the MQTT protocol keeps retrying - `esp_mqtt` on its own timer plus the
protocol's 60-second one - and once the application is idle again one of those
attempts surfaces `Lang::Strings::SERVER_NOT_CONNECTED` as a user-visible alert,
which also plays a notification sound and briefly reopens the codec on a device
that is supposed to be asleep. The alert latches, so it is still on screen after
the next key press. Keeping the link avoids all of that, keeps server push and an
alive session, and makes the wake instant because no Wi-Fi reconnect is needed.
The arithmetic changes with the window: over eight hours the radio is worth about
a third of the cell, so a longer window would have to stop the station and quiet
the protocol while it is down.

The three keys keep waking the device in every stage, but the press that wakes it
must not also act:

- One wake-key guard drops the whole press, not a window. It is armed on the
  press-down that wakes the device out of soft sleep, or from the key level sampled
  when the button component starts after a deep-sleep wake, and it is released when
  the component reports the end of that press sequence (`BUTTON_PRESS_END`). That is
  what keeps a long press from getting through: the component grades it 2 s after
  the press started, measured on hardware to be past any fixed window short enough
  to leave a normal press alone. `kWakeKeyGuardMs` (10 s) is only a safety net for a
  release event that never arrives.
- A deep-sleep wake whose key was already released before the button component
  starts arms no guard, so the next press acts normally - there is no wake press
  left to drop.
- A cold boot gets no guard, so OK during `kDeviceStateStarting` keeps working as
  the provisioning entry point.
- OK with the network down shows the ordinary "connecting" hint instead of failing
  to open the audio channel and raising an error alert. That covers a link that
  dropped on its own while the screen was off. Provisioning and the Wi-Fi-config
  speaker test open no audio channel, so they are not gated on the station.

### Deep sleep

Deep sleep follows the FoloToy AI Passport BSP shutdown contract
(`docs/reference/shinku-chen/deep-sleep-peripheral-power-off` in the BSP repo),
in this order:

1. Clear every previously armed wake source
   (`esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL)`) and then arm the GPIO0
   low-level wake source with IDF's
   `esp_sleep_enable_gpio_wakeup_on_hp_periph_powerdown()`. Automatic light sleep
   leaves the RTC timer armed for the next scheduled event, and a deep sleep that
   inherits it wakes up again on the next OS tick - measured on hardware as a reset
   roughly a second after sleeping, reported as `ESP_SLEEP_WAKEUP_TIMER` with an empty
   GPIO wake status. ESP32-C3 has no EXT0/EXT1, and the GPIO call takes a pin
   *bit mask*, so passing `GPIO_NUM_0` instead of `1ULL << GPIO_NUM_0` silently arms
   nothing. If arming fails the board falls back to a timed wake so the device cannot
   be stranded asleep.
2. CW2017 `CONFIG=0xF0`, read back 5 ms later, retried once on mismatch. The
   board init reverses this with the chip's restart-then-active cycle, so a
   gauge that slept before a deep sleep reports again after the wake.
3. ES8311 suspend: `esp_codec_dev` disable/close first, then the BSP's suspend
   register sequence written through a board-owned I2C device handle, with the key
   registers read back. REG0E is written as the vendor value `0xFF` but only bits
   6:0 are meaningful - bit 7 does not latch on this part, so it reads back as
   `0x7F`, which is what the check expects. The BSP checks the same six registers
   through a mask (`bsp_es8311_sleep_check.c`).
   Both I2S channels are then stopped explicitly, so the codec is not left driving
   inputs whose master went quiet once the pins are released. Codec construction
   enables those channels once and only `esp_codec_dev_close()` stops them again,
   so a board that never played anything since boot reaches this point with the
   clocks still running.
4. MCLK/BCLK/WS/DOUT/DIN released as inputs with no internal pulls.
5. SDA/SCL released the same way (terminal: no I2C transaction is valid after
   this point).
6. Under the LVGL lock: panel display-off and Sleep In, backlight PWM stopped at
   zero, then CS high / SCLK / MOSI / DC / backlight low, each held through deep
   sleep with `gpio_deep_sleep_hold_en()`.

A failed step is logged but never aborts the shutdown, so the device cannot be
left awake with a half-shut-down board. If deep sleep somehow returns, the board
restarts instead of trying to recover the released buses.

Pin holds are latched in the RTC domain and survive the deep-sleep reset, so
`gpio_hold_dis()` has to be called for every held pin on the way back up.
`ReleaseDeepSleepHolds()` does that first thing in the board constructor. On this
board the holds that survive a wake are GPIO1 (LCD CS) in `RTC_CNTL_PAD_HOLD_REG`
and GPIO8/GPIO9 (LCD SCLK/MOSI) in `RTC_CNTL_DIG_PAD_HOLD_REG`; without the
release they stay held and the panel never comes back.

What software cannot fix: the Passport does not wire the amplifier enable to the
MCU (`AUDIO_CODEC_PA_PIN` is `NC`), so amplifier standby current, regulator
quiescent current, the external I2C pull-ups and cell self-discharge all remain.
Isolate those on hardware if standby current still looks high.

Status of hardware verification (ESP32-C3, IDF 6.1). Verified on the device: board
init and a stable idle loop; reaching `kDeviceStateIdle` after provisioning; the dim
stage firing on schedule, the soft-sleep stage 300 s after it and the deep-sleep
fallback at the 36-minute deadline, all at the expected wall-clock time (`Idle 60s`
at 65 s and `Idle 360s` at 365 s of uptime, with the 4.7 s of startup subtracted;
the fallback at boot + 2165 s, which is also where a key press woke the device out
of it); the CPU down-clock landing as a single `esp_pm_configure` call, confirmed by
the kernel's `pm: Frequency switching config: ... Light sleep: DISABLED`; the
soft-sleep window staying silent for its whole 505-second run - no MQTT errors, no
alerts, no protocol or station disconnect and no codec reopen; the soft-sleep wake
restoring the panel, backlight and clock with zero Wi-Fi activity (no station start,
stop, scan or DHCP - the link is never dropped), the codec reopening on demand, and
a full spoken exchange (wake -> conversation -> speech recognition -> answer ->
volume keys) working afterwards; and a single OK press waking the device out of
soft sleep being swallowed outright - no state transition, no microphone open and no
MQTT traffic followed it; and a deep-sleep wake with the key still held keeping that
press from being graded a long press - no mute. Both runs used the earlier
window-and-release guard; the guard has since been reworked so that a whole press
sequence is dropped, and the reworked paths (soft-sleep wake as a short press and as
a long press, a deep-sleep wake whose key is already released, and OK during
`kDeviceStateStarting`) still have to be re-checked on hardware. For an earlier revision that went
straight to deep sleep: CW2017 sleep with a matching readback; the ES8311 suspend
sequence passing its register readback; the I2S/I2C pin release; deep sleep actually
sticking (no self-wake from a leftover wake source); a key press waking the device
with `esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_GPIO` and
`esp_sleep_get_gpio_wakeup_status() == 0x1`; and the deep-sleep pin holds being
released on the way back up (confirmed through `RTC_CNTL_PAD/DIG_PAD_HOLD` register
readbacks). The terminal shutdown sequence itself is verified through the current
code path as well: `CW2017 asleep (CONFIG=0xF0 verified)`, `ES8311 suspended and
verified (attempt 1)` and the I2S/I2C pin release all reported clean on the way into
the fallback.

Not verified: the idle, soft-sleep and deep-sleep currents (the 20 mA above is an
estimate from the parts list, not a measurement); and whether disabling
`CONFIG_ESP_SLEEP_GPIO_ENABLE_INTERNAL_RESISTORS` saves anything on top of the
external 10 kOhm pull-up. A successful build is not hardware validation.

A note on `i2s_common: i2s_channel_disable ... has not been enabled yet` in the log:
it comes from `esp_codec_dev`'s own pending-disable bookkeeping when the
`audio_testing` state re-opens the PCM path, not from this board's I2S handling -
the board reports how many channels it actually changed, which is zero in this path.

The soft-sleep stage keeps the CPU awake, so `pm: Frequency switching config:` shows
`Light sleep: DISABLED` by design; a later change that wants to enable it has to
move the three deadlines off the `skip_unhandled_events` timer first.

## Notes / calibration

- Display orientation, color inversion and the backlight PWM polarity were
  taken from the Passport BSP; verify on real hardware and adjust the
  `DISPLAY_*` macros in `config.h` if the image is rotated/inverted or the
  backlight is reversed.
- The ADC button voltage windows assume the Passport's external 10 kOhm
  pull-up. Re-measure with the Button page if thresholds drift.
- CW2017 presence is optional; without the chip the status bar shows no
  battery level and the board keeps working.
- `CONFIG_USE_ESP_WAKE_WORD` is off, so the board is key-driven. Turning it on
  costs about 60 KB of heap (measured on hardware: the lowest free heap fell from
  47-70 KB to 9.8 KB) and would contradict the soft-sleep stage, which releases
  the microphone only because no wake word needs to keep listening for it.
- `ES8311_CODEC_DEFAULT_ADDR` is the 8-bit form (`0x30`); an `i2c_device_config_t`
  takes the 7-bit address. esp_codec_dev shifts it when it builds the codec's own
  handle, and the terminal suspend sequence here talks through a board-owned handle,
  so that one shifts too (`kEs8311I2cAddress`). Using the unshifted address talks to
  nothing: measured on hardware, every register readback returned `0xF0` and both
  suspend attempts failed.

### Mia animated face (1.0.1 OTA)

Only the Mia variants use `YoumiDisplay`, a `SpiLcdDisplay` subclass. It reuses
ST7789/LVGL and keeps the existing status, battery/network indicators, subtitles,
notifications and preview-image path. A black 216x178 face region contains two
cyan eyes and a mouth. Fixed LVGL objects animate at 20 Hz, with no per-frame
allocation, image decoding, extra full-screen framebuffer or new resource assets.
The installed 1.0.0 assets and partition layout remain compatible with app OTA.

`mia_face.h` provides blink/gaze geometry, six moods and listening/speaking/
connecting activity. Existing localized status notifications select activity;
backend emotion names select mood (unknown names use neutral). Speaking motion
is a stylized loop, not synchronized to PCM or phonemes. Soft sleep pauses the
LVGL timer before panel sleep-in; waking resumes it. No new voice protocol or
core application dependency is introduced. The stock Passport UI is unchanged.

Host tests compile the exact geometry header and check expressions, fallback,
blink timing and object bounds. CI must build both Mia variants and the stock
board. Smoothness, subtitle overlap, heap during long conversations, sleep/wake,
and audio playback under animation load still require device testing. These
changes are included in the owner-requested 1.0.1 trial OTA release.

Mia subtitles are normalized to simplified Chinese in `SetChatMessage`, covering
both ASR and assistant/notification text. OpenCC 1.1.9 dictionary data is pinned
under `third_party/opencc` with its Apache-2.0 license. Configure-time generation
writes constexpr tables into the build directory; Taiwan variant normalization
then longest phrase/character matching preserves forms such as 著作 and 乾坤.
This changes display text only, not server history, audio or other boards.
The existing CI/release build command selects `--language zh-CN` for built-in
prompts; language remains a build parameter, following repository policy.
The dictionaries are application code/data, not changes to the frozen assets.

### Mia 1.0.2 personal memory OTA candidate

Uses the existing signed A/B application update and frozen pins, partitions,
assets and public key. The first boot still confirms authenticated legacy voice
within the original 120 seconds before asking for owner input. After confirmation,
the screen shows a 128-bit random one-time code for up to ten minutes. Open the
existing manager over HTTPS, select this device, choose 硬件授权 and enter that
code. No USB, Wi-Fi reset, account service or new database schema is required.

The device exchanges the code only at the pinned HTTPS endpoint with CA/hostname
verification and redirects disabled. The private credential is committed to a
separate NVS namespace, never to an OTA capsule or discovery response. Future
voice requests use the pinned WSS endpoint and private header. A stored invalid
grant fails closed instead of selecting legacy WS. On subsequent boots the
existing grant is renewed through the existing HTTPS renewal endpoint; a transport
failure preserves it. The existing 30-day server expiry and owner revocation
remain authoritative. Continuous uptime beyond expiry without a renewal still
requires a restart/reauthorization in this personal candidate.

Deployment order: HTTPS plus the existing owner authorization interface first;
signed OTA and physical owner confirmation second; full private memory backend
cutover after grant issuance. Confirmed hardware enrollment is not inferred from
a build, an OTA HTTP request, a MAC address, or an earlier voice connection.
Actual C3 TLS, screen readability, microphone and speaker remain device checks.

### Mia 1.0.3: six-digit screen code

Owner device testing found the 1.0.2 32-character code was not fully readable on
the screen. Version 1.0.3 shows six decimal digits (including leading zeroes).
The device retains a separate random 128-bit proof in its own NVS and sends it
only over verified TLS. The six digits approve the one pending request on the
selected device; they cannot be exchanged for a credential. The existing manager
uses one expiring Redis record, current binding/credential versions and client
identity, with its original rate limits. No task schema or user account changes.
The proof survives a restart during enrollment; successful credential storage
clears it. Ten-minute expiration, revocation and owner checks remain.

### Youmi 1.0.4 OTA

Updates the provisioning SSID prefix to Youmi and renames the display implementation.
Uses the installed 1.0.3 firmware as its base, retaining the signed updater, board identity,
partition table, frozen assets, release public key, authorization and audio behavior.
The application descriptor remains compatible with the installed updater.
