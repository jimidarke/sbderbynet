# SBDerbyNet SD-Card Image Pipeline

This directory builds the three pre-customized Raspberry Pi OS images that ship to race day:

| Image | Hardware | Network | What's baked in |
|-------|----------|---------|-----------------|
| `sbderbynet-derbypi-<sha>.img.xz` | Pi 3 B+ (arm64) | eth0 static `192.168.100.10` (WiFi disabled) | nginx + PHP + SQLite, mosquitto, rsyncd, rsyslog UDP 514, derbyrace, full `website/` + `extras/soapbox/infra/`, DS3231 RTC overlay, 15-min DB backup timer |
| `sbderbynet-finishtimer-<sha>.img.xz` | **Pi Zero W V1.1** (armhf) | wlan0 DHCP | python3-rpi.gpio, paho-mqtt, snapshot of finishtimer code, wpa_supplicant (creds from CI secrets), rsyslog UDP forward to .10, DIP-switch identity reader, `finishtimer.service`. Built on `raspios_lite_armhf` (Trixie, Debian 13) — BCM2835/ARMv6 cannot run a 64-bit kernel. |
| `sbderbynet-derbydisplay-<sha>.img.xz` | Pi 3 B+ (arm64) | eth0 DHCP (primary) + wlan0 DHCP (fallback, RouteMetric=2000) | Chromium kiosk with **respawn wrapper**, xinit + openbox + unclutter, wpa_supplicant (same creds as finishtimer), rsyslog UDP forward to .10, derby-pull from central, derbydisplay.service for MQTT telemetry |

Every image inherits the universal hardening layer in `_common/` (hardware watchdog, journald volatile, log2ram 64M from Trixie apt, masked `apt-daily*` timers, `noatime,commit=600` on root, pinned Python venv, America/Edmonton TZ, fleet SSH key baked for derbynet+root, sshd locked to key-only auth, SSH host keys regenerated per-card on first boot).

Source-of-truth design doc: [`docs/SD_CARD_RECOVERY.md`](../../docs/SD_CARD_RECOVERY.md).

## How a build works

