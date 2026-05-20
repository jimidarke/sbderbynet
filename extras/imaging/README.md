# SBDerbyNet SD-Card Image Pipeline

This directory builds the three pre-customized Raspberry Pi OS images that ship to race day:

| Image | Hardware | Network | What's baked in |
|-------|----------|---------|-----------------|
| `sbderbynet-derbypi-<sha>.img.xz` | Pi 3 B+ | eth0 static `192.168.100.10` | nginx + PHP + SQLite, mosquitto, rsyncd, rsyslog UDP 514, derbyrace, full `website/` + `extras/soapbox/infra/`, DS3231 RTC overlay, 15-min DB backup timer |
| `sbderbynet-finishtimer-<sha>.img.xz` | **Pi Zero 2 W** | wlan0 DHCP | python3-rpi.gpio, paho-mqtt, snapshot of finishtimer code, wpa_supplicant (creds from CI secrets), DIP-switch identity reader, `finishtimer.service` |
| `sbderbynet-derbydisplay-<sha>.img.xz` | Pi 3 B+ | eth0 DHCP | Chromium kiosk with **respawn wrapper**, xinit + openbox + unclutter, derby-pull from central, derbydisplay.service for MQTT telemetry |

Every image inherits the universal hardening layer in `_common/` (hardware watchdog, journald volatile, log2ram 64M, masked `apt-daily*` timers, `noatime,commit=600` on root, pinned Python venv, America/Edmonton TZ).

Source-of-truth design doc: [`docs/SD_CARD_RECOVERY.md`](../../docs/SD_CARD_RECOVERY.md).

## How a build works

