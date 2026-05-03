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

- VPS reachable. `wget https://<host>/derbynet/health` returns OK.
- `installer/docker-cloud/.env` populated:
  - `DERBYNET_CLOUD_MODE=public`
  - `MQTT_USER`, `MQTT_PASS`
  - `VIRTUAL_MQTT_USER=virtual-device`
  - `VIRTUAL_MQTT_PASS=<value>` (or let `setup-mqtt-auth.sh` generate one)
- Cloud DB is current. Confirm with:
  ```sh
  ssh deploy@<vps> 'cat /opt/derbynet/production/data/.cloud_readonly'
  ```
  and check `last_sync_utc` is within a few minutes.

### Step-by-step

1. **Sign in as RaceCoordinator** on the cloud twin (`/derbynet/login.php`).
2. **Open virtual control panel**: `/derbynet/virtual/index.php`.
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
6. **Trigger a pull-forward**:
   - Drop a racer scheduled for an upcoming heat.
   - Walk through the modal, accept with announce.
   - Verify the staging announcement appears on `/derbynet/kiosk.php?name=now-racing`.
7. **Run the full suite for the round** (auto-mode on all finish timers).
8. **Inspect**:
   - `/derbynet/device-status.php` — virtual devices appear with `B_` hwids.
   - `/derbynet/results.php` — finish times look plausible.
   - Race server logs (`docker logs derbynet-race-server`) — no errors.

### Cloud-twin pass criteria

- All virtual devices stayed connected for the duration.
- Pull-forward modal worked, announcement reached the kiosk.
- Round completed without manual intervention beyond clicking GO/finish.
- No `B_` hwid leaked into a "must be online to race" decision (the race
  server should treat them like any other timer over MQTT).

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
3. **Pull-forward live**: mid-event, simulate a dropout. Confirm the
   physical staging-area kiosk shows the broadcast and the moved racer
   appears on the lane LED in the next heat.
4. **Cloud-sync verification**: after the round completes, on the cloud
   twin verify `/derbynet/device-status.php` shows current Pi data and the
   sentinel `last_sync_utc` is within a minute.

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