The CI workflow uses [**dtcooper/rpi-image-modifier**](https://github.com/dtcooper/rpi-image-modifier) — a GitHub Action that mounts a Raspberry Pi OS base image, runs a script inside it (chroot + QEMU), then auto-shrinks (PiShrink) and xz-compresses the result.

1. `.github/workflows/build-images.yml` checks out the repo, reads the pinned base image for each `(role, arch)` from `extras/imaging/base-image.lock`, downloads it, and verifies SHA256. The lock is arch-keyed (`arm64`, `armhf`); derbypi + derbydisplay take arm64 (Pi 3 B+), finishtimer takes armhf (Pi Zero W V1.1 — BCM2835/ARMv6 can't run 64-bit).
2. For each `(role, arch)` in the matrix (3 builds, parallel):
   - The action mounts the base image and mounts the repo at `/mounted-github-repo/`.
   - Our `run:` script `rsync`s `_common/rootfs/` + `<role>/rootfs/` into the image, then invokes `_common/customize.sh <role>` followed by `<role>/customize.sh`.
   - Those scripts do all `apt install`s, render `wpa_supplicant.conf` from secrets (finishtimer + derbydisplay), bake repo content (`website/` + `extras/soapbox/infra/`) into the derbypi image, seed the SQLite skeleton with WAL+NORMAL pragmas.
3. The action auto-shrinks the root partition, xz-compresses, and emits `sbderbynet-<role>-<sha>.img.xz` plus a SHA256. One file per role — single arch each.
4. On `release` event the artifacts attach to the GitHub Release; on tag push (minor/major bumps only — `vX.Y.0`) they're 30-day-retained CI artifacts.

The workflow only runs on **minor/major version tag pushes** (`v*.*.0`), `release: created`, or manual `workflow_dispatch`. Routine commits to `master` do **not** build — a 24-minute build per push was too noisy. To cut a fresh image set, tag a minor bump:

```bash
# previous tag was v0.9.20 — bump to v0.10.0 to trigger images
git tag -a v0.10.0 -m "build images: <reason>"
git push origin v0.10.0
```

To get a one-off build without bumping a tag: from the GitHub Actions UI, click "Run workflow" on the `build-sd-images` workflow (or `gh workflow run build-sd-images`).

## Local build (no GitHub Actions)

You need a Linux host with Docker (the action uses a container internally). Easiest reproduction is the action itself, invoked via [`nektos/act`](https://github.com/nektos/act):

```bash
brew install act          # or: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
act push -j build -W .github/workflows/build-images.yml \
    --matrix role:derbypi \
    -s WIFI_SSID=DerbyNet -s WIFI_PASSWORD=xxx -s CONSOLE_PASSWORD=changeme
```

Secrets the build requires: `WIFI_SSID`, `WIFI_PASSWORD` (finishtimer/derbydisplay
WiFi), and `CONSOLE_PASSWORD` (break-glass console login on the `derbynet`
account, **all roles** — the build fails fast if it's unset). SSH stays
key-only; the console password is the fallback for when WiFi/the fleet key is
unavailable.

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

1. Browse https://downloads.raspberrypi.com/raspios_lite_arm64/images/ (and `raspios_lite_armhf/images/` for the finishtimer Pi Zero W V1.1)
2. Pick the newest folder, grab the `.img.xz` URL and its `.sha256`
3. Edit the matching arch block in `base-image.lock` (`url`, `sha256`, `version`, `filename`)
4. Push; CI will rebuild all 3 images against the new base(s). If something breaks (e.g., upstream renamed a package), iterate the per-role `customize.sh`.

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
4b. **Break-glass console login + no rename wizard (all 3 roles):** the uid-1000 user is still `derbynet` — `getent passwd 1000` shows `derbynet`, NOT `newname`/an operator name — confirming `userconfig.service` is masked (`systemctl is-enabled userconfig.service` → `masked`) and the wizard never clobbered it. At the **physical console/serial**, `derbynet` + the `CONSOLE_PASSWORD` value logs in (and `sudo -n true` works). Catches the 2026-05-29 lockout (wizard renamed `derbynet`→`newname` + no console password existed).
4c. **WiFi regulatory domain (finishtimer/derbydisplay):** `iw reg get` reports `country CA` and `rfkill list wifi` shows **not** soft/hard-blocked; `grep cfg80211.ieee80211_regdom /boot/firmware/cmdline.txt` is present. Catches the 2026-05-29 failure where a valid PSK still never associated because the radio stayed rfkill-blocked (regdomain unset).
4a. firstboot ran (all 3 roles): `systemctl is-enabled derby-firstboot.service` reports `disabled` (the service self-disables after success). On finishtimer, `cat /boot/firmware/derbyid.txt` should be `FT00<lane>` matching the DIP switches even when the operator left it as `CHANGE-ME` — confirms the `ConditionFirstBoot` regression is gone.
5. Host-key uniqueness: flash two cards of the same role; `ssh-keyscan` against each returns different host keys (`regenerate_ssh_host_keys.service` ran on first boot and self-disabled).
6. Log forwarding (satellites → derbypi): on the central Pi, `sudo tail -F /var/log/derbynet.log`; on a satellite, `logger -t derby-smoke "$(date -Iseconds)"` — the line should appear on the central tail within seconds.
7. DB restore: drop a known-good `derbynet-snapshot-test-2026.sqlite3.gz` + `.sha256` into `bootfs:\restore\` before booting the derbypi card. After boot, `ls /var/lib/derbynet/2026/test/`. Now corrupt the gz, flash again — firstboot should refuse and leave the DB empty (check `/var/log/derby-firstboot.log`).
8. WiFi rotation: change `WIFI_PASSWORD` secret in GitHub, re-run the workflow, flash a fresh finishtimer (or derbydisplay). New card associates; old cards do not (until re-flashed).
9. Satellite WiFi actually associates: on a flashed finishtimer/derbydisplay, `iw dev wlan0 link` shows `Connected to <bssid>` and `wpa_cli status` reports `wpa_state=COMPLETED`. From derbypi, `ping <satellite-dhcp-ip>` succeeds within 60s of power-on. Catches the `wpa_supplicant.conf` vs `wpa_supplicant-wlan0.conf` path mismatch (silent failure: device powers on, never joins WiFi).
10. Finishtimer service actually runs: on a flashed finishtimer, `systemctl status finishtimer` shows `active (running)` (not `auto-restart`), `journalctl -u finishtimer` shows no `ModuleNotFoundError` or `[Errno 2] No such file or directory`. From derbypi, `mosquitto_sub -h 192.168.100.10 -v -t 'derbynet/device/FT00+/telemetry'` shows `battery_raw` is a non-`None` integer — proves I2C is up and the MCP3421 ADC is being read.

## Lessons learned (2026-05 bring-up)

The first batch of flashed images (commits up to `dc43a7fc`) shipped with four interlocking bugs that only surfaced once we live-tested a fresh derbypi card on 2026-05-21. Then on the same day, the first live finishtimer flashes (FT001/FT002/FT003) surfaced four more. All nine are now guarded against by the smoke-test checklist above, but the patterns are worth remembering:

1. **rsync `--delete` and `_common`-created artifacts.** `_common/customize.sh` ran first and created `/var/lib/infra/.venv/`; `derbypi/customize.sh` then ran `rsync --delete extras/soapbox/infra/ → /var/lib/infra/`, which has no `.venv/` in the source, so the venv contents got wiped. Result: `derbyrace.service` 203/EXEC crash-loop. Fix: dropped the venv entirely (apt-installed deps are good enough; `/usr/bin/python3` is the stable interpreter). Lesson: if you ever reintroduce a build-time artifact under `/var/lib/infra/`, either `--exclude` it from the role rsync or place it under `/opt/derbyvenv/` outside the rsync target.

2. **App default fallbacks vs. baked broker bind.** `derbyRace.py` defaults `MQTT_BROKER` to `localhost`, but mosquitto binds only to `192.168.100.10:1883` (defense in depth from the audit). The satellite services (`finishtimer.service`, `derbydisplay.service`) had `Environment="MQTT_BROKER=192.168.100.10"` but the central `derbyrace.service` didn't — silently broken on every fresh flash. Fix: explicit env line on all three. Lesson: never rely on a Python default for cross-host networking on a frozen appliance image; pin the address in the unit file.

3. **`ConditionFirstBoot=no` means the opposite of what it sounds like.** Reads naturally as "no special condition," actually means "only run if this is NOT the first boot." So `derby-firstboot.service` was skipped on every fresh flash — including the finishtimer DIP-switch lane auto-detection. Fix: removed the condition; the script's `systemctl disable` at the end already enforces single-shot. Lesson: when a script self-disables, don't add a redundant systemd condition layer.

4. **Pi OS Lite Trixie's placeholder UID-1000 user has shell `/usr/sbin/nologin`.** `usermod -l placeholder derbynet` renames but inherits the shell. SSH then refuses with "This account is currently not available." Fix: unconditional `usermod -s /bin/bash derbynet` after the create/rename block. Lesson: when reusing a placeholder user, reset *every* attribute that matters — shell, gecos, home — don't trust inheritance.

5. **`WatchdogSec=` without app-side sd_notify is a guaranteed crash loop.** Both `derbyrace.service` and `finishtimer.service` declared `WatchdogSec=60s`, but neither `derbyRace.py` nor `finishtimer.py` calls `sdnotify.SystemdNotifier().notify("WATCHDOG=1")`. systemd SIGABRTs the process every minute, `Restart=always` brings it back, the cycle repeats. Surfaced only after the first four bugs were fixed and the apps could actually reach steady state. Fix: removed `WatchdogSec` from both units; `Restart=always` already covers genuine crashes. Lesson: `WatchdogSec` is a *contract* between the unit and the app — only add it after the app actually sends keepalives.

6. **`wpa_supplicant@wlan0.service` reads a different conf path than we wrote.** Our customize.sh rendered the WiFi conf to `/etc/wpa_supplicant/wpa_supplicant.conf` (the path the *non-template* `wpa_supplicant.service` uses). But we *enabled* the template instance `wpa_supplicant@wlan0.service` whose `ExecStart` is `wpa_supplicant -c/etc/wpa_supplicant/wpa_supplicant-%I.conf -i%I` — i.e. it expects `wpa_supplicant-wlan0.conf`. With the conf at the wrong path, the service starts, fails to open the file, exits, and the interface never associates. Silent failure: device powers on, never appears on the LAN. Fix: rename target to `wpa_supplicant-wlan0.conf` in both `finishtimer/customize.sh` and `derbydisplay/customize.sh`; also `systemctl disable wpa_supplicant.service` so the auto-enabled DBUS instance from the base image doesn't compete. Lesson: when picking a systemd template unit, **read its `ExecStart`** before deciding where to write its config — never assume the file paths are the same as the non-template variant.

7. **Build-time rsync layout vs. `derby-pull` layout were inconsistent.** `finishtimer/customize.sh` rsynced `extras/soapbox/infra/finishtimer/files/` → `/opt/derbynet/` (flattening the `files/` subdir), so at boot `/opt/derbynet/finishtimer.py` existed. But `derby-pull.service` rsyncs `rsync://192.168.100.10/derbynet/finishtimer/` → `/opt/derbynet/` with `--delete` (i.e. one level higher, preserving `files/` as a subdir). On first boot, derby-pull rewrites `/opt/derbynet/` and now `finishtimer.py` lives at `/opt/derbynet/files/finishtimer.py`. The service's `ExecStart=/usr/bin/python3 /opt/derbynet/finishtimer.py` then fails with status=2/INVALIDARGUMENT. Fix: `ExecStart=/usr/bin/python3 /opt/derbynet/files/finishtimer.py` to match the post-pull layout. Lesson: when two different processes (build-time staging vs. runtime pull) populate the same directory, **diff the resulting trees** — a `--delete` rsync that wins the second race silently rearranges everything.

8. **Missing Python deps not in apt.** `finishtimer/customize.sh` apt-installed `python3-rpi.gpio` but the running code imports `tm1637` (7-segment LED driver) and `smbus2` (I²C abstraction). Both are pure-Python; `smbus2` is in Debian Trixie main as `python3-smbus2` but `tm1637` is PyPI-only (package name `raspberrypi-tm1637`). On first boot, finishtimer.py fails with `ModuleNotFoundError: No module named 'tm1637'`. Fix: extend apt list with `python3-smbus2 python3-zeroconf`; add `pip3 install --break-system-packages --no-cache-dir raspberrypi-tm1637` for the PyPI-only one. Lesson: when adopting upstream Python code on an air-gapped appliance, **import-survey it** and pre-install every dep at image-build time (no satellite has internet at race day).

9. **I²C bus not enabled on finishtimer images.** `derbynetPCBv1.py:getBatteryPercent()` reads the MCP3421 ADC at `/dev/i2c-1`. Our `derbypi/customize.sh` writes `dtparam=i2c_arm=on` (for the DS3231 RTC), but `finishtimer/customize.sh` didn't — so `/dev/i2c-1` was absent, the ADC read returned `None`, and `sum([None, 0, …])` raised `TypeError` in a daemon thread, killing the whole process. Fix: add `dtparam=i2c_arm=on` to `/boot/firmware/config.txt` and `i2c-dev` to `/etc/modules-load.d/i2c.conf` in `finishtimer/customize.sh`. Requires a reboot to take effect. Lesson: hardware overlays are per-role — if a role's app code touches `/dev/i2c-*` or `/dev/spi-*` or any GPIO peripheral beyond plain pins, the matching `dtparam=`/`dtoverlay=` line **must** be in that role's customize.sh.

All nine had a common signature: **the failure was invisible at build time** (the CI build went green) **and only showed up on a live Pi**. Notably, bugs 6–9 only became visible *after* bugs 1–5 were fixed, in a strict cascade — each fix unblocked the next failure mode. The smoke-test checklist above (especially items 9 and 10) is the gate that catches them now; run it on a real card of every role before tagging a release.

### Second wave (2026-05-29 finishtimer bring-up)

A v0.10.0 finishtimer card was completely unreachable. Three more build-invisible bugs, now guarded by checklist items 4b/4c:

10. **The Pi OS first-boot wizard renamed our appliance user.** Pi OS Lite Trixie ships `userconfig.service` enabled; on first boot it renames the uid-1000 user to an operator-entered name and calls `/bin/cancel-rename` (which is what enables `getty@tty1`). We created `derbynet` in the chroot but never masked the wizard — so on first boot it silently renamed `derbynet`→`newname` and left it locked. That killed **console login** (locked password) **and** `ssh derbynet@` (no such user; the fleet key lives under `/home/derbynet`, which moved). Fix in `_common/customize.sh`: `systemctl mask userconfig.service` + `systemctl enable getty@tty1.service` (we must re-enable the getty userconfig would have). Lesson: a pre-baked uid-1000 user does **not** suppress the Trixie wizard — you must mask it explicitly, and re-enable the getty it owned.

11. **No break-glass console login existed.** `derbynet` had no password and sshd is key-only, so the *only* access path was the fleet SSH key over WiFi. When WiFi was down (bug 12) there was no way in at all — console or remote. Fix: bake a console password on `derbynet` from the `CONSOLE_PASSWORD` secret (`_common/customize.sh`); SSH stays key-only so it's console-only. Lesson: a key-only appliance needs a physical-console fallback for the day the network won't come up.

12. **WiFi radio stayed rfkill-blocked — `country=` in wpa_supplicant.conf is not enough.** The conf had `country=CA` and a valid PSK, but on Pi OS the wlan0 radio is soft-blocked by rfkill until the kernel **cfg80211 regdomain** is set. The known-good legacy card set it via `cfg80211.ieee80211_regdom=CA` on the kernel cmdline; the image dropped that step (a comment even claimed it was unnecessary), so wlan0 never associated. Fix in `finishtimer/customize.sh`: append `cfg80211.ieee80211_regdom=CA` to `cmdline.txt` + write `/etc/default/crda`. Lesson: setting the WiFi country requires the **regdomain**, not just a line in wpa_supplicant.conf — verify with `iw reg get` and `rfkill list wifi`, not by reading the config file.

Also hardened in the same pass: WiFi conf is now generated directly from `wpa_passphrase` (no `sed`-template substitution that an `&`/`\` in the SSID could corrupt, and which had been rewriting comment lines), with a build-time validation gate asserting a real `ssid=`/64-hex `psk=` landed; and a `systemd-networkd-wait-online` timeout drop-in so a slow/missing link can't stall boot for the full ~120 s.
