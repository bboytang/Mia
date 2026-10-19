# YOUMI ESP32 firmware UI — visual references

These 12 images are **visual targets**, extracted from the conceptual overview artwork and resized to 240x320 for convenient side-by-side comparisons. They are NOT source bitmaps for full-screen embedding. Pixel-perfect reproduction at 240x320 must be judged with a native-size preview (and ideally on real hardware). The collage has stylized text and simulated effects that need adapting for legibility, RAM, screen driver and actual button input.

Screen mapping:
01 boot; 02 idle; 03 listening; 04 thinking; 05 speaking; 06 emotions (six samples on one page); 07 settings; 08 Wi-Fi network list; 09 Wi-Fi password reference (do not implement numeric-only Wi-Fi password input); 10 connecting; 11 success; 12 OTA.

UX preferences:
- Face stays the focus. Large symmetric blue/violet eyes, sparse mouth: idle = tiny curved smile; listening = tiny dot; thinking = short understated line; speaking = small mouth states (closed/small oval/small smile). No tongue, giant open mouth or protruding teeth.
- Black background, sparse cyan and violet accents, selective small highlights; no full-screen particle simulation.
- Remove nonessential miniature text, prioritize readable labels and 3-button control. Treat the concept art's iconography and labels as direction, not proof of functional implementation.
- Never block audio/network/OTA to render animation.

Implementation requirements:
1. Inspect repository FIRST: find existing firmware, target board, screen driver, GPIO map, buttons, available RAM/flash, audio pipeline, networking, OTA partition table and whether there is PSRAM. If any of these differ from the design, report them and adapt. Never invent pin assignments, board model or driver.
2. Integrate into the existing firmware architecture. Do not break Youmi voice/WebSocket/provisioning/backend behavior. Respect SDK/library version already used.
3. Build UI out of LVGL primitives/simple pre-quantized RGB565 sprites, partial line-buffer rendering / damage regions. No 240x320 full-screen double buffer, no large per-frame image sequences, no runtime Gaussian blur, no per-frame heap allocations.
4. Each emotion and voice state should be a deterministic, testable state machine. State change from actual voice pipeline events; never simulate success as if network/OTA complete.
5. Provide screenshot-preview or simulation renderer at native 240x320 with every screen; compare against reference, iterate, and show side-by-side. If emulator/screenshot is unsupported, say so.
6. Build project using actual toolchain; report size/RAM/Flash, measured redraw/update times, free heap / largest block before and during Wi-Fi + voice, OTA compatibility where supported. If board is unavailable, label tests as not run.
7. Carefully handle real password entry: use existing BLE/captive-portal/provisioning UI if supported, or implement full WPA password character selection with 3 hardware keys; the illustrated numeric keypad alone is insufficient for general Wi-Fi passwords.
8. Confirm with user before destructive flash or OTA partition changes.
