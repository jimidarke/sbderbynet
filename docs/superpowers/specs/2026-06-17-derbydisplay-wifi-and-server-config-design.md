# DerbyDisplay: WiFi fix + configurable server address — design

**Date:** 2026-06-17
**Status:** Approved (brainstorming) → ready for implementation plan
**Scope:** `extras/imaging/derbydisplay/` (kiosk image only)

## Background / motivation

Live bring-up of a freshly flashed derbydisplay card (v0.13.0, sha `98a7006`) on
2026-06-17 surfaced three distinct issues. Two are in scope here; one is hardware.

1. **WiFi rfkill soft-block (IN SCOPE).** On the running kiosk: `phy0 soft=1`,
   no `cfg80211` regdomain on `/proc/cmdline`, and `NetworkManager` **active**.
   The derbydisplay image never received the WiFi fixes the finishtimer image got
   in v0.12.0/v0.13.0. WiFi is the kiosk's *fallback* path (eth0 is primary via
   `RouteMetric=2000`), so the gap stayed invisible until tested cable-out.
2. **Hardcoded server `192.168.100.10` (IN SCOPE).** The kiosk dials `.10` in
   four places (browser URL + readiness probe in `.xinitrc`, `MQTT_BROKER` in
   `derbydisplay.service`, rsync source in `derby-pull.service`). Off the race
   LAN it can never reach its server — confirmed: `curl http://192.168.100.10/derbynet/`
   → timeout, `http_code=000`. The kiosk shows `error.png`, then Chromium's
   "site can't be reached".
3. **Under-voltage / reboot instability (OUT OF SCOPE — hardware).**
   `vcgencmd get_throttled` → `0x50000` (under-voltage + throttling occurred);
   `dmesg` shows repeated `Undervoltage detected!`. Fix is a proper 5V/3A PSU +
   short/thick cable, not an image change. Prerequisite for stable bench testing.

## Goals

- wlan0 comes up unblocked (regdomain CA), nothing re-blocks it, eth→wifi
  fallback actually works. No change when eth is up.
- The server the kiosk talks to is operator-configurable from a Windows-editable
  file on the FAT bootfs, with a safe default that preserves current behavior.

## Non-goals (YAGNI)

- Extending the server knob to finishtimer/derbypi MQTT hardcoding (they work on
  the race LAN today).
- Deleting the legacy `infra/derbydisplay/kiosk.sh` + `setup.sh` duplicate (dead
  at boot; leave for a separate cleanup).
- Any power/under-voltage remediation (hardware).

## Section 1 — WiFi fix (port finishtimer §2b to derbydisplay)

Edit `extras/imaging/derbydisplay/customize.sh`:
- Add `rfkill` to the apt install list (the drop-in calls `/usr/sbin/rfkill`).
- New "WiFi regulatory domain + rfkill" block mirroring `finishtimer/customize.sh`:
  - Append `cfg80211.ieee80211_regdom=CA` to `/boot/firmware/cmdline.txt`
    (idempotent, single-line `sed`).
  - `echo 'REGDOMAIN=CA' > /etc/default/crda`.
  - `systemctl disable NetworkManager.service` + `systemctl mask NetworkManager.service`.
  - `systemctl mask systemd-rfkill.service systemd-rfkill.socket`.

New file `extras/imaging/derbydisplay/rootfs/etc/systemd/system/wpa_supplicant@wlan0.service.d/10-rfkill-unblock.conf`
— verbatim copy of the finishtimer drop-in:
```
[Service]
ExecStartPre=-/usr/sbin/rfkill unblock wifi
```

## Section 2 — Configurable server address (Approach B: two plaintext files)

### Config files (shipped as commented templates via `derbydisplay/rootfs/boot/firmware/`)
- `derby-server.txt` — host/IP. Default `192.168.100.10`. Drives browser URL,
  MQTT broker, and rsync source.
- `derby-url.txt` — optional. A complete browser URL used **verbatim** (no MAC
  appended). Empty by default.

Both files: consumers read **the first non-comment, non-blank line, stripped of
CR/whitespace**. CRLF-safe (Windows Notepad). Lines starting with `#` are comments.