The CI workflow uses [**dtcooper/rpi-image-modifier**](https://github.com/dtcooper/rpi-image-modifier) — a GitHub Action that mounts a Raspberry Pi OS base image, runs a script inside it (chroot + QEMU), then auto-shrinks (PiShrink) and xz-compresses the result.

1. `.github/workflows/build-images.yml` checks out the repo, reads the pinned base image from `extras/imaging/base-image.lock` (currently `raspios_lite_arm64-2026-04-21`), downloads it, and verifies SHA256.
2. For each role in `[derbypi, finishtimer, derbydisplay]` (matrix-parallel):
   - The action mounts the base image and mounts the repo at `/mounted-github-repo/`.
   - Our `run:` script `rsync`s `_common/rootfs/` + `<role>/rootfs/` into the image, then invokes `_common/customize.sh <role>` followed by `<role>/customize.sh`.
   - Those scripts do all `apt install`s, render `wpa_supplicant.conf` from secrets (finishtimer only), bake repo content (`website/` + `extras/soapbox/infra/`) into the derbypi image, seed the SQLite skeleton with WAL+NORMAL pragmas.
3. The action auto-shrinks the root partition, xz-compresses, and emits `sbderbynet-<role>-<sha>.img.xz` plus a SHA256.
4. On `release` event the artifacts attach to the GitHub Release; on push to master they're 30-day-retained CI artifacts.

## Local build (no GitHub Actions)

You need a Linux host with Docker (the action uses a container internally). Easiest reproduction is the action itself, invoked via [`nektos/act`](https://github.com/nektos/act):

```bash
brew install act          # or: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
act push -j build -W .github/workflows/build-images.yml \
    --matrix role:derbypi \
    -s WIFI_SSID=DerbyNet -s WIFI_PASSWORD=xxx
```

For a from-scratch local build without Docker, you can adapt the action's approach with `qemu-user-static` + a loop-mounted image. But CI iteration is fast enough that local builds aren't usually necessary.

```bash
# Reference variables (used in the workflow)
URL=$(jq -r .url extras/imaging/base-image.lock)
SHA=$(jq -r .sha256 extras/imaging/base-image.lock)
FN=$(jq -r .filename extras/imaging/base-image.lock)
curl -fL "$URL" -o "$FN"
echo "$SHA  $FN" | sha256sum -c

# Strongly recommended: just use `act` (above) instead of this — the action
# handles QEMU + chroot + shrink + xz uniformly. Building "by hand" requires
# replicating the action's loop-mount + binfmt setup. See action source:
# https://github.com/dtcooper/rpi-image-modifier
```

(Easier: trigger the workflow with `gh workflow run build-sd-images`.)

## Refreshing the USB stick on Windows

```powershell
# Replace v1.0.0 with the desired release tag (or use 'latest')
gh release download v1.0.0 --repo jimidarke/sbderbynet `
    --dir E:\images\ --pattern '*.img.xz' --pattern '*.sha256'
```

Then verify against the SHA file and label the cards.

## Updating the pinned base image

When upstream RPi OS ships a new release worth picking up:

1. Browse https://downloads.raspberrypi.com/raspios_lite_arm64/images/
2. Pick the newest folder, grab the `.img.xz` URL and its `.sha256`
3. Edit `base-image.lock` (`url`, `sha256`, `version`, `filename`)
4. Push; CI will rebuild all 3 images against the new base. If something breaks (e.g., upstream renamed a package), iterate the per-role `customize.sh`.

## Where things go on the running Pi

| Pi path | What lives there | Comes from |
|---------|------------------|------------|
| `/etc/derby-role` | `derbypi` / `finishtimer` / `derbydisplay` | `_common/customize.sh` |
| `/etc/derby-image-sha` | git SHA of the build | role `customize.sh` |
| `/etc/derby-image-built-at` | ISO-8601 build timestamp | role `customize.sh` |
| `/boot/firmware/derbyid.txt` | per-device ID (operator-editable on Windows) | `_common/rootfs/` |
| `/usr/local/sbin/derby-firstboot.sh` | dispatch, runs once | `_common/rootfs/` |
| `/usr/local/sbin/derby-firstboot-<role>.sh` | role-specific first-boot hook | role `rootfs/` |
| `/var/lib/infra/.venv/` | pinned Python venv | `_common/customize.sh` |
| `/var/lib/infra/` (derbypi only) | infra dirs served via rsync | baked from `extras/soapbox/infra/` |
| `/var/www/html/derbynet/` (derbypi only) | PHP app | baked from `website/` |
| `/var/lib/derbynet/skeleton.sqlite3` (derbypi only) | WAL+NORMAL skeleton | `derbypi/customize.sh` |
| `/var/lib/derbynet/backups/auto-*.sqlite3` (derbypi only) | every-15-min SQLite snapshots | `derbynet-backup.service` |
| `/opt/derbynet/` (satellites) | refreshed from central via `derby-pull.service` | rsync at boot |

## Smoke-test checklist after a fresh build

Run before tagging a release:

1. `sbderbynet-derbypi-<sha>.img.xz` → flash → boot → `curl http://192.168.100.10/derbynet/` returns 200 in <3 min. `cat /etc/derby-role` says `derbypi`. `sqlite3 /var/lib/derbynet/skeleton.sqlite3 'PRAGMA journal_mode'` says `wal`. `systemctl is-active mosquitto nginx php*-fpm derbyrace rsync rsyslog` shows all active.
2. `sbderbynet-finishtimer-<sha>.img.xz` → flash → boot → `wpa_cli status` (over serial) shows `wpa_state=COMPLETED`. `cat /boot/firmware/derbyid.txt` is `FT00<n>` matching DIP. `mosquitto_sub -h 192.168.100.10 -v -t 'derbynet/device/+/telemetry'` on the central Pi shows it within 60s.
3. `sbderbynet-derbydisplay-<sha>.img.xz` → flash → boot → kiosk page within 60s. Pull power, plug back in — Chromium respawns.
4. DB restore: drop a known-good `derbynet-snapshot-test-2026.sqlite3.gz` + `.sha256` into `bootfs:\restore\` before booting the derbypi card. After boot, `ls /var/lib/derbynet/2026/test/`. Now corrupt the gz, flash again — firstboot should refuse and leave the DB empty (check `/var/log/derby-firstboot.log`).
5. WiFi rotation: change `WIFI_PASSWORD` secret in GitHub, re-run the workflow, flash a fresh finishtimer. New card associates; old cards do not (until re-flashed).
