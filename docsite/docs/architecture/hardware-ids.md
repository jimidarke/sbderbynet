# Hardware IDs

Every device on the race subnet identifies itself in MQTT telemetry and HTTP discovery using a stable hardware ID (`hwid`). The convention is **mostly** consistent, with one explicit exception you should know about.

---

## The conventions

### MAC-derived (default)

Most devices derive `hwid` from their primary network MAC, with vendor prefix stripped, lowercased, and dash-separated. This guarantees the ID is unique to the physical device and survives re-flashing.

Used by:

- LED signs (ESP32 firmware in `extras/ledsign/src/`)
- Derby display kiosks (`extras/soapbox/infra/derbydisplay/`)
- Most generic peripherals

### `/boot/firmware/derbyid.txt` (Raspberry Pi)

Pi Zero finish timers and Pi 4 displays read a plain-text `hwid` from `/boot/firmware/derbyid.txt` at boot. This is set during Ansible provisioning (see [DerbyPi](../components/derbypi.md), [Finish Timer](../components/finish-timer.md)).

The Pi falls back to MAC derivation if the file is missing — but in practice every provisioned Pi has it.

### Hardcoded `"START"`

The ESP32 start timer firmware hardcodes its `hwid` to the literal string `"START"` (see `extras/soapbox/infra/starttimer/main.py`).

!!! warning "Known inconsistency"
    The start timer is intentionally singleton — there's only one of them — so a hardcoded ID was the path of least resistance. It does mean:

    - If you ever run two start timers (e.g. a backup), they'll collide on the broker.
    - The MQTT topic for it is fixed at `derbynet/device/starttimer/state` rather than the standard `derbynet/device/{hwid}/state`.

    Cleanup is parking-lot work: derive `hwid` from the ESP32 chip ID and update the broker subscriptions to match. Tracked separately.

---

## How `hwid` shows up

- **MQTT topics**: `derbynet/device/{hwid}/state`, `derbynet/device/{hwid}/telemetry`, `derbynet/device/{hwid}/status`. See [MQTT API](../reference/mqtt-api.md).
- **DeviceStatus table**: PHP records last-seen times keyed by `hwid`. Visible on `device-status.php`.
- **LED-sign discovery**: ESP32 polls `/ledsign.php?mac=<mac>` (uses MAC literally, not derived `hwid`) to receive zone assignment.
- **Coordinator poll**: `query=poll.coordinator` returns per-`hwid` health.

---

## Lane vs. hwid (finish timers)

Finish timer **lane** is independent of `hwid`. Lane is set by **DIP switches** on the timer board (positions encode `1000`, `0100`, `0010`, `0001` → lanes 1–4). This means:

- All three finish timers can run identical firmware images.
- A failed timer can be physically swapped — flip the DIPs to match the slot, and the new device takes over the lane.
- The `hwid` will change after a swap; the lane assignment in the database may need refreshing on `device-status.php`.