### Shared helper `/usr/local/sbin/derby-server-host` (shipped via rootfs, mode 0755)
Prints the resolved host: first non-comment line of `/boot/firmware/derby-server.txt`,
`\r`/whitespace stripped; falls back to `192.168.100.10` if the file is missing,
empty, or comment-only. Pure shell, no dependencies. **This is the unit under test.**

Reference behavior:
```sh
read_first_line() {  # file -> first non-comment non-blank line, CR/ws stripped
  [ -f "$1" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}; line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    case "$line" in ''|\#*) continue;; *) printf '%s\n' "$line"; return 0;; esac
  done < "$1"
  return 1
}
host=$(read_first_line /boot/firmware/derby-server.txt) || host=192.168.100.10
[ -n "$host" ] || host=192.168.100.10
printf '%s\n' "$host"
```

### Consumer changes
1. **`.xinitrc`** (`derbydisplay/rootfs/home/kioskuser/.xinitrc`):
   - `HOST=$(/usr/local/sbin/derby-server-host)`.
   - `OVERRIDE` = first non-comment line of `/boot/firmware/derby-url.txt` (else empty).
   - If `OVERRIDE` non-empty: `FINAL_URL="$OVERRIDE"` (verbatim, **no MAC**); skip
     the readiness probe; show splash briefly, then launch Chromium at `FINAL_URL`.
   - Else: `BASE_URL="http://$HOST/derbynet/kiosk.php?address="`; probe
     `http://$HOST/derbynet/`; launch `"${BASE_URL}${MAC}"`.
   - Remove the old `/opt/derbynet/url.txt` block (superseded; it was clobbered by
     `derby-pull --delete` every boot anyway).
2. **`derbydisplay.service`** (`derbydisplay/rootfs/etc/systemd/system/derbydisplay.service`):
   - `ExecStart=/usr/local/sbin/derbydisplay-run` (new wrapper, shipped via rootfs):
     `export MQTT_BROKER="$(/usr/local/sbin/derby-server-host)"; exec /usr/bin/python3 /opt/derbynet/derbydisplay.py`.
   - Remove the hardcoded `Environment="MQTT_BROKER=192.168.100.10"`.
   - `derbydisplay.py` is untouched.
3. **`derby-pull.service`** (`derbydisplay/rootfs/etc/systemd/system/derby-pull.service`):
   - `ExecStart=/bin/sh -c 'H="$(/usr/local/sbin/derby-server-host)"; rsync -az --delete --timeout=10 "rsync://$H/derbynet/derbydisplay/" /opt/derbynet/ || true'`.

### Fallback semantics
Any config file missing/blank/comment-only → host defaults to `192.168.100.10`,
no URL override → **existing race-LAN cards behave exactly as today**.

## Section 3 — Testing & rollout

### Local (no Pi)
TDD the `derby-server-host` helper first. Cases: valid IP; CRLF (Windows) file;
blank file; comment-only file; missing file; leading/trailing whitespace; comment
line then value. Assert correct host or `.10` default each time. Shell-based test
(bats or a plain assert script under `extras/imaging/derbydisplay/tests/`).

### Rebuild
Build runs only on `vX.Y.0` tags / `release` / `workflow_dispatch`. Latest tag is
`v0.14.1`; cut **`v0.15.0`** (or `gh workflow run build-sd-images`). Then download
the `sbderbynet-derbydisplay-<sha>` artifact, verify `sha256` + `xz -t`, flash,
**read-back hash verify**.

### On-Pi smoke tests
- **WiFi:** `rfkill list` wlan0 not blocked; `iw reg get` = `country CA`;
  `grep cfg80211 /proc/cmdline`; `systemctl is-enabled NetworkManager` = `masked`;
  `systemd-rfkill` masked; pull eth cable → rejoins via wlan0 ≤30s,
  `wpa_cli -i wlan0 status` = `COMPLETED`.
- **Server config:** default → `.10` everywhere (unchanged); edit `derby-server.txt`
  to a reachable IP → browser/pull/MQTT follow; full URL in `derby-url.txt` →
  Chromium loads it verbatim; CRLF-saved file still parses; blank → `.10`.

### Rollout sequence
branch → helper + tests (TDD) → WiFi port + config templates + drop-in + wrapper +
3 consumer edits → local tests green → merge → tag `v0.15.0` → CI → verify + flash
+ read-back → on-Pi smoke tests. (Same build refreshes derbypi/finishtimer images —
unchanged logic, new SHA, harmless.)
