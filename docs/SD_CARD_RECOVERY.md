# SD-Card Recovery & Image Pipeline

> **Race-day TL;DR:** the central Pi at `192.168.100.10` and the satellite Pis (finishtimer × 4, derbydisplay × N) are appliances. Every Pi role has a pre-built SD-card image that you flash from a Windows laptop using Pi Imager + the USB stick in the gear bag. **Target: under 30 minutes** from "SD card died" to "Pi back online and racing." No SSH, no Ansible, no internet required.

This doc is the **index** for the image-based deployment story. The pieces live in these three places:

| What you want | Where it lives |
|---------------|----------------|
| **Race-day operator recovery instructions** | [`extras/imaging/INSTRUCTIONS.md`](../extras/imaging/INSTRUCTIONS.md) — 1-page sheet, source for the USB-stick PDF |
| **Developer build pipeline + smoke-test checklist** | [`extras/imaging/README.md`](../extras/imaging/README.md) — `dtcooper/rpi-image-modifier` workflow, local builds via `act`, base-image pinning, USB-stick refresh |
| **CI workflow** | [`.github/workflows/build-images.yml`](../.github/workflows/build-images.yml) — produces 3 `.img.xz` per push, publishes to GitHub Releases on tag |
| **Audit that motivated this work** | [`docs/RACE_SYSTEM_AUDIT_2026-05.md`](RACE_SYSTEM_AUDIT_2026-05.md) — drift findings, hardening recommendations |

## Hardware footprint

| Role | Board | Network | IP | Image |
|------|-------|---------|----|----|
| derbypi (central) | Pi 3 B+ | Ethernet only (WiFi intentionally disabled) | static `192.168.100.10` | `sbderbynet-derbypi-<sha>.img.xz` |
| finishtimer (per lane) | Pi Zero 2 W | WiFi only | DHCP | `sbderbynet-finishtimer-<sha>.img.xz` |
| derbydisplay (kiosk) | Pi 3 B+ | Ethernet (primary) + WiFi fallback | DHCP | `sbderbynet-derbydisplay-<sha>.img.xz` |
| starttimer | ESP32 | WiFi | — | not SD-card-based (OTA from web app) |

WiFi credentials (`WIFI_SSID` / `WIFI_PASSWORD` repo secrets) are baked into the finishtimer and derbydisplay images at build time. PSK is hashed via `wpa_passphrase` so the plaintext password never lands on the SD card. On derbydisplay, wlan0 has `RouteMetric=2000` so it stays dormant when eth0 is up — the WiFi is purely a recovery path if the cable fails.

## §Time-sync reality (referenced from satellite setup.sh files)

The central Pi does **not** run an NTP server. `systemd-timesyncd` is client-only on every Pi; race timing measures elapsed time (GPIO ticks) rather than wall-clock, so log-timestamp drift is the only impact and rsyslog on the central Pi re-stamps on arrival. Satellite `setup.sh` files used to write `NTP=192.168.100.10` into their `/etc/systemd/timesyncd.conf`; those blocks were removed in May 2026.

If you ever need LAN NTP back (e.g. a future device that uses wall-clock for race scoring), install `chrony` on the central Pi with `allow 192.168.100.0/24` and add the NTP line back to the satellite setup scripts.

## What got demoted

- `extras/derbypi/bootstrap.sh` — **expert/development path only**. Race-day recovery uses the image pipeline. Don't `curl | sudo bash` from `master` in production.
- `extras/derbypi/ansible/` — reference for what's inside the derbypi image. Source-of-truth is now `extras/imaging/derbypi/`.
- `extras/soapbox/infra/deployment/sdcard/` — deleted. The capture-from-running-Pi pipeline (`createImage.sh`, `deployImage.sh`, vendored `pishrink.sh`) is replaced by reproducible builds from git.

## Verification commands

The full smoke-test checklist is in [`extras/imaging/README.md`](../extras/imaging/README.md#smoke-test-checklist-after-a-fresh-build). On a running Pi you can confirm provenance with:

```bash
cat /etc/derby-role             # derbypi / finishtimer / derbydisplay
cat /etc/derby-image-sha        # git SHA the image was built from
cat /etc/derby-image-built-at   # ISO-8601 build timestamp
```
