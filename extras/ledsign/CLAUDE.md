# LED Sign System

## Purpose

Controls BetaBrite Alpha Protocol LED signs via ESP32 microcontrollers. Each sign is assigned a zone (starter, usher, finish, registration, audience) via MQTT and displays context-appropriate content during races. All devices run identical firmware — behavior is determined by zone assignment.

## How It Fits

The Race Server publishes race state changes. This firmware receives zone-specific content via MQTT and drives BetaBrite signs via RS232 serial. Emergency broadcasts override all signs instantly. During idle periods, registration/audience signs rotate sponsor messages.

## Key Files

- `src/main.py` — Main application (MicroPython). HTTP discovery polling, MQTT content subscription, BetaBrite serial output
- `src/betabrite.py` — BetaBrite Alpha Protocol implementation (display modes, colors, effects)
- `src/config.py` — Configuration management (WiFi, MQTT, HTTP endpoints)
- `src/boot.py` — Startup and WiFi connection
- `src/test_betabrite.py` — Interactive hardware tests

## Hardware

- **Controller**: ESP32 with MicroPython
- **Serial**: MAX3232 TTL-to-RS232 converter
- **Sign**: BetaBrite LED sign (Alpha Protocol compatible)
- **Wiring**: TX/RX through MAX3232 — correct wiring is critical

## Lifecycle

1. **UNCONFIGURED**: Polls HTTP endpoint (`/ledsign.php`) for zone assignment using MAC address
2. **CONFIGURED**: Subscribes to zone-specific MQTT topics for content delivery
3. **OPERATING**: Displays content, responds to priority overrides (emergencies)

## Dependencies

- MicroPython on ESP32
- WiFi access to race network
- MQTT broker and DerbyNet web server on `192.168.100.10`

## Common Tasks

- **Flash**: Upload MicroPython firmware, copy `src/` files to ESP32
- **Test signs**: Run `test_betabrite.py` interactively on ESP32 REPL
- **Run tests**: `cd tests/ && pip install -r requirements.txt && pytest`

## Gotchas

- **Zone architecture**: Signs are agnostic — identical firmware, zone determines behavior
- **Priority messaging**: Emergency broadcasts override all zones instantly
- **BetaBrite modes**: Rotate, flash, scroll, roll, wipe — see `BETABRITE.md` for capabilities
- **176 unit tests**: Comprehensive test suite in `tests/`

## Related Docs

- [BETABRITE.md](BETABRITE.md) — Display capabilities, modes, effects, colors
- [ESP32_BETABRITE_IMPLEMENTATION.md](ESP32_BETABRITE_IMPLEMENTATION.md) — Hardware integration guide
- [LED_SIGN_INTEGRATION_PLAN.md](LED_SIGN_INTEGRATION_PLAN.md) — System integration plan
- [src/README.md](src/README.md) — Firmware architecture (v1.1.0)
- [TODO-FIRMWARE-AUDIT.md](TODO-FIRMWARE-AUDIT.md) — Known firmware issues
