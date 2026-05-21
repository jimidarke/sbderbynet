# Dress Rehearsal Runbook

Two parallel rehearsals before race day:

1. **Cloud twin with browser virtual hardware** — exercises the full
   software stack remotely.
2. **Local Pi with real hardware** — exercises the actual event setup.

Run both, in that order. The cloud twin catches integration regressions
cheaply; the Pi rehearsal catches anything truly hardware-bound.

---

## Part A — Cloud twin rehearsal

### Prereqs

Use the wrapper for everything operational; it bakes in the right paths,
gates, and backup behavior.

- Cloud twin reachable: `./scripts/derbyvps.sh audit` exits 0 and shows
  5 healthy SBDerbyNet containers (Caddy, MQTT, derbynet-web, race-server,
  derbynet-stats-gen), UISP siloed, all expected ports free.
- Cloud DB is current. Inside the audit output check the "LAST CLOUD-SYNC"
  block — `last_sync_utc` should be within a few minutes if the Pi is
  syncing.
- `.env` provisioning is done. (If this is a fresh VPS, run
  `./scripts/derbyvps.sh bootstrap` first; it generates broker passwords
  and writes the `.env` for you.)

### Step-by-step

0. **Tablet sanity check** (do this on the actual race-day Android tablet,
   in portrait, before anything else):
   - Open the coordinator page in Chrome on the tablet, not just DevTools'
     mobile mode (DevTools is a poor proxy for real touch handling).
   - Drag-scroll the page top-to-bottom — must be smooth, no rubber-band
     fight, no element absorbing the touch.
   - Every interactive element (button, flipswitch, arrow, table row)
     must be ≥48 px tall in portrait. Tap each Heat-Control button —
     no mid-word wrap, every label fits on one line.
   - Timer-status row labels readable from arm's length without leaning in.

