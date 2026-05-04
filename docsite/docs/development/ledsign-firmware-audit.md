# LED Sign Firmware Audit

Findings from auditing `extras/ledsign/src/main.py` (firmware **v1.1.0**) on 2026-03-31.

**Overall**: good shape for race day. Items below are improvements, not blockers.

---

## Issues

### 1. MQTT disconnect doesn't update sign display (medium)

**Where**: `src/main.py:866–869`.

When MQTT drops but WiFi is still up, the sign freezes on stale content with no visual indication. `update_display_offline()` only triggers on WiFi loss (line 224), not MQTT loss.

```python
except Exception as e:
    log(f"MQTT error: {e}", "ERROR")
    mqtt_connected = False
    sign.write_text("MQTT LOST", mode='flash', color='red', charset='7high')
```

### 2. No periodic garbage collection (low–medium)

**Where**: main loop `src/main.py:829–893`, `src/boot.py`.

`gc.collect()` only runs once at boot (`boot.py:17`). Long-running MicroPython on ESP32 can fragment heap from JSON parsing, MQTT buffers, string ops.

```python
# every 30 seconds
if now % 30 == 0:
    gc.collect()
```

### 3. OTA update has no integrity verification (medium)

**Where**: `src/main.py:782–813`.

Downloads firmware over HTTP and writes directly to flash with no checksum. A corrupted/partial download can brick the device with no rollback.

Options, in order of effort:

- Read back and compare length before reboot.
- Download to a temp file, verify size/checksum, then rename.
- Add an MD5 alongside the firmware on the server and verify before write.

### 4. Sponsor rotation only shows the first sponsor (low)

**Where**: `src/main.py:647–670`.

`handle_sponsor_rotation()` is admittedly a stub — only displays the first sponsor. Full rotation needs a timer to cycle through the list.

### 5. Dead test code references `publish_identity()` (low)

**Where**: `tests/test_firmware.py:624–650`.

Tests reference `firmware_module.publish_identity()` which doesn't exist in `main.py`. The `IDENTITY_INTERVAL` constant in `config.py:64` is unused.

Either implement identity publishing or remove the dead test code and unused config.

---

## Verified working

- BetaBrite Alpha-Protocol library (`betabrite.py`) — complete and correct.
- Newline handling (`\r` = `\x0d` = BetaBrite `\015`) — passes through correctly.
- Watchdog feeding in main loop (line 831).
- Priority message handling with `display_config.priority`.
- Zone-specific subscriptions (usher-lane pinny, sponsor topic).
- Zone switching on admin reassignment.
- HTTP polling discovery.
- Display-config parsing (named values and raw codes).
- Zone-appropriate ready-state defaults.
