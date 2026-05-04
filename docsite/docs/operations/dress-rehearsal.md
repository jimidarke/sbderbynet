# Dress Rehearsal Runbook

Two parallel rehearsals, in order:

1. **Cloud twin with browser virtual hardware** — exercises the full software stack remotely.
2. **Local Pi with real hardware** — exercises the actual event setup.

The cloud twin catches integration regressions cheaply; the Pi rehearsal catches anything truly hardware-bound.

---

## Part A — Cloud-twin rehearsal

### Prereqs

- `./scripts/derbyvps.sh audit` exits 0; four healthy SBDerbyNet containers, UISP siloed, all expected ports free.
- "LAST CLOUD-SYNC" `last_sync_utc` from the audit is within a few minutes (Pi is syncing).
- `.env` provisioning is done. On a fresh VPS, `./scripts/derbyvps.sh bootstrap` first.

### Steps

0. **Tablet sanity check** — on the actual race-day Android tablet, in portrait, before anything else:
    - Open the coordinator page in **Chrome on the tablet**, not DevTools mobile mode (DevTools is a poor proxy for real touch).
    - Drag-scroll top-to-bottom — must be smooth, no rubber-band fight.
    - Every interactive element ≥ 48 px tall in portrait. Every Heat-Control button label fits on one line.
    - Timer-status row labels readable from arm's length.

1. **Sign in as RaceCoordinator** at `https://uisp.darketech.ca/derbynet/login.php`.
2. **Open virtual control panel**: `https://<host>/derbynet/virtual/index.php`. Confirm one card per finish timer, the start timer, LED signs (starter + one usher per lane), and displays.
3. **Open all virtual devices** in popup tabs. Each connection chip should reach **connected** within ~5 s.
4. **Create or select a test event/round**.
5. **Run a heat manually** through the virtual hardware:
    - Toggle each finish-timer to *Ready*.
    - On the start timer, click **OPEN GATE — GO**.
    - On each finish-timer, click **CAR CROSSED FINISH LINE** at staggered intervals (or use *Auto-finish* with a 2.0–6.0 s window).
    - Coordinator page advances; results record.
6. **Trigger a pull-forward** (dedicated page):
    - In the running round's controls, tap **Pull Forward…** (only appears once at least one heat has run).
    - Tap a racer scheduled for an upcoming heat.
    - Inline simulation renders: dropout summary, moves table, byes, fairness warnings, side-effect note.
    - **Apply + Announce**. Confirm Undo button briefly pulses, staging announcement appears on `/derbynet/kiosk.php?name=now-racing`, schedule matches simulation byte-for-byte.
7. **Run the full suite for the round** with auto-mode on all finish timers.
8. **Inspect**:
    - `/derbynet/device-status.php` — virtual devices appear with `B_` hwids.
    - `/derbynet/results.php` — finish times look plausible.
    - `./scripts/derbyvps.sh logs race-server` — no errors.

### Pass criteria

- All virtual devices stayed connected throughout.
- Pull-forward rendered correctly in portrait, simulation matched the post-Apply schedule.
- Round completed without intervention beyond GO/finish.
- No `B_` hwid leaked into a "must be online to race" decision.

---

## Part B — Local Pi rehearsal

On the actual race-day Pi with all hardware on the `192.168.100.x` subnet.

1. **Health check**:
    ```sh
    sudo systemctl status derbyrace
    mosquitto_sub -h 192.168.100.10 -t 'derbynet/#' -v -W 5
    ```
    Confirm telemetry from real finish timers, start timer, signs.
2. **Mock event**: import test roster, generate a schedule with the real lane count, run a complete round end-to-end.
3. **Pull-forward live**: mid-event, open `pull-forward.php` from the coordinator's tablet (portrait), pick a racer, **Apply + Announce**. Confirm staging-area kiosk shows the broadcast, moved racer appears on the lane LED in the next heat, Undo button pulses on return.
4. **Cloud-sync verification**: after the round, `./scripts/derbyvps.sh audit` from your dev box — `last_sync_utc` within a minute. `device-status.php` on the cloud should show current Pi-synced state.

### Pass criteria

- Real hardware completes a full round without manual time entry.
- Pull-forward triggers a visible staging announcement.
- Cloud sync continues during the rehearsal (one push per minute).

---

## Replay regression test (between rehearsals)

Capture the Pi rehearsal MQTT session:

```sh
mosquitto_sub -h 192.168.100.10 -p 1883 \
  -u "$MQTT_USER" -P "$MQTT_PASS" \
  -t 'derbynet/#' -v -F '{"t":%I,"topic":"%t","payload":%j}' \
  > testing/captures/dress-rehearsal-$(date +%Y-%m-%d).jsonl
```

Replay against the cloud twin (or a local dev stack):

```sh
python testing/replay-real-race.py \
  testing/captures/dress-rehearsal-YYYY-MM-DD.jsonl \
  --broker localhost --user derbynet --pass "$MQTT_PASS"
```

Compare the resulting `RaceChart` against the original. Bit-equivalent ⇒ cloud stack is faithful for race-server behavior.

---

## Race-day go/no-go

Race day is **green** when all four pass:

1. Pull-forward shell tests: `./testing/test-pull-forward.sh https://<cloud>/derbynet`
2. Pull-forward Puppeteer tests: `node testing/puppeteer/pull-forward-test.js http://localhost/derbynet`
3. Both rehearsals (Part A and Part B) pass their criteria.
4. Replay regression test passes against the cloud twin.

If any fails: do not ship to the Pi. Roll back to the last green commit on `master` and rerun.

See also: [Testing](../development/testing.md), [VPS Procedures](vps-procedures.md), [Logging](logging.md).