1. **Sign in as RaceCoordinator** at `https://uisp.darketech.ca/derbynet/login.php`
   (replace with your `CADDY_HOST` if you've overridden it).
2. **Open virtual control panel**: `https://uisp.darketech.ca/derbynet/virtual/index.php`.
   - Confirm a card per finish timer (one per lane), the start timer card,
     LED sign cards (starter + one usher per lane), and display cards.
3. **Open all virtual devices** in popup tabs from the control panel.
   - Each tab's connection chip should reach **connected** within ~5s.
4. **Create or select a test event/round** in the coordinator UI.
5. **Run a heat manually** through the virtual hardware:
   - Toggle each finish-timer to *Ready*.
   - On the start timer page, click **OPEN GATE — GO**.
   - On each finish-timer, click **CAR CROSSED FINISH LINE** at staggered
     intervals (or use *Auto-finish* with a 2.0–6.0s window).
   - Verify the coordinator page advances and results record.
6. **Trigger a pull-forward** (now via the dedicated page):
   - On the coordinator page, in the running round's controls, tap
     **Pull Forward…** (only appears once at least one heat has run).
   - On `pull-forward.php`, tap a racer scheduled for an upcoming heat.
   - Confirm the inline simulation renders below the roster: dropout summary,
     moves table, any trailing byes, fairness warnings, side-effect note.
   - Tap **Apply + Announce**. Verify you land back on the coordinator page
     and the **Undo Pull Forward** button briefly pulses.
   - Verify the staging announcement appears on `/derbynet/kiosk.php?name=now-racing`:
     the `#race-status-bar` should turn amber and read **STAGING**, then green
     **RACING** while the heat runs, and red pulsing **CHECK TIMER** if the
     timer drops out. (Replaces the older full-page background tint.)
   - Verify the schedule shown on the coordinator page matches the
     simulated moves byte-for-byte.
7. **Run the full suite for the round** (auto-mode on all finish timers).
8. **Inspect**:
   - `https://<host>/derbynet/device-status.php` — virtual devices appear with `B_` hwids.
   - `https://<host>/derbynet/results.php` — finish times look plausible.
   - `./scripts/derbyvps.sh logs race-server` — no errors. (For the full
     log map run `./scripts/derbyvps.sh logs --where`; troubleshooting
     index in `docs/LOGGING.md`.)
9. **Spectator pages** (`docs/PUBLIC_STATS.md`):
   - `./scripts/derbyvps.sh stats-token rotate` to mint a token (or
     `stats-token show` if one's already set).
   - On a phone, scan the QR (or visit the printed URL) — `schedule.html`
     shows the round name + heat table with the current heat highlighted;
     `recent.html` shows the last completed heat(s) ordered by most recent.
   - Strip one character from the token URL → expect a flat 404.
   - `./scripts/derbyvps.sh logs derbynet-stats-gen` — render loop ticking
     every ~30 s, no SQLITE_BUSY retries.

### Cloud-twin pass criteria

- All virtual devices stayed connected for the duration.
- Pull-forward page rendered correctly in portrait orientation, simulation
  matched the post-Apply schedule, announcement reached the kiosk, Undo
  button pulsed and was usable.
- Round completed without manual intervention beyond clicking GO/finish.
- No `B_` hwid leaked into a "must be online to race" decision (the race
  server should treat them like any other timer over MQTT).
- Spectator schedule + recent pages reflected the rehearsed heat results
  within one refresh tick (~30 s), and a wrong-token URL returned 404.

---

## Part B — Local Pi rehearsal

Run on the actual race-day Pi with all hardware connected on the
`192.168.100.x` subnet.

### Step-by-step

1. **Health check**:
   ```sh
   sudo systemctl status derbyrace
   mosquitto_sub -h 192.168.100.10 -t 'derbynet/#' -v -W 5
   ```
   Confirm telemetry from the real finish timers, start timer, and signs.
2. **Mock event**: import the test roster, generate a schedule with the
   real lane count, run a complete round end-to-end.
3. **Pull-forward live**: mid-event, open `pull-forward.php` from the
   coordinator's tablet (portrait), pick a racer, tap **Apply + Announce**.
   Confirm the physical staging-area kiosk shows the broadcast, the moved
   racer appears on the lane LED in the next heat, and the coordinator's
   Undo button pulses on return.
4. **Cloud-sync verification**: after the round completes, run
   `./scripts/derbyvps.sh audit` from your dev box and confirm the
   "LAST CLOUD-SYNC" sentinel `last_sync_utc` is within a minute.
   `https://<host>/derbynet/device-status.php` should also show the
   current Pi-synced state.

### Pi-rehearsal pass criteria

- Real hardware completes a full round without manual time entry.
- Pull-forward triggers a visible staging announcement.
- Cloud sync continues during the rehearsal (one push per minute).

---

## Replay regression test (between rehearsals)

Capture the Pi rehearsal MQTT session:

```sh
mosquitto_sub -h 192.168.100.10 -p 1883 \\
  -u "$MQTT_USER" -P "$MQTT_PASS" \\
  -t 'derbynet/#' -v -F '{"t":%I,"topic":"%t","payload":%j}' \\
  > testing/captures/dress-rehearsal-$(date +%Y-%m-%d).jsonl
```

Replay it on the cloud twin's broker (or a local dev stack):

```sh
python testing/replay-real-race.py \\
  testing/captures/dress-rehearsal-YYYY-MM-DD.jsonl \\
  --broker localhost --user derbynet --pass "$MQTT_PASS"
```

Inspect the resulting RaceChart against the original — if they match, the
cloud stack is bit-equivalent for race-server behavior.

---

## Race-day go/no-go

Race day is **green** when:

1. Pull-forward shell tests pass: `./testing/test-pull-forward.sh https://<cloud>/derbynet`.
2. Pull-forward Puppeteer tests pass:
   `node testing/puppeteer/pull-forward-test.js http://localhost/derbynet`.
3. Both rehearsals (Part A and Part B) pass their criteria.
4. The replay regression test passes against the cloud twin.

If any one fails, do NOT ship that change to the Pi — roll back to the last
green commit on `master` and rerun.
