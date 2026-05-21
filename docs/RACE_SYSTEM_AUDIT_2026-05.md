# Race System Audit — 2026-05-20

> **Update (post-audit):** The SD-card recovery + image-pipeline strategy planned in response to this audit has been built. See [`docs/SD_CARD_RECOVERY.md`](SD_CARD_RECOVERY.md). Several P0/P1 findings below (watchdog armed, SQLite WAL pragma, hardened journald, masked apt-daily, Chromium respawn, logrotate, MQTT clear-on-boot, derbypi NTP-server claim removed) are addressed by the baked image and so may already be resolved on any freshly-flashed Pi — verify on the live hardware before treating a specific bullet as still-true.
>
> **Second pass (2026-05-21):** image-pipeline tuned for SSH, WiFi, and logging consistency across all three roles:
> - **SSH hardening (all roles):** fleet `ed25519` key baked for `derbynet`, `root` (all roles), and `kioskuser` (derbydisplay). `/etc/ssh/sshd_config.d/10-derby-hardening.conf` sets `PasswordAuthentication=no` + `PermitRootLogin=prohibit-password`. Host keys are wiped at build and regenerated per-card on first boot by the shipped `regenerate_ssh_host_keys.service`. So §"No firewall installed" — SSH itself is now key-only.
> - **Satellite log forwarding:** `extras/imaging/{finishtimer,derbydisplay}/rootfs/etc/rsyslog.d/30-forward-derbynet.conf` ships `*.* @192.168.100.10:514` on every freshly-flashed satellite, matching the architecture described in [`docs/LOGGING.md`](LOGGING.md). Until this PR the doc described a path that the imaging pipeline didn't actually implement.
> - **WiFi fallback on derbydisplay:** wlan0 joins the same WiFi as finishtimer (CI-secret-rendered `wpa_supplicant.conf`) but at `RouteMetric=2000` so eth0 stays primary. Cable failure no longer dark-screens a kiosk.
> - **log2ram via apt:** `log2ram 1.7.2+ds-1` from Debian Trixie main replaced the hand-rolled tarball install.
>
> **Snapshot date:** 2026-05-20. **Scope:** the race-day Pi at `192.168.100.10`, plus the core racing system (engine, finish timers, kiosk displays, network). SaaSbox and LED signs intentionally out of scope.
>
> This is a **point-in-time snapshot**, not a living spec. Many findings will be resolved by follow-up PRs; check `git log` on `extras/derbypi/`, `extras/soapbox/infra/`, and `website/inc/` before treating any specific finding as still-true. The high-level patterns (Part 1: appliance drift; Part 2: latent race-engine bugs + appliance-grade hardening) age more slowly than the line-numbered details.
>
> **How this was produced:** static review of the repo + live read-only inspection of the Pi via SSH (`ssh derbypi`) + 2025–2026 web research on Pi-appliance / Mosquitto 2.x / SQLite WAL / ESP32+MQTT best practices.

---

# Part 1 — DerbyPi Reality Check

## 30-second verdict: 🟡 YELLOW

The Pi is **functionally alive** — HTTP, MQTT, rsync, syslog, and `derbyRace.py` are all running and serving the LAN. But it is **not the system the documentation describes**, and several critical promises from the Ansible playbook were never delivered:

1. **Ansible has never actually run here.** `ansible`, `ansible-pull`, `ansible-playbook` are not installed. `/opt/derbynet-repo` does not exist. The `ansible-pull.timer` does not exist. The whole self-update mechanism is fiction; somebody hand-installed pieces by copying out what the playbook *would* have produced.
2. **No LAN NTP server is running** (see §"Time-sync reality" below for the full story — short version: nothing on UDP 123, but in practice this is cosmetic, not race-blocking).
3. **`derbytime.service` is disabled and inactive.** Per `derbyTime.py`, this is the service that publishes wall-clock time over MQTT for clients — so devices have no MQTT-based time fanout either.
4. **Under-voltage is being reported right now.** `vcgencmd get_throttled = 0x50005` = currently under-voltage AND currently throttled, plus historical occurrences of both. Hardware/PSU problem.
5. **Hardware is a Pi 3 B+ (1GB micro-USB)**, not the Pi 4 the README mandates. That alone probably explains the under-voltage.
6. **Hostname is `raspberrypi`, not `derbynetpi`.** Doc/nginx server_name says `derbynetpi`. Functionally harmless on the LAN but symptomatic.

Nothing on this list will cause a race to fail today *if no devices need NTP and the PSU holds up* — but every one of them is something the doc says is there and isn't.

---

## Live audit summary

```
hostname:   raspberrypi         (docs say: derbynetpi)
model:      Pi 3 Model B+       (docs require: Pi 4)
os:         Debian 13 (trixie)  (docs say: RPi OS Lite 64-bit)
ip:         192.168.100.10/24   ✓ static, eth0 only
ram/load:   906Mi / 0.23        ✓ healthy
disk:       5.9G/29G root, 86M/510M /boot/firmware   ✓ healthy
temp:       52-54°C             ✓
THROTTLED:  0x50005             ✗ under-voltage now + throttled now
uptime:     ~45 min (rebooted today)
ansible:    NOT INSTALLED        ← biggest finding
```

## Role → Reality matrix

