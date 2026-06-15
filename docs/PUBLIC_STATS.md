# Public Spectator Pages — Operator Runbook

> **Active token (do NOT rotate until 2026-06-22):**
> `bea32bfcdd26bedf8303cc33`
>
> This is the auto-minted token from the first deploy. The QR has already
> been distributed to spectators during testing and they've been showing
> it off; rotating mid-event would invalidate every scan they've taken.
> Keep stable through race day on 2026-06-21 + the day after for any
> lingering "what was that URL?" lookups. Rotate after June 22 if the
> next event wants a fresh one.

Three prerendered HTML surfaces served from the cloud-twin, behind an
obfuscated token URL. Designed for race-day spectators viewing on phones via
QR code.

- **Schedule** — current + upcoming heats for the active round, plus the last
  two completed heats for context. Heat number, lane, pinny, status, and
  finish time per row, with a darker rule separating heat groups.
- **Recent** — most recently completed heats (up to 10) with placements and
  times, in card view.
- **My Races** — keypad entry page where a spectator types their 4-digit
  pinny and is routed to a pre-rendered per-racer page showing that racer's
  heats in the current round.

No personally identifiable data leaves the cloud — the generator only reads
`carnumber` (pinny) from `RegistrationInfo`; first/last name fields are
never emitted, including on the per-racer pages. The only racer identifier
on any public-stats surface is the carnumber, which is already painted on
the car itself and visible on the schedule page. The schedule, recent, and
per-racer pages auto-refresh via **version-bump polling**: a few lines of JS
poll a tiny `version.txt` every ~4 s and reload only when the underlying race
data actually changed (the version is keyed on the synced DB's mtime, so an
idle DB triggers no reloads). The keypad page additionally has its numeric
input + navigate JS. No external assets.

### Event-driven freshness (how a result reaches a phone fast)

Updates are driven by race **events**, not a wall-clock poll, with a timer
backstop:

- **Pi push.** Race code requests a near-immediate push on the events that
  change the spectator pages — schedule generated/changed, heat advanced,
  round changed, result recorded/corrected. PHP (`request_cloud_push()` in
  `website/inc/data.inc`) and the Python race server (`derbydb.py`) bump the
  mtime of a world-writable trigger file (`/run/derbynet-cloud-sync.trigger`,
  mode 0666 via tmpfiles.d). A systemd `.path` unit
  (`derbynet-cloud-sync.path`) watching that file launches the existing
  cloud-sync service. The 30 s timer remains as the stray-catcher.
- **Single-flight + one catch-up.** `cloud-sync.sh` takes a non-blocking
  `flock`, so only one push runs at a time. If triggers arrive while a push is
  in flight they coalesce into exactly **one** catch-up push afterward
  (mtime recheck); anything past that rides the next 30 s tick. Verified by
  `testing/test-cloud-sync-trigger.sh`.
- **Cloud render-on-change.** The stats-gen container polls the synced DB's
  mtime every `POLL_SECONDS` (default 2) and re-renders the moment it changes,
  with `REFRESH_SECONDS` (default 30) as an idle floor. Each render publishes
  `version.txt`, which the pages poll to reload.

End-to-end a result is visible in roughly **5–12 s** (cellular push + ≤2 s
detect + render + ≤4 s browser poll), versus the old ~90 s worst case.

## URL shape

```
https://live.soapboxderbynet.com/<TOKEN>/schedule.html
https://live.soapboxderbynet.com/<TOKEN>/recent.html
https://live.soapboxderbynet.com/<TOKEN>/myraces.html      ← keypad entry
https://live.soapboxderbynet.com/<TOKEN>/me/<pinny>.html   ← per-racer detail
https://live.soapboxderbynet.com/<TOKEN>/feedback.html     ← audience feedback form
https://live.soapboxderbynet.com/<TOKEN>/feedback-submit   ← POST sink (→ derbynet-web)
```

`<TOKEN>` is a 24-hex-char random string. Wrong-token and bare-host requests
return a flat 404 with no body content that hints the route exists. An
unknown pinny under `/me/*.html` falls through to a friendly "not racing in
this round" page (via Caddy `try_files` → `me/notfound.html`).

