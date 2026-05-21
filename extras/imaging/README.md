# SBDerbyNet SD-Card Image Pipeline

This directory builds the three pre-customized Raspberry Pi OS images that ship to race day:

| Image | Hardware | Network | What's baked in |
|-------|----------|---------|-----------------|
| `sbderbynet-derbypi-<sha>.img.xz` | Pi 3 B+ (arm64) | eth0 static `192.168.100.10` (WiFi disabled) | nginx + PHP + SQLite, mosquitto, rsyncd, rsyslog UDP 514, derbyrace, full `website/` + `extras/soapbox/infra/`, DS3231 RTC overlay, 15-min DB backup timer |
| `sbderbynet-finishtimer-arm64-<sha>.img.xz` | **Pi Zero 2 W** (arm64) | wlan0 DHCP | python3-rpi.gpio, paho-mqtt, snapshot of finishtimer code, wpa_supplicant (creds from CI secrets), rsyslog UDP forward to .10, DIP-switch identity reader, `finishtimer.service` |
| `sbderbynet-finishtimer-armhf-<sha>.img.xz` | **Pi Zero W V1.1** (armhf) | wlan0 DHCP | Same as the arm64 variant — same `_common` + `finishtimer/` customize scripts, just built on `raspios_lite_armhf` (Trixie, Debian 13) for the BCM2835/ARMv6 SoC that can't run 64-bit. Use when you're recovering one of the legacy Pi Zero W finishtimers. |
| `sbderbynet-derbydisplay-<sha>.img.xz` | Pi 3 B+ (arm64) | eth0 DHCP (primary) + wlan0 DHCP (fallback, RouteMetric=2000) | Chromium kiosk with **respawn wrapper**, xinit + openbox + unclutter, wpa_supplicant (same creds as finishtimer), rsyslog UDP forward to .10, derby-pull from central, derbydisplay.service for MQTT telemetry |

Every image inherits the universal hardening layer in `_common/` (hardware watchdog, journald volatile, log2ram 64M from Trixie apt, masked `apt-daily*` timers, `noatime,commit=600` on root, pinned Python venv, America/Edmonton TZ, fleet SSH key baked for derbynet+root, sshd locked to key-only auth, SSH host keys regenerated per-card on first boot).

Source-of-truth design doc: [`docs/SD_CARD_RECOVERY.md`](../../docs/SD_CARD_RECOVERY.md).

## How a build works