| Role | What it promises | Reality on the Pi | Verdict |
|------|------------------|-------------------|---------|
| `common` — hostname | set to `derbynetpi` | still `raspberrypi` (last set 2026-01-17) | ✗ DRIFT |
| `common` — disable avahi/triggerhappy/bluetooth/hciuart/wpa_supplicant | all stopped+disabled | `avahi-daemon` is **enabled+active**, listening UDP 5353 | ✗ DRIFT |
| `common` — disable WiFi/BT overlays | `dtoverlay=disable-wifi`, `disable-bt` in config.txt | ✓ both present | ✓ |
| `common` — `gpu_mem=16` | reduce GPU mem | ✗ NOT set in config.txt | ✗ DRIFT (minor) |
| `common` — derbynet user uid 1000, groups www-data+sudo | exists | ✓ | ✓ |
| `common` — journald 100M cap | `/etc/systemd/journald.conf.d/size.conf` | journal usage 3M, but cap file unverified (likely absent — manual install) | LIKELY DRIFT |
| `common` — install i2c-tools, vim, htop, jq | present | ✓ all installed | ✓ |
| `rtc` — DS3231 + `i2c-rtc,ds3231` overlay | `/dev/rtc0` driven by rtc-ds1307, 0x68 claimed (`UU`) | ✓ working; `dtoverlay=i2c-rtc,ds3231` in config.txt | ✓ |
| `rtc` — purge fake-hwclock | absent | ✓ not installed | ✓ |
| `rtc` — `hwclock-set` template | installed at `/lib/udev/hwclock-set` | unknown, `hwclock` CLI itself is missing (util-linux split package?) | LIKELY DRIFT |
| `ntp` — install chrony | running, port 123 served, `192.168.100.0/24` allowed | **chrony NOT installed.** `systemd-timesyncd` (client-only) is what's actually running. Nothing serving UDP 123 to the LAN. See §"Time-sync reality". | ✗ ROLE UN-REALIZED — but consumers don't depend on it the way the role implies |
| `logging` — rsyslog UDP 514 listener | `0.0.0.0:514` UDP | ✓ listening, `/etc/rsyslog.d/10-derbynet.conf` present, writes JSONL to `/var/log/derbynet/derby.jsonl` | ✓ |
| `mosquitto` — broker 1883, `derbynet.conf` | listening, `allow_anonymous true` | ✓ derbysvr connecting/disconnecting normally; retained traffic flowing | ✓ |
| `php` — php-fpm + extensions | active | ✓ but on **PHP 8.4** (Debian 13 default), docs hard-code 8.2 | ✓ functional / ✗ doc drift |
| `nginx` — site `derbynet` enabled, `default` removed | `derbynet` enabled, default removed | ✓ working, returns HTTP 200; `server_name derbynetpi 192.168.100.10` | ✓ |
| `python` — pip install paho-mqtt, requests, psutil, pytz, cryptography | system-wide via `--break-system-packages` | derbyRace.py is importing them and running — ✓ functionally | ✓ (origin unknown) |
| `derbynet` — clone `/opt/derbynet-repo`, sync website → `/var/www/html/derbynet`, sync infra → `/var/lib/infra` | repo cloned, files in sync | **`/opt/derbynet-repo` does not exist.** `/var/www/html/derbynet/*` last modified 2025-12-09. `/var/lib/infra/server` files dated Dec 7 2025. | ✗ STALE: ~5 months behind master |
| `derbynet` — `app -> server` compat symlink | symlink exists | ✓ `/var/lib/infra/app -> /var/lib/infra/server` | ✓ |
| `raceserver` — derbyrace enabled+running | enabled, active | ✓ running PID 7684, polling PHP API ~1Hz | ✓ |
| `raceserver` — derbytime enabled+running | enabled, active | **disabled + inactive.** Service file present. | ✗ MISSING |
| `rsync` — daemon, module `derbynet` → `/var/lib/infra` | listening 873, module exposed | ✓ | ✓ |
| `saasbox` — RSA-2048 keypair at `/var/lib/derbynet/keys/` | exists | **directory does not exist.** No SaaS device key. | ✗ MISSING |
| `bootstrap.sh` — install ansible-pull timer (30 min) | systemd timer running | **timer + service do not exist; ansible not installed at all** | ✗ MISSING |

Net: **8 of 12 roles only partially realized**; the self-update + NTP-server + SaaS-keypair guarantees are entirely absent.

## How this happened (working theory)

The mosquitto, nginx, rsyslog, derbyrace, derbytime service-file contents on the Pi are byte-for-byte the Ansible templates from this repo (e.g., nginx `server_name derbynetpi 192.168.100.10` is straight from `roles/nginx/templates/derbynet.conf.j2`). But ansible is not installed, `/opt/derbynet-repo` is gone, and `apt history` shows no record of `ansible` or `chrony` ever being installed.

Most likely: the playbook was run *somewhere else* (e.g., the cloud twin) and the **rendered config files plus `/var/lib/infra/` were rsync'd onto a fresh Debian 13 image manually**, treating the Pi as a one-shot snapshot rather than a self-managed appliance. That's fine until you need to update — at which point you have no path back.

## Time-sync reality (the "chrony / something else" question, fully unpacked)

There are **three distinct time concepts** in this codebase, and the docs/playbook/setup scripts conflate them:

1. **OS clock sync on the Pi itself** — what keeps `date` correct on `192.168.100.10`.
   - Documented intent: `chrony` (as both client and server).
   - Reality: `systemd-timesyncd` (Debian 13 trixie default). Client-only. The system clock is correct. Reasonably accurate.

2. **NTP service for downstream devices** — the Pi acting as the time server for finishtimer Pis, derbydisplay Pis, the starttimer ESP32, etc.
   - Documented intent: chrony with `allow 192.168.100.0/24` ([`roles/ntp/templates/chrony.conf.j2`](../extras/derbypi/ansible/roles/ntp/templates/chrony.conf.j2)).
   - Setup scripts on the consumers still assume this exists:
     - `extras/soapbox/infra/finishtimer/setup.sh:47` — `echo 'NTP=$SERVER_IP' >> /etc/systemd/timesyncd.conf`
     - `extras/soapbox/infra/finishtimer/ansible/roles/finishtimer/templates/timesyncd.conf.j2:3` — `NTP={{ finishtimer_ntp_server }}` (= `race_server_ip` = `192.168.100.10`)
     - `extras/soapbox/infra/derbydisplay/setup.sh:39` — same pattern
     - `extras/soapbox/infra/starttimer/src/main.py:73,184` — ESP32 calls `ntptime.host = 192.168.100.10; ntptime.settime()`
     - `extras/soapbox/infra/server/LOGGING.md:36-44` explicitly tells you to "Configure NTP client to sync from DerbyPi: 192.168.100.10"
   - Reality: nothing is listening on UDP 123 on the Pi. All of those clients silently fail to sync and keep whatever clock they had at boot.
   - **Functional impact: cosmetic, not race-blocking.**
     - Race timing measures elapsed time / GPIO ticks, not wall-clock. Lane times are correct.
     - rsyslog on the Pi re-stamps remote messages with `timegenerated` (`/etc/rsyslog.d/10-derbynet.conf`), so the unified JSONL has *Pi-time*, not device-time. Drift on the timer Pis is invisible.
     - The only thing that could break is on-device log timestamps, which nobody is reading directly.