## Why no rate limiting on My Races

The whole "My Races" surface is **pre-rendered** (on each race event, with a
30 s idle floor) — the keypad navigation just hits a static HTML file. There
is no DB query per visitor, no fetch endpoint to abuse. Concrete properties:

- Caddy serves each per-racer page from disk. The HTML is sent `no-cache`
  (revalidate-each-load, so a version-bump reload never serves stale) and the
  `version.txt` heartbeat is `no-store`; both are tiny, so a packed venue
  polling `version.txt` every ~4 s costs only a few bytes per poll and a full
  page read only when the data actually changes.
- The keypad page has a 300 ms client-side debounce + input lock after the
  4th digit, preventing accidental double-navigates.
- Random guessing falls through to `me/notfound.html` — itself a static
  cached file. No additional DB load, no information leak (all pinnies in
  the round are already visible on schedule.html anyway).

We deliberately do not run Caddy's rate-limit module here — there's no
threat model that requires it.

## Audience feedback form

A **💬 Submit feedback** button sits in the footer of every spectator page (just
above the sponsor credit) and opens `feedback.html` — a small static page with a
150-character text box. Purpose: capture spectator sentiment during the event for
a manual post-mortem afterwards (no live analysis, no moderation surface).

How it works:

- **Page** (`stats-gen/template-feedback.html`): rendered into the token dir like
  the other pages, but with **no auto-reload script** (a reload would wipe a draft).
  On load it mints a per-device id (`crypto.randomUUID`, fallback for old browsers)
  in `localStorage['sbd_fb_device']` and prefills the box from
  `localStorage['sbd_fb_text']`, so a returning visitor **edits** their note rather
  than adding a new one. This "one note per person" gate is soft and client-side by
  design.
- **Submit**: a relative `fetch("feedback-submit", {method:"POST", …})`. Because the
  page is served under `/<TOKEN>/`, Caddy resolves that to
  `/<TOKEN>/feedback-submit` and **reverse-proxies it to `derbynet-web`** (rewritten
  to `/feedback-submit.php`). Staying on the `live.*` host keeps it **same-origin
  (no CORS)** and never exposes the control-surface host to spectators. It's still
  behind the token gate, and the request body is capped at 8 KB in Caddy.
- **Server** (`website/feedback-submit.php`): a deliberately **standalone,
  unauthenticated** endpoint — it does **not** include the DerbyNet session/DB/auth
  stack, so it can never touch the race database. It validates + truncates `text` to
  150 chars, then appends one JSON object per line to
  `/var/lib/derbynet/feedback/feedback.jsonl` (in the `derbynet_data` volume) with
  `LOCK_EX`. Each record is `{ts, device_id, text, ip, ua}` (UTC ISO-8601; `ip`/`ua`
  are stored for the forensic post-mortem only and are **never displayed**).
- **No rate limiting on purpose**: every submission — including a returning visitor's
  edits — is recorded as its own timestamped line under the same `device_id`. That's
  what lets the post-mortem spot a single device or IP spamming. A 50 MB file cap is
  the only backstop (accept-but-drop past it); far above any plausible event volume.

Retrieve the log after the event (routes through the web container, so you don't
need the host bind path):

```
./scripts/derbyvps.sh feedback show          # submission count + last 5 entries
./scripts/derbyvps.sh feedback dump [outfile] # download feedback.jsonl (default ./derby-feedback.jsonl)
```

`dump` also prints the unique-device count when `jq` is available locally. The file
is JSONL — one record per line — so a post-mortem can `jq` / group by `device_id`
or `ip` directly.

## One-time prerequisites

Performed once per VPS, before the first race day.

1. **DNS A-record** for `live.soapboxderbynet.com` pointing at the VPS public IP
   (149.248.56.169 at time of writing). Caddy auto-acquires the Let's Encrypt
   cert on first request.

2. **Deploy** the stack including the `derbynet-stats-gen` service:

   ```
   ./scripts/derbyvps.sh deploy
   ```

   Deploy creates `/opt/derbynet/production/public-stats/` automatically (kept
   outside `/opt/derbynet/production/data` so it cannot collide with the
   Pi → cloud SQLite sync) and brings the stack up with `EXPECTED_SERVICES_MIN=5`
   in postflight.

