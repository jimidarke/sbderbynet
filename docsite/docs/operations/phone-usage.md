# Phone Usage

There is **no dedicated mobile UI**. SBDerbyNet phones are read-only consumers of standard web pages — never a substitute for hardware, never a control surface during the event.

---

## What works fine on a phone

- **Public-facing pages** on the cloud twin (when sync is current):
    - `/derbynet/index.php` — landing
    - `/derbynet/results.php` — results browsing
    - `/derbynet/standings.php` — class standings
    - `/derbynet/kiosk.php?name=now-racing` — view-only kiosk render
    - `/derbynet/kiosk-public.php`, `/derbynet/public-displays.php` — spectator view (in-progress on this branch)
- Coordinator pages **viewed** on phone (functional, but not laid out for small screens — use a tablet or laptop for actual coordination).

---

## What does NOT work, by design

- **`/derbynet/virtual/*` pages.** Browser virtual hardware is desktop-only. Auto-finish requires `setInterval` to keep firing while the tab is foregrounded; phones aggressively background tabs and the broker connection drops. There is no mobile-touch finish-timer interface and there will not be one.

    If a real timer dies on race day, the fallback is the existing DNF / manual time-entry path on the coordinator page — not a phone.

- **MQTT-over-WebSocket** from a phone browser. The `/mqtt` route through Caddy is reserved for desktop-only virtual hardware on the cloud twin.

---

## Why the strict separation

- **Race-day reliability**: if a phone is allowed to act as a finish timer, someone *will* try it during a real event, and the result variance from human button-press timing makes results unfair.
- **Security model**: the `virtual-device` MQTT credential only exists in cloud mode and grants publish on `derbynet/device/B_*`. Putting that cred on a phone (which can't be reliably wiped after the event) widens the leak surface for no race-day benefit.

---

## Phones in the press box / spectator area

Encourage spectators and parents to:

1. Open the public spectator URL of the cloud twin.
2. Bookmark `/results.php` for live results.
3. Avoid the coordinator URL — it works but the desktop layout is awkward.

That is the entire intended scope of phone use.
