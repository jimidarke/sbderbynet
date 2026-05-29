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
| derbypi (central) | Pi 3 B+ (arm64) | Ethernet only (WiFi intentionally disabled) | static `192.168.100.10` | `sbderbynet-derbypi-<sha>.img.xz` |
| finishtimer (per lane) | Pi Zero W V1.1 (armhf) | WiFi only | DHCP | `sbderbynet-finishtimer-<sha>.img.xz` |
| derbydisplay (kiosk) | Pi 3 B+ (arm64) | Ethernet (primary) + WiFi fallback | DHCP | `sbderbynet-derbydisplay-<sha>.img.xz` |
| starttimer | ESP32 | WiFi | — | not SD-card-based (OTA from web app) |

WiFi credentials (`WIFI_SSID` / `WIFI_PASSWORD` repo secrets) are baked into the finishtimer and derbydisplay images at build time. PSK is hashed via `wpa_passphrase` so the plaintext password never lands on the SD card. On derbydisplay, wlan0 has `RouteMetric=2000` so it stays dormant when eth0 is up — the WiFi is purely a recovery path if the cable fails.

The finishtimer image is armhf-only because the BCM2835 (Pi Zero W V1.1) cannot run a 64-bit kernel. The fleet is standardized on V1.1 boards; the Pi Zero 2 W arm64 variant was retired 2026-05.

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

## Boot troubleshooting (bench / recovery)

### A finishtimer (Pi Zero W) that won't boot, reboots itself, or hangs on `systemd-networkd-wait-online`

Before suspecting the image or WiFi, **check the power path — including HDMI.**

- **HDMI parasitic power (confirmed 2026-05-29).** A monitor's HDMI cable connected to a Pi Zero W can back-feed enough parasitic current into the board to prevent it from powering down/up cleanly. Symptoms seen: card boots once fine, then on reboot it spontaneously resets, takes a very long time on the `systemd-networkd-wait-online.service` job, and never re-joins WiFi (so it looks "up" on the console but is unreachable on the LAN / silent on MQTT). **Fix: unplug the HDMI when power-cycling.** The Zero W only initialises HDMI output if the cable is present at power-on anyway, so for headless bench testing leave it disconnected and diagnose over SSH / the MQTT broker instead.
- A flaky/under-spec 5V supply or a marginal USB cable produces the same class of symptoms. `vcgencmd get_throttled` (≠ `0x0`) flags under-voltage *if* you can reach a shell.

### LED flash codes ≠ always the image
A repeating green-ACT flash pattern (e.g. 3 flashes) is a **firmware-stage** failure (before the Linux kernel runs), so it is *not* an armv6-vs-arm64 kernel mismatch. On the Zero W it usually means a **bad/incompatible SD card or a bad write** — `dd` reports success without verifying what landed. Confirmed 2026-05-29: a 3-blink card failed while a different card flashed with the *same* image booted fine. Re-flash to a known-good card (and read back / hash-verify the write) before chasing image bugs.

### Break-glass console login
When WiFi (and therefore the fleet SSH key) is unavailable, log in at the **physical console/serial** with the appliance account and the `CONSOLE_PASSWORD` secret value:

```
login: derbynet
password: <CONSOLE_PASSWORD>   # GitHub Actions repo secret; ask the maintainer
```

`derbynet` has passwordless `sudo`. SSH stays key-only (`PasswordAuthentication no`), so this password only works at the console — it is the deliberate fallback for the day the network won't come up. (Images from before 2026-05-29 have **no** console password and were unreachable in this situation; see imaging README "Second wave" lessons.)

### Booted to the console but no WiFi / unreachable on the LAN
If the Pi reaches a login prompt but never appears on the broker:

- **Regulatory domain (most common, fixed in image ≥ 2026-05-29).** On Pi OS the wlan0 radio is rfkill-blocked until the kernel cfg80211 regdomain is set; `country=CA` in `wpa_supplicant.conf` alone is **not** enough. Check `iw reg get` (want `country CA`) and `rfkill list wifi` (must not be blocked). Quick manual unblock: `sudo rfkill unblock wifi && sudo iw reg set CA`. Permanent fix is `cfg80211.ieee80211_regdom=CA` on the kernel cmdline (now baked into the finishtimer image).
- Then check association: `wpa_cli -i wlan0 status` → `wpa_state=COMPLETED`, and `systemctl status wpa_supplicant@wlan0 systemd-networkd`.

### First-boot user wizard / "I can't log in as derbynet"
If the console shows the stock Pi OS "new user" wizard, or `getent passwd 1000` shows a name other than `derbynet`, the image predates the `userconfig.service` mask (≥ 2026-05-29) — the wizard renamed the appliance user (e.g. `derbynet`→`newname`) and broke both console and `ssh derbynet@`. Reflash with a current image; do not try to complete the wizard.