## Race-day workflow

### Morning of, before doors open

```
./scripts/derbyvps.sh stats-token rotate
./scripts/derbyvps.sh stats-token qr --out derby-qr-$(date +%F).png
```

`rotate` does five things on the VPS:
- generates a fresh 24-hex token (`openssl rand -hex 12`),
- updates `LIVE_STATS_TOKEN` in `installer/docker-cloud/.env`,
- recreates `derbynet-stats-gen` and `caddy` so both read the new token,
- runs one synchronous render so the new token's HTML exists immediately,
- generates `qr.png` inside `tokens/<TOKEN>/`.

`qr` scp's the PNG down to `./derby-qr.png` (or `--out <path>`) ready to print.

### Verify before posting the QR

From any phone on cellular:

1. Scan the QR — should land on `schedule.html` showing the round name and a
   table of heats.
2. Strip the URL to the bare host — should return `Not found` 404.
3. Change one character in the token — should return `Not found` 404.

If the page shows "Awaiting race start", the Pi hasn't synced a populated
`RaceInfo.RoundID` yet. The page will populate automatically on the next
sync; no operator action needed.

## Day-of troubleshooting

| Symptom | First thing to check |
|---------|----------------------|
| Phones get 404 on a known-good URL | `./scripts/derbyvps.sh logs caddy` — look for the host block loading the token from env. |
| Page says "Awaiting race start" mid-race | The cloud DB isn't getting fresh syncs from the Pi. Check `./scripts/derbyvps.sh audit` for "LAST CLOUD-SYNC". |
| "Updated" timestamp >2 min stale | `./scripts/derbyvps.sh logs derbynet-stats-gen` — look for SQLITE_BUSY or render errors. |
| Wrong heat highlighted | The Pi may not have re-synced `RaceInfo.Heat`. Force a sync from the Pi. |
| TLS cert error on first hit | Caddy is still negotiating with Let's Encrypt — retry in 30 s. If persistent, check rate limits in `logs caddy`. |
| `qr.png` missing after rotate | Re-run `stats-token rotate` — the `qrencode` step is best-effort and logs `WARN qr generation failed` on failure. The token itself is still active. |

## Mid-event token rotation

Generally avoid — the printed QR becomes useless and crowd-confusing. But if
the token leaks (someone screenshots and posts publicly), `stats-token rotate`
again. Old token's path returns 404 within seconds of recreate finishing;
the old `tokens/<OLD>/` directory can be left in place (50 KB) or pruned later.

## Pi-side push (cloud-sync)

The cloud-twin only displays what the DerbyPi pushes to it. Without an active
pusher, `health.json` shows `db_mtime: "(missing)"` and both pages render
the "Awaiting race start" placeholder.

### What runs on the Pi

`/usr/local/sbin/derbynet-cloud-sync.sh` runs on two triggers: a 30 s systemd
timer (`derbynet-cloud-sync.timer`, the stray-catcher) and — for near-immediate
freshness — a `.path` unit (`derbynet-cloud-sync.path`) that fires whenever race
code requests a push (see "Event-driven freshness" above). Each run:

1. SQLite `.backup` of the active event DB (WAL-safe; no main DB lock).
2. `scp -C` the snapshot to `/opt/derbynet/production/data/derbynet.sqlite3.tmp`
   on the VPS, with a 15 s connect timeout + 5 s keepalive (cellular-tolerant).
3. `scp -C` a `.cloud_readonly.tmp` sentinel containing `last_sync_utc=...`.
4. Single SSH `mv` to atomically swap both files into their final paths
   so concurrent stats-gen reads never see a torn DB.

Only one push runs at a time: the script takes a non-blocking `flock`, and if a
trigger lands mid-push it does exactly one coalesced catch-up afterward (further
triggers ride the next timer tick). Failure on any step logs to journal
(rate-limited during outages — first failure + every 10th) and exits non-zero;
the 30 s timer is the ultimate retry. The flock + coalesce-to-one-retry logic is
covered by `testing/test-cloud-sync-trigger.sh`.

### One-time setup

**1. Fleet keypair** (generated once; same key on every Pi in the fleet).

