# Phone Usage

This file documents what works on a phone browser. **There is no dedicated
mobile UI.** SBDerbyNet phones are read-only consumers of the standard web
pages — never a substitute for hardware, never a control surface during the
event.

## What works fine on a phone

- **Spectator pages** on `live.soapboxderbynet.com` (the recommended
  destination for race-day spectators — see `docs/PUBLIC_STATS.md`):
  - `/<TOKEN>/schedule.html` — current-round lineup with the active heat
    highlighted
  - `/<TOKEN>/recent.html` — last 3 completed heats with placements/times
  - Pages are prerendered HTML behind a per-event obfuscated token,
    distributed by QR. Refresh every ~30 s; pinny-only (no PII).
- **Public-facing pages** on the cloud twin (when sync is current and the
  spectator pages above aren't sufficient):
  - `/derbynet/index.php` — landing
  - `/derbynet/results.php` — results browsing
  - `/derbynet/standings.php` — class standings
  - `/derbynet/kiosk.php?name=now-racing` — view-only kiosk render
- Coordinator role pages **viewed** on phone (functional but not laid out
  for small screens — use a tablet or laptop for actual coordination).

## What does NOT work on a phone, by design

- **`/derbynet/virtual/*` pages.** The browser virtual hardware is
  desktop-only. Auto-finish requires `setInterval` to keep firing while the
  tab is foregrounded; phones aggressively background tabs and the broker
  connection drops. There is no mobile-touch finish-timer interface and
  there will not be one. If a real timer dies on race day, the fallback is
  the existing DNF / manual time-entry path on the coordinator page — not a
  phone.
- **MQTT-over-WebSocket** from a phone browser. The `/mqtt` route through
  Caddy is reserved for the desktop-only virtual hardware pages on the
  cloud twin.

## Why the strict separation

- Race-day reliability: if a phone is allowed to act as a finish timer,
  someone *will* try it during a real event, and the result variance from
  human button-press timing makes results unfair.
- Security model: the `virtual-device` MQTT credentials only exist in cloud
  mode and grant publish on `derbynet/device/B_*`. Putting that cred on a
  phone (which can't be reliably wiped after the event) widens the leak
  surface for no race-day benefit.

## Phones in the press box / spectator area

Encourage spectators and parents to:
1. Scan the printed QR for the race-day spectator URL
   (`live.soapboxderbynet.com/<TOKEN>/schedule.html`).
2. If they want depth, bookmark `/derbynet/results.php` on the cloud twin.
3. Avoid the coordinator URL — it works but the desktop layout is awkward.

That is the entire intended scope of phone use.