The CI workflow uses [**dtcooper/rpi-image-modifier**](https://github.com/dtcooper/rpi-image-modifier) — a GitHub Action that mounts a Raspberry Pi OS base image, runs a script inside it (chroot + QEMU), then auto-shrinks (PiShrink) and xz-compresses the result.

1. `.github/workflows/build-images.yml` checks out the repo, reads the pinned base image for each `(role, arch)` from `extras/imaging/base-image.lock`, downloads it, and verifies SHA256. The lock is arch-keyed (`arm64`, `armhf`); finishtimer is built twice (once per arch) for the two hardware generations, derbypi + derbydisplay are arm64-only.
2. For each `(role, arch)` in the matrix (4 builds, parallel):
   - The action mounts the base image and mounts the repo at `/mounted-github-repo/`.
   - Our `run:` script `rsync`s `_common/rootfs/` + `<role>/rootfs/` into the image, then invokes `_common/customize.sh <role>` followed by `<role>/customize.sh`.
   - Those scripts do all `apt install`s, render `wpa_supplicant.conf` from secrets (finishtimer + derbydisplay), bake repo content (`website/` + `extras/soapbox/infra/`) into the derbypi image, seed the SQLite skeleton with WAL+NORMAL pragmas.
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

1. Browse https://downloads.raspberrypi.com/raspios_lite_arm64/images/ (and `raspios_lite_armhf/images/` for the Pi Zero W variant)
2. Pick the newest folder, grab the `.img.xz` URL and its `.sha256`
3. Edit the matching arch block in `base-image.lock` (`url`, `sha256`, `version`, `filename`)
4. Push; CI will rebuild all 4 images against the new base(s). If something breaks (e.g., upstream renamed a package), iterate the per-role `customize.sh`.

Both arches are kept on the same Debian release line (currently Trixie / Debian 13) so that `customize.sh` can use the same apt package names. If they diverge, the per-arch `_common/customize.sh` apt list needs conditional logic.

## Where things go on the running Pi

| Pi path | What lives there | Comes from |
|---------|------------------|------------|
| `/etc/derby-role` | `derbypi` / `finishtimer` / `derbydisplay` | `_common/customize.sh` |
| `/etc/derby-image-sha` | git SHA of the build | role `customize.sh` |
| `/etc/derby-image-built-at` | ISO-8601 build timestamp | role `customize.sh` |
| `/boot/firmware/derbyid.txt` | per-device ID (operator-editable on Windows) | `_common/rootfs/` |
| `/usr/local/sbin/derby-firstboot.sh` | dispatch, runs once | `_common/rootfs/` |
| `/usr/local/sbin/derby-firstboot-<role>.sh` | role-specific first-boot hook | role `rootfs/` |
| `/var/lib/infra/` (derbypi only) | infra dirs served via rsync | baked from `extras/soapbox/infra/` |
| `/var/www/html/derbynet/` (derbypi only) | PHP app | baked from `website/` |
| `/var/lib/derbynet/skeleton.sqlite3` (derbypi only) | WAL+NORMAL skeleton | `derbypi/customize.sh` |
| `/var/lib/derbynet/backups/auto-*.sqlite3` (derbypi only) | every-15-min SQLite snapshots | `derbynet-backup.service` |
| `/opt/derbynet/` (satellites) | refreshed from central via `derby-pull.service` | rsync at boot |

## Smoke-test checklist after a fresh build

Run before tagging a release:

1. `sbderbynet-derbypi-<sha>.img.xz` → flash → boot → `curl http://192.168.100.10/derbynet/` returns 200 in <3 min. `cat /etc/derby-role` says `derbypi`. `sqlite3 /var/lib/derbynet/skeleton.sqlite3 'PRAGMA journal_mode'` says `wal`. `systemctl is-active mosquitto nginx php*-fpm derbyrace rsync rsyslog` shows all active. Critically, `systemctl show derbyrace -p SubState` reports `running` (not `auto-restart`) — confirms the venv-nuke regression is gone. `mosquitto_sub -h 192.168.100.10 -v -t 'derbynet/#' -W 3` should show `derbynet/status online` from derbyrace.
2. `sbderbynet-finishtimer-<sha>.img.xz` → flash → boot → `wpa_cli status` (over serial) shows `wpa_state=COMPLETED`. `cat /boot/firmware/derbyid.txt` is `FT00<n>` matching DIP. `mosquitto_sub -h 192.168.100.10 -v -t 'derbynet/device/+/telemetry'` on the central Pi shows it within 60s.
3. `sbderbynet-derbydisplay-<sha>.img.xz` → flash → boot → kiosk page within 60s. Pull power, plug back in — Chromium respawns. Confirm WiFi fallback: `ip route` shows eth0 at default metric and wlan0 metric 2000; pull eth0, the kiosk should remain reachable via wlan0 inside ~30s.
4. SSH hardening (all 3 roles): `ssh derbynet@<pi>` and `ssh root@<pi>` both succeed with the fleet key; `sshpass -p anything ssh root@<pi>` fails (password auth disabled); `sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin'` reports `no` and `prohibit-password`. Also `getent passwd derbynet` should show `/bin/bash`, not `/usr/sbin/nologin` — confirms the placeholder-shell fix is in place.
4a. firstboot ran (all 3 roles): `systemctl is-enabled derby-firstboot.service` reports `disabled` (the service self-disables after success). On finishtimer, `cat /boot/firmware/derbyid.txt` should be `FT00<lane>` matching the DIP switches even when the operator left it as `CHANGE-ME` — confirms the `ConditionFirstBoot` regression is gone.
5. Host-key uniqueness: flash two cards of the same role; `ssh-keyscan` against each returns different host keys (`regenerate_ssh_host_keys.service` ran on first boot and self-disabled).
6. Log forwarding (satellites → derbypi): on the central Pi, `sudo tail -F /var/log/derbynet.log`; on a satellite, `logger -t derby-smoke "$(date -Iseconds)"` — the line should appear on the central tail within seconds.
7. DB restore: drop a known-good `derbynet-snapshot-test-2026.sqlite3.gz` + `.sha256` into `bootfs:\restore\` before booting the derbypi card. After boot, `ls /var/lib/derbynet/2026/test/`. Now corrupt the gz, flash again — firstboot should refuse and leave the DB empty (check `/var/log/derby-firstboot.log`).
8. WiFi rotation: change `WIFI_PASSWORD` secret in GitHub, re-run the workflow, flash a fresh finishtimer (or derbydisplay). New card associates; old cards do not (until re-flashed).

## Lessons learned (2026-05 bring-up)

The first batch of flashed images (commits up to `dc43a7fc`) shipped with four interlocking bugs that only surfaced once we live-tested a fresh derbypi card on 2026-05-21. They're now guarded against by the smoke-test checklist above, but the patterns are worth remembering:

1. **rsync `--delete` and `_common`-created artifacts.** `_common/customize.sh` ran first and created `/var/lib/infra/.venv/`; `derbypi/customize.sh` then ran `rsync --delete extras/soapbox/infra/ → /var/lib/infra/`, which has no `.venv/` in the source, so the venv contents got wiped. Result: `derbyrace.service` 203/EXEC crash-loop. Fix: dropped the venv entirely (apt-installed deps are good enough; `/usr/bin/python3` is the stable interpreter). Lesson: if you ever reintroduce a build-time artifact under `/var/lib/infra/`, either `--exclude` it from the role rsync or place it under `/opt/derbyvenv/` outside the rsync target.

2. **App default fallbacks vs. baked broker bind.** `derbyRace.py` defaults `MQTT_BROKER` to `localhost`, but mosquitto binds only to `192.168.100.10:1883` (defense in depth from the audit). The satellite services (`finishtimer.service`, `derbydisplay.service`) had `Environment="MQTT_BROKER=192.168.100.10"` but the central `derbyrace.service` didn't — silently broken on every fresh flash. Fix: explicit env line on all three. Lesson: never rely on a Python default for cross-host networking on a frozen appliance image; pin the address in the unit file.

3. **`ConditionFirstBoot=no` means the opposite of what it sounds like.** Reads naturally as "no special condition," actually means "only run if this is NOT the first boot." So `derby-firstboot.service` was skipped on every fresh flash — including the finishtimer DIP-switch lane auto-detection. Fix: removed the condition; the script's `systemctl disable` at the end already enforces single-shot. Lesson: when a script self-disables, don't add a redundant systemd condition layer.

4. **Pi OS Lite Trixie's placeholder UID-1000 user has shell `/usr/sbin/nologin`.** `usermod -l placeholder derbynet` renames but inherits the shell. SSH then refuses with "This account is currently not available." Fix: unconditional `usermod -s /bin/bash derbynet` after the create/rename block. Lesson: when reusing a placeholder user, reset *every* attribute that matters — shell, gecos, home — don't trust inheritance.

5. **`WatchdogSec=` without app-side sd_notify is a guaranteed crash loop.** Both `derbyrace.service` and `finishtimer.service` declared `WatchdogSec=60s`, but neither `derbyRace.py` nor `finishtimer.py` calls `sdnotify.SystemdNotifier().notify("WATCHDOG=1")`. systemd SIGABRTs the process every minute, `Restart=always` brings it back, the cycle repeats. Surfaced only after the first four bugs were fixed and the apps could actually reach steady state. Fix: removed `WatchdogSec` from both units; `Restart=always` already covers genuine crashes. Lesson: `WatchdogSec` is a *contract* between the unit and the app — only add it after the app actually sends keepalives.

All five had a common signature: **the failure was invisible at build time** (the CI build went green) **and only showed up on a live Pi**. The smoke-test checklist above is the gate that catches them now; run it on a real card before tagging a release.