Generate locally with:

```
ssh-keygen -t ed25519 -f cloud-sync-key -N "" -C "derbypi-fleet-sync"
```

The **private key** goes into the GitHub Action secret `CLOUD_SYNC_PRIVATE_KEY`.
The image-build workflow (`.github/workflows/build-images.yml`) writes it
into `extras/imaging/derbypi/rootfs/etc/derbynet/cloud-sync-key` at build
time. If the secret is unset, the workflow logs a `::warning::` and ships
an empty key — Pis will boot with cloud-sync disabled (logged on each tick,
otherwise harmless).

The **public key** goes into `~claude/.ssh/authorized_keys` on the VPS,
with a `command="..."` restriction that locks the key to the receiver
wrapper at `installer/docker-cloud/scripts/cloud-sync-recv.sh`:

```
from="*",command="/opt/sbderbynet/installer/docker-cloud/scripts/cloud-sync-recv.sh",restrict ssh-ed25519 AAAA... derbypi-fleet-sync
```

The receiver wrapper allows exactly three operations: scp into the DB tmp
path, scp into the sentinel tmp path, and the atomic-mv that swaps both
into place. Anything else is logged to `auth.warning` and refused with
exit code 100.

**2. VPS host keys** are already captured in
`extras/imaging/derbypi/rootfs/etc/derbynet/cloud-sync-known_hosts`
(checked in, not secret). `StrictHostKeyChecking=yes` on the Pi side
refuses unknown hosts — no TOFU window.

**3. Image rebuild + flash**. With the GitHub Action secret set, push to
master (or run the workflow manually) to rebuild the derbypi `.img.xz`.
Flash one Pi; observe the timer:

```
sudo systemctl status derbynet-cloud-sync.timer    # active, next fire <30s
sudo journalctl -u derbynet-cloud-sync -n 50       # "synced <DB> -> <VPS>" lines
```

### Troubleshooting

| Symptom on the Pi | First check |
|-------------------|-------------|
| `derbynet-cloud-sync` exits status 1 with "SSH key not readable" | Image was built without `CLOUD_SYNC_PRIVATE_KEY` set. Re-run the workflow with the secret, reflash. |
| `derbynet-cloud-sync` exits status 2 ("DB not found") | No `derbynet.sqlite3` under `/var/lib/derbynet/`. Run a race-day setup first; this is expected on a fresh image. |
| Repeated "FAIL: scp DB failed" | Cellular outage, or VPS authorized_keys entry missing. `ssh -i /etc/derbynet/cloud-sync-key claude@uisp.darketech.ca` (interactively, with the right command) should give "not permitted" — if it gives "Permission denied (publickey)", the pubkey isn't in authorized_keys. |
| Pi pushes successfully but cloud pages still say "Awaiting race start" | Pi's active DB has no `RaceInfo.RoundID` row. Check `sqlite3 /var/lib/derbynet/<year>/<event>/derbynet.sqlite3 "SELECT * FROM RaceInfo"`. |
| stats-gen `health.json` shows old `db_mtime` | Pi's timer stopped firing, or scp is being silently rejected. Check `derbyvps.sh logs caddy` for `cloud-sync-recv: not permitted` entries. |

### Rotating the fleet key

If the image leaks publicly or you suspect the key is compromised:

1. Generate a new keypair.
2. Add the new pubkey to VPS authorized_keys; remove the old one.
3. Update `CLOUD_SYNC_PRIVATE_KEY` GitHub secret.
4. Rebuild + reflash the fleet (or `scp` the new key onto running Pis
   into `/etc/derbynet/cloud-sync-key` and `systemctl restart derbynet-cloud-sync.timer`).

The blast radius before rotation is one bind-mounted directory on the
VPS (Pi-synced DB + sentinel). The leaked key cannot read VPS files,
run arbitrary commands, or touch the Pi.

---

## How it's built