3. **Race clock for UI / displays / LED signs** — broadcasting "the time right now" so kiosks and signs render it.
   - This is `extras/soapbox/infra/server/derbyTime.py` publishing on MQTT topic `derbynet/race/time` (or `derbynet/t/{slug}/race/time` in multi-tenant mode — `derbyTime.py:90,95`).
   - Reality on the Pi: `derbytime.service` is **disabled and inactive**. So nobody is publishing the race-clock fanout either.
   - This is probably what was meant by "we used something else for NTP" — but `derbyTime.py` is NOT an NTP replacement; it's a UI tool, and it isn't running.

**Net: three different "time" mechanisms documented, only one half-working** (the Pi's own clock sync via timesyncd). The chrony role is dead intent; the MQTT race-clock is dead intent; only the *appearance* of each survives in code/docs.

## Operational risks (race-day specific)

1. **PSU/cable under-voltage** — `0x50005` means the SoC is being clocked down *right now*. Race-time CPU spikes (lots of MQTT, PHP API polling) will be hit hardest. Replace the power supply with the official RPi 3 B+ 2.5A micro-USB or move to a Pi 4 + USB-C PSU.
2. **Time-sync inconsistency between Pi + downstream devices** — see §"Time-sync reality". Cosmetic, not blocking. Listed here so it's in one place: setup scripts on finishtimer/derbydisplay/starttimer all point at a non-existent NTP server on `192.168.100.10`.
3. **No MQTT race-clock fanout** — `derbytime.service` is disabled. Anything that subscribes to `derbynet/race/time` for UI rendering gets nothing. Confirm whether any kiosk/sign actually consumes this topic — if yes, enable derbytime; if no, the service can be deleted.
4. **No self-update at all** — every change since Dec 2025 (incl. the recent scheduler / kiosk / now-racing fixes in `git log`) is absent on the appliance. Race day = whatever was deployed in Dec 2025.
5. **SaaS keypair missing** — any code path that signs requests to the cloud twin / saasbox with `/var/lib/derbynet/keys/device.key` will fail.
6. **`apt-daily-upgrade.timer` is active**, but `unattended-upgrades` itself is not installed and there's no `20auto-upgrades` config — so the timer is a no-op (downloads metadata, doesn't apply). Not actually a risk; verify and remove the noise.
7. **No logrotate config for `/var/log/derbynet/` JSONL** — currently 9.1MB and growing. Nginx access logs ARE being rotated (~14 days retained, 36MB). The race-day JSONL will grow unboundedly until you rotate it.
8. **Stale `derbynet` console sessions** since Jan 17 on `tty1` + `seat0` — minor; reboots will clear, but indicates somebody plugged in a monitor/kb at one point and never logged out.
9. **Single boot ID since Jan 17 in journalctl** while `uptime` reports 45 min — RTC/clock skew at boot is confusing the journal. Functionally fine, just a tell for clock weirdness.
10. **avahi/mDNS is on** — chatty on a clean race LAN, and contradicts the "appliance" intent. If anything queries `derbynetpi.local`, it currently resolves to nothing because of the hostname drift.

## Dead weight / mismatch in the repo itself

These are issues with the `extras/derbypi/` source, independent of what's on the Pi:

- `DEPLOYMENT.md` hardcodes `php8.2-fpm` everywhere; Debian 13 ships 8.4.
- `README.md` says "Pi 4 (2GB+ RAM recommended)" but the playbook only asserts ARM architecture and your real Pi is a 3 B+.
- `bootstrap.sh` is a `curl | sudo bash` from `master` — no commit pin, no signature, no checksum. If the GitHub repo or DNS were tampered with, a fresh bootstrap would run arbitrary code.
- `playbook.yml` does the architecture assert with `ansible_architecture in ['aarch64', 'armv7l', 'armv6l']` — fine — but the post-task summary still references `chrony` and `derbytime` without confirming they're up. No `assert` or `command` post-tasks to fail loudly if a role silently no-op'd.
- `roles/python/tasks/main.yml` uses `--break-system-packages` against pip on Debian 13. That works but installs unpinned, system-wide. A venv at `/var/lib/infra/.venv` would be cleaner and pinned.
- `roles/raceserver/tasks/main.yml` calls a `Reload systemd daemon` task INSIDE `tasks/`, not handlers — minor smell, since it always runs even when service files haven't changed.
- `roles/derbynet/tasks/main.yml` runs `git ... force: yes` against the repo path; combined with `become_user: derbynet`, a clean checkout, fine — but no `version: HEAD` sanity check, and `synchronize` modules on each pull. Idempotent but heavy.
- `roles/common/tasks/main.yml` creates `/var/lib/derbynet` with `mode 0777` and its subdirectories the same. World-writable race data is intentional in DerbyNet but worth noting.
- `roles/saasbox/tasks/main.yml` references `generate_keypair.py` but I haven't verified the script handles a re-run (the `creates:` guard should be sufficient, just confirm `device.key` is the actual output path).
- `inventory/hosts.yml` says `derbynetpi` but `ansible_host: 192.168.100.10` — only useful for *remote* runs (which require ssh from a controller), conflicts with the `localhost / ansible_connection: local` design used by bootstrap. Pick one.
- No `roles/*/handlers/main.yml` checked for `Restart journald` referenced by `common` — playbook will warn or fail if missing. (Verify.)
- `bootstrap.sh` step 2 installs `ansible` (full) when `ansible-core` is sufficient and a fraction of the size.

## Prioritized cleanup plan (Part 1 — appliance drift)

### P0 — needed before next race
1. **Replace the PSU / Pi.** Either swap to a Pi 4 + official USB-C 3A PSU, or at minimum install a known-good 5V/2.5A micro-USB supply and a short, thick cable. After it's up, confirm `vcgencmd get_throttled` is `0x0`.
2. **Decide: re-run the playbook, or formalize the manual setup.**
   - Option A: on the existing Pi, install ansible + run `ansible-pull` once to true-up state. **Caveat:** the playbook currently still installs chrony, enables derbytime, and tries to generate the SaaS keypair — all things you may not actually want. Don't run as-is until §"Time-sync reality" decisions are made (see P1 #4 and #5).
   - Option B: throw away the SD card and re-bootstrap from scratch using `bootstrap.sh` on Debian 13. Cleanest but loses race data in `/var/lib/derbynet` unless backed up. Same caveat about the playbook's stale intent.
