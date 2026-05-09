# LED Sign Firmware Audit Findings

**Date**: 2026-03-31
**Firmware Version Audited**: 1.1.0 (`extras/ledsign/src/main.py`)
**Overall Assessment**: Good shape for race day. Issues below are improvements, not blockers.

---

## Issues to Address

### 1. MQTT disconnect doesn't update sign display (Medium)

**File**: `src/main.py` lines 866-869

When MQTT connection is lost but WiFi is still up, the sign freezes on stale content with no visual indication. The `update_display_offline()` function only triggers on WiFi loss (line 224), not MQTT loss.

**Fix**: Show a visual indicator when MQTT drops:
```python
except Exception as e:
    log(f"MQTT error: {e}", "ERROR")
    mqtt_connected = False
    sign.write_text("MQTT LOST", mode='flash', color='red', charset='7high')
```

---

### 2. No periodic garbage collection (Low-Medium)

**File**: `src/main.py` main loop (lines 829-893), `src/boot.py`

`gc.collect()` only runs once at boot (`boot.py` line 17). Long-running MicroPython on ESP32 can fragment heap from JSON parsing, MQTT buffers, and string ops.

**Fix**: Add periodic collection in main loop:
```python
# Every 30 seconds
if now % 30 == 0:
    gc.collect()
```

---

### 3. OTA update has no integrity verification (Medium)

**File**: `src/main.py` lines 782-813

Downloads firmware files over HTTP and writes directly to flash with no checksum verification. A corrupted or partial download could brick the device with no rollback.

**Fix**:
- Download to a temp file first, verify size/checksum, then rename
- Or at minimum: read back and compare length before rebooting
- Consider adding MD5 checksum file alongside firmware on server

---

### 4. Sponsor rotation only shows first sponsor (Low)

**File**: `src/main.py` lines 647-670

`handle_sponsor_rotation()` has a comment admitting it's a stub — only displays the first sponsor from the list. Full rotation would need a timer to cycle through sponsors.

**Fix**: Implement timer-based rotation in main loop, cycling through sponsor list every N seconds.

---

### 5. Dead test code references `publish_identity()` (Low)

**File**: `tests/test_firmware.py` lines 624-650

Tests reference `firmware_module.publish_identity()` which doesn't exist in `main.py`. The `IDENTITY_INTERVAL` config constant (line 64 in `config.py`) is also unused.

**Fix**: Either implement identity publishing or remove dead test code and unused config.

---

## Verified Working

- BetaBrite Alpha Protocol library (`betabrite.py`) - complete and correct
- Newline handling (`\r` = `\x0d` = BetaBrite `\015`) - passes through correctly
- Watchdog feeding in main loop (line 831) - working
- Priority message handling with display_config.priority - working
- Zone-specific subscriptions (usher-lane pinny topic, sponsor topic) - working
- Zone switching on admin reassignment - working
- HTTP polling discovery - working
- Display config parsing (both named and raw codes) - working
- Zone-appropriate ready state defaults - working