| Component | Container / Host | Source |
|-----------|------------------|--------|
| Static page generator | `derbynet-stats-gen` | `installer/docker-cloud/Dockerfile.stats` + `stats-gen/*.sh` |
| Renderer SQL queries | (same) | `stats-gen/render.sh` — reads RaceInfo, Rounds, RaceChart, RegistrationInfo |
| HTML templates | (same) | `stats-gen/template-{schedule,recent,myraces,me-detail,me-notfound,feedback}.html` |
| Public routing | `derbynet-caddy` | `installer/docker-cloud/Caddyfile` (`live.soapboxderbynet.com` block) |
| Feedback sink | `derbynet-web` | `website/feedback-submit.php` → `feedback.jsonl` in `derbynet_data` volume |
| Bind-mount | VPS host | `/opt/derbynet/production/public-stats/` |
| Token store | VPS host | `installer/docker-cloud/.env` (`LIVE_STATS_TOKEN=…`) |
| Pi-side pusher | DerbyPi systemd | `extras/imaging/derbypi/rootfs/etc/systemd/system/derbynet-cloud-sync.{service,timer,path}` + `…/tmpfiles.d/derbynet-cloud-sync-trigger.conf` + `extras/soapbox/infra/server/cloud-sync.sh` |
| VPS-side receiver | `claude@uisp.darketech.ca` ForceCommand | `installer/docker-cloud/scripts/cloud-sync-recv.sh` (in `authorized_keys` `command=`) |
| Fleet key (private) | GitHub secret `CLOUD_SYNC_PRIVATE_KEY` → image rootfs at build | `extras/imaging/derbypi/rootfs/etc/derbynet/cloud-sync-key` |
| Fleet key (public) | VPS `~claude/.ssh/authorized_keys` with restricted `command=` | (committed by operator manually) |
| VPS host keys | Pi rootfs known_hosts | `extras/imaging/derbypi/rootfs/etc/derbynet/cloud-sync-known_hosts` |

Generator runs as a non-root `stats` user, reads `derbynet.sqlite3` read-only,
writes its tmp directory inside `/out/tokens/.tmp.*` then `mv`s into place
(atomic per-file). No PHP, no DB writes, no MQTT — fully decoupled from the
race-control surface.

## Architecture notes

- Caching: pages are served `Cache-Control: no-cache` (revalidate each load) and
  `version.txt` `no-store`, so a version-bump reload always fetches fresh. Both
  are tiny — Caddy gzips on the wire (~3 KB per page, a few bytes per ~4 s poll),
  and a full page is re-fetched only when the data actually changed.
- Index hygiene: `X-Robots-Tag: noindex, nofollow` and `<meta name="robots">`
  keep accidental crawls out of search results.
- DerbyPi impact: zero. The generator only reads the cloud-twin's replica DB.
- Tenant scope: the generator reads the canonical `derbynet.sqlite3` (Pi-sync
  target). It does NOT understand `DERBYNET_TENANT_MODE=multi` sandboxes; if
  you ever route the Pi sync into a per-tenant subdir, update `DB_PATH` in
  `docker-compose.yml`.

## Testing

Offline suites (no Pi/cloud needed) under `testing/`:

| Suite | Covers |
|---|---|
| `test-cloud-sync-trigger.sh` | Pi push single-flight `flock` + coalesce-to-one-catch-up retry (stubs scp/ssh/sqlite3) |
| `test-stats-render.sh` | `render.sh`: `version.txt` = DB mtime, stable when idle, bumps on change; `{{VERSION}}` substitution + content (real sqlite DB); feedback page generated (form, 150-char cap, no auto-reload) + footer button on spectator pages |
| `test-stats-render-loop.sh` | `entrypoint.sh`: renders on startup + on DB change, not while idle |
| `test-cloud-push-integration.sh` | PHP hooks against a real DerbyNet instance in Docker — no-op when the trigger is absent (cannot break racing), fires on schedule/heat/result when present |
| `test-derbydb-cloud-push.py` | The real `derbydb.request_cloud_push`: no-op absent, fires present, swallows `OSError` |

These prove the system **can't break racing** and that freshness behaves
correctly. They do **not** exercise the real `.path` trigger firing, the scp
transfer, Caddy's headers, or end-to-end latency — confirm those once on real
hardware via [DRESS_REHEARSAL.md](DRESS_REHEARSAL.md). Every failure on that
remaining path degrades to the 30 s timer; none can break racing.