3. **Documentation discrepancy: hardware mismatch.** README says "Pi 4 (2GB+ RAM recommended)"; reality is Pi 3 B+ (1GB, micro-USB). Either update README to reflect Pi 3 B+ is supported, or commit to migrating to Pi 4. (See also #1.)

### P1 — discrepancies to resolve (decisions needed)
4. **`ntp` role: keep or delete?** See §"Time-sync reality". The role is wired up in the playbook but its setup-script consumers also need to be touched. Three possible paths:
   - Delete: drop `extras/derbypi/ansible/roles/ntp/`, strip `NTP=$SERVER_IP` lines from `extras/soapbox/infra/finishtimer/setup.sh:47`, `extras/soapbox/infra/finishtimer/ansible/roles/finishtimer/templates/timesyncd.conf.j2:3`, `extras/soapbox/infra/derbydisplay/setup.sh:39`. Update `extras/soapbox/infra/starttimer/src/main.py:73,184` to make `ntptime.settime()` failure non-fatal (it probably already is) or remove. Fix LOGGING.md's claim that the Pi serves NTP.
   - Keep as-is: actually run chrony per the playbook. UDP 123 will then be served and the existing consumer configs work as documented.
   - Document-only: leave code alone, just add a note in CLAUDE.md / README.md that LAN NTP is currently aspirational and not actually working. Defer the decision.
5. **`derbytime.service`: keep or delete?** Similar question — is anything actually subscribed to `derbynet/race/time`? Grep `website/` and the kiosk JS for that topic. If yes, enable the service. If no, delete the role + `.py` + `.service.j2`.
6. **`saasbox` role: still needed?** The Pi has no `/var/lib/derbynet/keys/`. Either the SaaS integration was abandoned, or the role just never ran. Check `extras/saasbox/` to see whether the cloud backend currently expects to be hit from this Pi.
7. **Documentation discrepancy: PHP version.** `DEPLOYMENT.md` hardcodes `php8.2-fpm`; Debian 13 trixie ships 8.4. Replace with `php8.4-fpm`, or with `php-fpm` (the unversioned alias).
8. **Documentation discrepancy: ansible-pull self-update is a promise the appliance doesn't keep.** README, CLAUDE.md, and bootstrap.sh all claim the Pi self-updates every 30 minutes. The current Pi has no ansible installed at all. Either re-enable ansible-pull or strip the claim from the docs.
9. **`/var/log/derbynet/` has no logrotate config** — currently 9.1M and growing. The rsyslog 10-derbynet.conf writes to `derby.jsonl` but nothing rotates it. Pattern off `/etc/logrotate.d/rsyslog`; size 10M, rotate 14, compress, copytruncate.
10. **`bootstrap.sh` is `curl | sudo bash` from `master`** — unpinned. At minimum pin to a tag/SHA; ideally have it self-verify against a published checksum.
11. **`playbook.yml` post-tasks just *print* service names** without asserting they're up. Add a post-run `assert` block so a future drift like the current one fails loudly instead of silently.

### P2 — quality of life
12. Convert `roles/python` to use a venv at `/var/lib/infra/.venv` with a `requirements.txt` so pin versions are reproducible.
13. Replace `apt-get install ansible` in `bootstrap.sh` with `ansible-core`; install only `community.general` and `ansible.posix` collections.
14. Consolidate `inventory/hosts.yml` — pick local-only OR remote-managed, not both.
15. Mask `apt-daily-upgrade.service` so race-day apt activity is impossible. (Currently the timer runs but unattended-upgrades isn't installed, so it's a no-op — still noise.)
16. Add a `monitoring` role: a tiny `/derbynet/health.php` endpoint or a systemd service that publishes Pi telemetry (`temp`, `throttled`, `df`, MQTT broker liveness) on MQTT `derbynet/server/health`. Today the only visibility is `derbyRace.py` POST'ing to `device-status-api.php`.
17. Disable / re-enable `common`'s avahi-daemon disable. Currently avahi is enabled+active, contrary to playbook intent.

### P3 — paper cuts
18. Delete the `app -> server` compat symlink and just point service `WorkingDirectory` at `/var/lib/infra/server` directly. The "compatibility" comment in `roles/derbynet/tasks/main.yml:67-72` no longer reflects a real consumer of the alternate path.
19. The `mosquitto` template comments-out `persistence true/persistence_location` but main `/etc/mosquitto/mosquitto.conf` enables persistence anyway. Document this or unify.
20. `DEPLOYMENT.md`'s troubleshooting tip about "duplicate persistence_location" is now stale guidance — the template doesn't do that anymore.
21. Stale console sessions: `pkill -KILL -u derbynet -t tty1 seat0` and re-image with auto-login disabled.
22. nginx `server_name derbynetpi 192.168.100.10` — `derbynetpi` resolves to nothing because the Pi hostname is still `raspberrypi`. Decide whether to fix the hostname (per playbook intent) or drop `derbynetpi` from server_name.

## Critical files referenced (Part 1)

- `extras/derbypi/bootstrap.sh` — entry point, needs pin + ansible-core
- `extras/derbypi/ansible/playbook.yml` — add post-run asserts
- `extras/derbypi/ansible/roles/common/tasks/main.yml` — hostname/avahi/journald drift source
- `extras/derbypi/ansible/roles/ntp/tasks/main.yml` — entirely un-realized; decide keep vs. delete
- `extras/derbypi/ansible/roles/raceserver/tasks/main.yml` — derbytime never enabled
- `extras/derbypi/ansible/roles/saasbox/tasks/main.yml` + `files/generate_keypair.py` — keypair never generated on this Pi
- `extras/derbypi/ansible/roles/python/tasks/main.yml` — system-wide pip → venv
- `extras/derbypi/DEPLOYMENT.md` + `README.md` — PHP version + hardware drift
- Pi: `/etc/systemd/system/derbytime.service` (exists, disabled)
- Pi: `/etc/logrotate.d/` (no derbynet entry)

---
---

# Part 2 — Deep audit of core racing system

Scope of this section: race engine, finish timers, kiosk displays, network. SaaSbox and LED signs explicitly skipped per request. Findings combine: (a) static review of `extras/soapbox/infra/{server,finishtimer,derbydisplay,starttimer}/`, (b) live read-only inspection of the Pi via SSH, (c) 2025–2026 web research on Pi-appliance / mosquitto / SQLite / ESP32+MQTT best practices.

## 30-second verdict (Part 2): 🟢 GREEN-with-asterisks

The race engine itself is **well-designed and currently healthy**. Coordinator poll responds in ~49ms, `derbyRace.py` is running cleanly, MQTT is flowing, the PHP API surface is coherent. Several latent issues exist (HTTP-timeout-not-set, finishtimer integer-second timestamps, SQLite not actually in WAL despite code claiming it is) but they are not race-stopping today.

The **operating-system layer** around the engine is not appliance-grade. No hardware watchdog armed, no firewall, journald persistent, idle console sessions from January, stale retained MQTT messages from the last test. None of these break the engine — they just mean a race-day failure has no automatic recovery path.

---

## §A. Race engine — live snapshot

### Coordinator poll API
- **Endpoint:** `http://localhost/derbynet/action.php?query=poll.coordinator`
- **Latency:** 10 sequential requests, mean 51ms, max 75ms. Fast.
- **Payload size:** ~6.5KB JSON per poll.
- **Polling rate:** hardcoded 1Hz in `derbyRace.py:1220` (`time.sleep(1)`). Coordinator UI ALSO polls at 1Hz per `docs/COORDINATOR_POLL_API.md:249`. Each kiosk page polls at its own cadence.
- **Top fields returned:**
  ```
  current-heat (dict-10), racers (list-3), timer-state (dict-13),
  replay-state (dict-5), heat-results (list-0), classes (list-3),
  rounds (list-6), race-integrity (dict-3), ...
  ```

### Live timer-state right now
```json
{ "lanes": 3, "state": 1, "message": "NOT CONNECTED",
  "timers": [
    { "lane": 1, "ready": false, "is_online": false, "seconds_ago": 10616232 },  // 122 days
    { "lane": 3, "ready": true,  "is_online": false, "seconds_ago": 2356 }       // ~40 min
  ],
  "timers_online": 0, "timers_required": 3,
  "health_status": "critical",
  "health_message": "WARNING: Only 0/3 timers online during active race!" }
```
- "Lane 2" missing from the array entirely.
- `health_status: "critical"` is being driven by the discrepancy between `timers_required=3` and `timers_online=0`. This is just stale data, not an actual error — there *is* no race active (DB has `NowRacingState=0`). But the alert text is misleading ("during active race!" while no race is active).

### Live DB state
```
RaceInfo:
  NowRacingState = 0          ← no race active ✓
  current_scene = 4
  timer_state = "1+1768696607++"      ← state=1, ts=Jan 17 2026
  racing_blocked_reason = "" ✓
```

The PHP API claim of `current-heat.now_racing = true` while `RaceInfo.NowRacingState = 0` is a **discrepancy**: `now_racing` (in `current-heat`) comes from `get_running_round()` which reflects "there is a round actively scheduled", not "the timer says a race is active". Two different concepts share the same name. Worth a doc note.

### SQLite reality vs. code claim
| Pragma | Code says (`derbydb.py:67-69`) | Live DB |
|---|---|---|
| `journal_mode` | `WAL` | **`delete`** ← drift |
| `synchronous` | `NORMAL` | **`FULL` (2)** ← drift |
| `busy_timeout` | `5000` | `5000` ✓ |
| `page_size` | (default) | 4096 |
| `cache_size` | (default) | -2000 (≈2MB) |

`derbydb.py` sets `journal_mode=WAL` on its own connection, but **journal_mode WAL is persistent** — once set, it stays. The fact that the live DB is in `delete` mode means **`derbydb.py` has never successfully written to this DB**. The only writer that's been touching it is **PHP via PDO**, which uses default rollback-journal mode.

**Why this matters:**
- PHP writes go through full fsync (synchronous=FULL) — extra SD wear, slower commits.
- Readers (`derbyRace.py`'s direct-write fast path) and writers (PHP) block each other under rollback-journal — WAL eliminates that.
- The race-results "fast path" via `derbydb.write_race_results()` (cited in `derbyRace.py:660`) has apparently never been exercised on this DB, since it would have flipped journal mode the first time.

### derbyRace.py process detail
```
PID 7684, user=root, RSS=33MB, %CPU=2.4 (averaged), ELAPSED=37min
CWD=/var/lib/infra/server
Python 3.13
```
Running cleanly. The "Main process exited code=1 / Scheduled restart" entry seen earlier was a normal one-off systemd restart, recovered on retry.

### MQTT live snapshot
- `derbynet/race/state` flips between `RACING` and `STAGING` every poll cycle — these are **retained messages from the last test event** plus `derbyRace.py` continuously republishing based on PHP poll. No actual race is happening; the engine is just driving LED commands for a phantom heat.
- Retained per-lane payloads from Jan 17 still visible: `Lane3 hwid DT54SIV0003`, `Lane1 hwid DT54SIV0001`. **The broker has never been cleared since the last test event.**
- `192.168.100.240` connects intermittently as `mqtt-explorer-cd2edc8a` — someone's MQTT debug GUI on a laptop, not a permanent device. Not a problem.

---

## §B. Findings from the three sub-system audits

### B1. Core racing engine (derbyRace.py + PHP + DB)

**Strengths**
- Thread-safety via `_race_lock` / `_heartbeat_lock` is real and consistent.
- Direct-SQLite write fast-path (`derbydb.write_race_results`) cuts result-recording latency vs. HTTP round-trip — *when it actually runs* (see WAL drift above).
- Coordinator poll is single-query-per-section, no N+1 in the racer list (`json-current-racers.inc:28` uses a JOIN, not per-racer SELECTs).
- Migrations run at startup (`update_schema.inc`), schema version 17.
- Clear LWT + retained pattern on `derbynet/status` is implemented (`derbyRace.py:183, 378`).

**Latent bugs (in approximate severity order)**

| # | Where | Description | Severity |
|---|---|---|---|
| 1 | `derbyapi.py:195` (verify) | `requests.get()` likely has **no explicit timeout**. PHP slow-response = engine hangs on `api.get_race_status()`. Matches the observed ~90s timeout cycles in `/var/log/derbynet/derby.jsonl`. | **HIGH** — root cause of the disconnect/reconnect noise |
| 2 | `derbyRace.py:399-403` | Lane count is mutated from API response while not RACING, but `lanesFinished` is not adjusted. Operator pulling a racer just before STAGING could leave a stale counter; `lanesFinished == lane_count` check on completion could fire early or hang. | Medium |
| 3 | `derbyRace.py:761` + `:1206-1207` | `checkRaceTimeout()` method still defined but never called (commented out per doc'd "DNF only from coordinator"). Dead code that misleads readers. | Low (cleanup) |
| 4 | `derbyRace.py:335-341` | `lane not in self.lane_times` check is unprotected before calling `laneFinish()` (which holds the lock). Two near-simultaneous MQTT messages would both pass the check, but the lock-holding inner double-check rejects the second. Sloppy but **not a correctness bug**. | Low |
| 5 | `derbyRace.py:414-421` | DNF detected by `finishtime_str >= "99.999"` string-parsed as float. Works today, would break if PHP started formatting with extra precision. Use a shared sentinel. | Low |
| 6 | `derbyRace.py:481-492` | `api.set_staging()` is called every poll that detects "stale state needs clearing", not only on actual state transitions. If `set_staging` is non-idempotent, this causes repeated side effects. Probably idempotent — but unverified. | Low |
| 7 | `website/sql/sqlite/schema.inc` | RaceChart has indexes on `roundid`, `heat`, `lane` individually; no compound `(roundid, heat)` index. Poll picks one, filters the other. Fine at current scale, would matter on a multi-event cloud DB. | Low |
| 8 | `derbylogger.py:106` | `DEFAULT_RSYSLOG_IP = '192.168.100.10'` hardcoded; should be env-var-overridable to match other components. | Cosmetic |

**Dead-code candidates**
- `derbyRace.py:761` `checkRaceTimeout()` — commented-out caller in main loop; remove the method too.
- `derbyTime.py` — service disabled on Pi; produces `derbynet/race/time` retained MQTT, but **no consumer found** in `website/`, `derbydisplay/`, `finishtimer/`, `starttimer/`. If nothing reads it, the role + service unit + script are all dead weight. **Recommend grepping the flutterapp / hlsfeed before deletion** in case the cloud side consumes it.
- `racing-state.inc:35-59` — large commented-out `check_registration_status()` function; replaced inline at `:63-99`. Remove.

### B2. Finish timer subsystem

**Strengths**
- Clean separation: `finishtimer.py` (entry), `derbynetPCBv1.py` (HW abstraction), `derbynet.py` (MQTT client w/ offline queue), `nodelogger.py` (rsyslog + local file).
- Lane identity is **hardware-immutable**: DIP switches on GPIO 6/13/19/26, HWID from `/boot/firmware/derbyid.txt`. No runtime ambiguity.
- LWT + retained `derbynet/device/{hwid}/status` is properly implemented.
- Telemetry-driven liveness on the central server (3-second offline threshold; `derbyRace.py:130`) is correct.
- Offline message queue at `/var/lib/derbynet/queue/` with exponential backoff in `derbynet.py:55-123`.

**Latent bugs**

| # | Where | Description | Severity |
|---|---|---|---|
| 1 | `finishtimer.py:122` | **`nowtime = int(time.time())`** — finish event has integer-second precision. Server computes race time with 3-decimal precision (`derbyRace.py:609`), but the underlying event has ±500ms bucket. Acceptable for casual heats; bad for tiebreakers. | **Medium — easy fix** |
| 2 | `finishtimer.py:136` | Finish state published with `retain=True, qos=2`. A retained stale `toggle=False` could mislead a server that reconnects mid-state. Telemetry should be retained; **state events should not be**. | Medium |
| 3 | `derbynetPCBv1.py:323` | `getBatteryPercent()` blocks 0.5s (10 samples × 50ms). Called whenever pinny re-renders with red LED. Could freeze the display refresh during low-battery condition. | Low |
| 4 | `derbynetPCBv1.py:150` | Toggle detection is GPIO polling every 100ms, not edge-triggered. Worst-case latency 100ms on top of integer-second timestamp. Use `GPIO.add_event_detect(... GPIO.FALLING)`. | Low (precision gain) |
| 5 | `derbynetPCBv1.py:109` | Hostname-default check uses literal `"DEFAULT"`. Modern RPi OS ships `"raspberrypi"`, so this check never matches on a fresh image; auto-rename never fires unless someone hand-set `DEFAULT`. | Low |
| 6 | Setup vs. Ansible | `setup.sh` and the Ansible role both configure NTP, power optimizations, packages. Ansible is declarative; setup.sh is the rescue script. Documented separation is correct; no drift. | OK |

**Dead-code candidates:** none found. Single canonical `finishtimer.py`, no abandoned MicroPython/ESP32 variant in this directory.

### B3. Kiosk display subsystem

**Strengths**
- 22 `.kiosk` pages; all are referenced by either DB scenes or fallback templates. No orphan pages.
- Central `css/kiosks.css` (258 lines) is loaded by every kiosk; design tokens defined; the recent commit `84384875` removed the `table-layout:fixed` regression and ellipsizes names.
- DIP-style automatic kiosk identity via MAC lookup → `Kiosks.page` table.
- Chromium launched fullscreen with `--kiosk --incognito` (no persistent cache).

**Drift vs. `docs/KIOSK_DESIGN.md`**
- 5 pages intentionally exempt from `body.kiosk` shell (columnar variants, slideshow trio, video) — documented exemption at `KIOSK_DESIGN.md:94-107`.
- Pending follow-ups (already listed in `KIOSK_DESIGN.md:112-123`):
  - `elimination-results.kiosk:50-51` — hardcoded gradient `#1e3c72, #2a5298`, should be `--brand` tokens.
  - `please-check-in.kiosk:54` — hardcoded `top: 128px`; should be `calc(var(--banner-h) + 4rem)`.
  - `slideshow.css` — `bottom: 10px/50px`, should be `vh` units.
  - `elimination-standings.kiosk` — same hardcoded colors as `elimination-results.kiosk` likely.

**Latent bugs**

| # | Where | Description | Severity |
|---|---|---|---|
| 1 | `derbydisplay.py:80, :85` | Subscribes to `derbynet/device/{hwid}/update` but `on_update()` is a **stub** (does nothing). Scene switching is HTTP-poll-only. Comments imply MQTT-trigger was intended. | Design gap |
| 2 | `kiosk.sh` (xinitrc) | Chromium launched with `exec`; if it crashes the X session exits and the Pi sits at a black screen until reboot. No respawn wrapper, no systemd unit watching it. | **Medium — race-day** |
| 3 | `please-check-in.kiosk:23-43` | Synchronous `while` loop measuring `.wanted_container.height()` and shrinking font-size until it fits. On Pi 3B+ with many racers, can block UI. Only happens on page load. | Low |
| 4 | `setup.sh` (kiosk Pi side) | `setup_kiosk_app()` function defined but never called (replaced by `setup_kiosk_app_v2()`). Dead code. | Cosmetic |

### B4. Network + isolation

Live findings from the central Pi:

- `eth0` is the only active interface, static `192.168.100.10/24`, default route `192.168.100.1`.
- Gateway is at `192.168.100.1` (MAC `cc:2d:21:a8:48:40`) — physical router, not the Pi. **The Pi is not a router and does not run DHCP.** The router hands out `.x` leases; the Pi happens to be at `.10` statically.
- **No internet reachability** — DNS resolves to `192.168.100.1` but the gateway has no upstream; `curl 1.1.1.1` and `curl github.com` both fail. This is the *intended* isolated race-day LAN.
- **No firewall installed at all** — `iptables`, `ip6tables`, `ufw` all "command not found". The Pi accepts MQTT, SSH, HTTP, syslog, rsync from anyone on the LAN. Acceptable for an isolated LAN (and there's no upstream anyway), but if the LAN is ever bridged to the internet (e.g. a misconfigured WiFi AP), the Pi is wide open.
- **Mosquitto binds 1883 on `0.0.0.0`** with `allow_anonymous true` — fine on isolated LAN, dangerous if exposed. Should be bound to `192.168.100.10` only as defense-in-depth.
- ARP table sweep shows only the gateway, the Pi, and the connecting laptop alive right now. All FAILED entries for `192.168.100.{20-44, 50-53}` (documented finishtimer/display/starttimer ranges) confirm no race-day hardware is currently connected.
- `mqtt-explorer-cd2edc8a` connected from `192.168.100.240` — someone's debug tool, not part of the appliance. Not a problem.

### B5. OS-level appliance posture

| Item | Reality | Recommendation (from web research) |
|---|---|---|
| Hardware watchdog | `/dev/watchdog0` exists, kernel driver loaded | **`RuntimeWatchdogSec=off`** — watchdog is NOT armed in systemd. Race-day, an MQTT-thread deadlock would hang forever. Set `RuntimeWatchdogSec=15` and `RebootWatchdogSec=2min`. |
| journald storage | `/var/log/journal/` populated (persistent) | RPi OS Trixie default. For appliance: set `Storage=volatile`, `RuntimeMaxUse=64M`. |
| swap | `/dev/zram0` 905M (zram-generator), 0B used | Good. zram beats dphys-swapfile for SD wear. `dphys-swapfile` not installed. ✓ |
| apt-daily timers | `apt-daily.timer` ACTIVE, `apt-daily-upgrade.timer` ACTIVE | `unattended-upgrades` not installed so timers are no-ops, but still wake the SD card and run apt every day. Mask them all. |
| Logged-in users | `derbynet@tty1` + `derbynet@seat0` since 2026-01-17 (4 months idle) | Stale physical-console logins. Reboot clears them; disable auto-login on the appliance. |
| SQLite | journal=DELETE, sync=FULL | Should be WAL + NORMAL. The `derbydb.py` direct-write path has never run, hence pragmas never applied. |
| Mosquitto bind | `0.0.0.0:1883` | Bind to `192.168.100.10` only. |
| Mosquitto persistence | `persistence true` in main conf, `autosave_interval` default (1800s) | Lower to 60s so retained topics survive a power-cut close to a real race result. |
| Retained MQTT pollution | Old retained `derbynet/race/state RACING`, `lane/N/led`, `device/DT54SIV*/telemetry` from January | After a test event: clear retained topics with `mosquitto_pub -r -n -t 'derbynet/...'` or restart with `persistence false` briefly. Race day should start clean. |
| nginx access log | 36MB rotated logs over Dec–May, current `derbynet_access.log` at ~800KB | Logrotate is working ✓. |
| `/var/log/derbynet/derby.jsonl` | 9.4MB, last touched Jan 17 | **No logrotate config for this file** — would grow without bound during a live event. |
| ESP32 starttimer client | Uses `umqtt`/`ntptime`, no LWT, no `mqtt_as`-style reconnect | (Web research) — migrate to `peterhinch/micropython-mqtt` `mqtt_as` + `machine.WDT(8000)` + retained LWT. |

---

## §C. Bug suspicions worth investigating before next event

In rough order of "would actually bite at race time":

1. **`derbyapi.py` HTTP timeout** — confirm `timeout=` is set on `requests.get/post`. If not, set it explicitly (3–5 s). Single biggest reliability win for the engine.
2. **Finishtimer integer-second timestamp** — change `int(time.time())` → `time.time()` at `finishtimer.py:122`. Trivial diff, massive precision win.
3. **Finishtimer state retain flag** — `retain=True` at `finishtimer.py:136` for the toggle topic should be `False`. Telemetry and status keep retain; finish events do not.
4. **Chromium auto-respawn** — wrap kiosk Chromium launch in a `while true; do chromium-browser ...; sleep 2; done` so a crash doesn't black-screen the display until reboot.
5. **Hardware watchdog armed in systemd** — `/etc/systemd/system.conf.d/99-derby-watchdog.conf` with `RuntimeWatchdogSec=15`. If `derbyRace.py` deadlocks, the Pi reboots in 15s instead of hanging.
6. **SQLite WAL on the live DB** — manually `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` on each event DB once. This persists. Reduces concurrent reader/writer blocking and SD wear.
7. **Clear retained MQTT before each event** — current broker has 4-month-old retained messages that derbyRace.py picks up on restart. Add a "broker reset" step to the pre-event checklist.
8. **timer-state.health_message wording** — "WARNING: Only 0/3 timers online during active race!" fires when **no race is active**. Stale-heartbeat detection is conflating "round scheduled" with "race in progress". Fix the conditional in the PHP source that builds this message.

## §D. "Good ideas" from 2025–2026 best-practice research

- **Mosquitto 2.x:** `bind 192.168.100.10`, set ACL by topic prefix even on the anonymous user, **do not set `max_keepalive`** (broker bug in 2.0.21+), `autosave_interval 60`, `max_queued_messages 1000`, `keepalive=30` on every client.
- **MQTT state pattern:** retained `derbynet/race/state` published *only* by the central engine, with `{seq, ts, phase, heat_id}` payload. Per-device LWT `derbynet/device/{hwid}/online` retained. Per-event topics (finish results) **not retained**, with `event_id` UUID so the PHP receiver can UPSERT idempotently.
- **Pi appliance:** mask `apt-daily*`, `fstrim.timer`, `man-db.timer`, `logrotate.timer`; install `log2ram` with `SIZE=64M`; `journald Storage=volatile, SystemMaxUse=20M`; `noatime, commit=600` on root mount.
- **SD card:** SanDisk Industrial 16GB or Samsung PRO Endurance 32GB, sourced from Mouser/Digi-Key. Keep two clones in the gear bag. Next season: USB-SSD on Pi 4 or NVMe-HAT on Pi 5.
- **ESP32 (starttimer):** `peterhinch/micropython-mqtt` `mqtt_as` library; `machine.WDT(8000)` fed only from main asyncio loop; LWT `derbynet/device/STARTER_001/online` retained.
- **Reference architectures:** FRC FMS for "isolated event LAN" patterns; Team 254 Cheesy Arena for an open-source state-machine reference. Upstream DerbyNet has no Pi-hardening guidance — your appliance work is genuinely additive.

## §E. Updated cleanup plan (race-day path, Part 2)

**Goal**: a known-good appliance for the next race, without forcing the existing decisions about ansible/chrony/derbytime/saasbox.

### P0 — must-fix before next event
1. **Replace PSU.** `0x50005` throttling is currently active. Beefier 5V/3A supply + short thick cable. Verify `0x0` after.
2. **Set request timeout in `derbyapi.py`** to 3–5s. Single-line change. Eliminates the 90s hang cycles.
3. **Arm hardware watchdog** in systemd. (`RuntimeWatchdogSec=15`.)
4. **Clear retained MQTT** before race day. Add to operator checklist.
5. **Pre-race DB pragma fix:** open each event DB once, set `journal_mode=WAL` and `synchronous=NORMAL`. Persists thereafter.

### P1 — should-fix before next event
6. **Finishtimer `int(time.time())` → `time.time()`** (precision).
7. **Finishtimer `retain=True` → `False`** on state topic (avoid stale-toggle pollution).
8. **Chromium respawn wrapper** in `kiosk.sh`.
9. **logrotate for `/var/log/derbynet/derby.jsonl`** — `daily, rotate 14, compress, copytruncate`.
10. **PHP `timer-state.health_message` conditional fix** — only flag "during active race" when `NowRacingState=1`.
11. **Mosquitto bind** to `192.168.100.10` (not `0.0.0.0`); add topic ACL even without auth.
12. **Mask `apt-daily*`, `fstrim.timer`, `man-db.timer`** + kill stale `tty1/seat0` sessions.

### P2 — cleanup / dead-weight
13. Remove `checkRaceTimeout()` (dead code in `derbyRace.py:761`).
14. Decide derbyTime.py fate (after confirming no consumer in `flutterapp`/`hlsfeed`).
15. Resolve KIOSK_DESIGN.md pending follow-ups (hardcoded colors in elimination kiosks, `top: 128px` in please-check-in, slideshow `vh` units).
16. Add compound index `(roundid, heat)` on `RaceChart`.
17. Convert `derbylogger.py` `DEFAULT_RSYSLOG_IP` to env var.

### P3 — next-season polish
18. Migrate ESP32 starttimer to `mqtt_as` + `machine.WDT`.
19. Move root FS to USB-SSD (Pi 4) or NVMe-HAT (Pi 5). Plan PSU upgrade with it.
20. Add a `derbynet/server/health` MQTT publisher on the central Pi (temp/throttled/df/MQTT-broker-up) — closes the monitoring gap.
21. Implement MQTT-driven kiosk scene switching (`on_update()` in `derbydisplay.py` currently a stub).

## §F. Verification queries you can run at any time

```bash
# Engine health
ssh derbypi
sudo vcgencmd get_throttled                                  # expect 0x0
curl -sS "http://localhost/derbynet/action.php?query=poll.coordinator" \
  | python3 -m json.tool | head -50
systemctl is-active derbyrace mosquitto nginx rsyslog rsync php8.4-fpm

# DB pragmas
sudo python3 -c "import sqlite3; c=sqlite3.connect('<event-db>'); \
  print('jm=',list(c.execute('PRAGMA journal_mode'))[0][0], \
        'sync=',list(c.execute('PRAGMA synchronous'))[0][0])"

# Retained topic snapshot
timeout 5 mosquitto_sub -h localhost -v -t '$SYS/broker/retained messages/count' -t 'derbynet/#'

# Watchdog status
grep -E "RuntimeWatchdog" /etc/systemd/system.conf*

# Logrotate coverage
ls /etc/logrotate.d/ | grep -i derby
```

## §G. Open questions (not blocking)

- Is `derbyTime.py`'s `derbynet/race/time` MQTT topic consumed by **`extras/flutterapp/`** or **`extras/soapbox/hlsfeed/`**? Not audited here. If yes, derbytime is alive; if no, it's pure dead weight.
- Is the kiosk MQTT-scene-switching (`on_update` stub) a feature to finish, or has HTTP polling become the official model? Affects whether to delete the subscription or finish wiring it.
- Is the finishtimer firmware version (`extras/soapbox/infra/finishtimer/files/` at `v0.8.0`) tracked anywhere? If so, an `rsync sync.sh`-driven update cycle is already in place — confirm it's been exercised recently.
