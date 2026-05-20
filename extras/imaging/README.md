# SBDerbyNet SD-Card Image Pipeline

This directory builds the three pre-customized Raspberry Pi OS images that ship to race day:

| Image | Hardware | Network | What's baked in |
|-------|----------|---------|-----------------|
| `sbderbynet-derbypi-<sha>.img.xz` | Pi 3 B+ | eth0 static `192.168.100.10` | nginx + PHP + SQLite, mosquitto, rsyncd, rsyslog UDP 514, derbyrace, full `website/` + `extras/soapbox/infra/`, DS3231 RTC overlay, 15-min DB backup timer |
| `sbderbynet-finishtimer-<sha>.img.xz` | **Pi Zero 2 W** | wlan0 DHCP | python3-rpi.gpio, paho-mqtt, snapshot of finishtimer code, wpa_supplicant (creds from CI secrets), DIP-switch identity reader, `finishtimer.service` |
| `sbderbynet-derbydisplay-<sha>.img.xz` | Pi 3 B+ | eth0 DHCP | Chromium kiosk with **respawn wrapper**, xinit + openbox + unclutter, derby-pull from central, derbydisplay.service for MQTT telemetry |

Every image inherits the universal hardening layer in `sdm/_common/` (hardware watchdog, journald volatile, log2ram 64M, masked `apt-daily*` timers, `noatime,commit=600` on root, pinned Python venv, America/Edmonton TZ).

The plan that produced this directory: `/home/jimi/.claude/plans/lets-go-through-carefully-purrfect-beacon.md` (also tracked in `docs/SD_CARD_RECOVERY.md`).

## How a build works

1. CI (`.github/workflows/build-images.yml`) checks out the repo and fetches the upstream base image pinned in `sdm/base-image.lock` (`raspios_lite_arm64-2026-04-21`).
2. SHA256 is verified — fail-fast on tampering.
3. `sdm` mounts the image, registers QEMU binfmt, copies `_common/rootfs/` + `<role>/rootfs/` into the image's filesystem.
4. `sdm` chroots in and runs `_common/customize.sh <role>` → `<role>/customize.sh`. These do all `apt install`s, render `wpa_supplicant.conf` from secrets (finishtimer only), bake repo content (website/infra) into the derbypi image, seed the SQLite skeleton with WAL+NORMAL pragmas.
5. `sdm --shrink` cuts unused space from the root partition.
6. xz -6 compresses. SHA256 sidecar generated.
7. On `release` event, the artifacts attach to the GitHub Release; on `push` to master, they're 30-day-retained CI artifacts.

## Local build (no GitHub Actions)

You need a Linux host with `qemu-user-static`, `binfmt-support`, and the `sdm` install:

```bash
# Once
sudo apt-get install qemu-user-static binfmt-support xz-utils jq
curl -fsSL https://raw.githubusercontent.com/gitbls/sdm/master/EZsdmInstaller | sudo bash

# Every time
cd /path/to/sbderbynet
URL=$(jq -r .url extras/imaging/sdm/base-image.lock)
SHA=$(jq -r .sha256 extras/imaging/sdm/base-image.lock)
FN=$(jq -r .filename extras/imaging/sdm/base-image.lock)
curl -fL "$URL" -o "$FN"
echo "$SHA  $FN" | sha256sum -c
xz -d "$FN"
cp "${FN%.xz}" build.img

# Build, e.g., the derbypi image
mkdir -p /tmp/build-context
rsync -a --exclude='.git' ./ /tmp/build-context/
# (set WIFI_SSID/WIFI_PASSWORD if building finishtimer)
sudo /usr/local/sdm/sdm --customize \
    --plugin copyfile:from=extras/imaging/sdm/_common/rootfs:to=/ \
    --plugin copyfile:from=extras/imaging/sdm/derbypi/rootfs:to=/ \
    --plugin copyfile:from=/tmp/build-context:to=/build-context \
    --plugin runscript:script=/path/to/derby-build.sh \
    --no-rsyncbackup --batch build.img

sudo /usr/local/sdm/sdm --shrink build.img
xz -T0 -6 build.img
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
3. Edit `sdm/base-image.lock` (`url`, `sha256`, `version`, `filename`)
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
