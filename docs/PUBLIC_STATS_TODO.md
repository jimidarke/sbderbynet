# Public-Stats Spectator Pages — Improvement Backlog

Captured 2026-05-22 after the v0.10.1 deploy (`feat(public-stats): My Races
pinny lookup + spectator UI polish`). Pages live behind the locked token
through 2026-06-22; see [PUBLIC_STATS.md](PUBLIC_STATS.md) for the current
architecture.

The system today (since the 2026-06-15 event-driven rework): race events on
the Pi request a push (single-flight + one coalesced catch-up; 30 s timer as
backstop) → cloud-twin → stats-gen renders on DB-mtime change (≤2 s poll, 30 s
idle floor) → static HTML + `version.txt` → Caddy (`no-cache` HTML, `no-store`
version.txt) → browser version-bump poll (~4 s, reload only on change).
End-to-end latency ≈ 5–12 s. PII-free (pinny only), token-gated. See
[PUBLIC_STATS.md](PUBLIC_STATS.md) "Event-driven freshness".

> **Done:** items P1-#1 (tighten cadence) and P1-#5 (push-not-poll) below are
> superseded by that rework — kept for history. The version-bump poll achieves
> P1-#5's goal (reload only on change, low mobile data) without needing a
> streaming SSE backend, which static-file Caddy can't serve anyway.
>
> **Done (2026-06-15): audience feedback form.** A footer **💬 Submit feedback**
> button → static `feedback.html` (150-char box, soft one-note-per-device gate via
> `localStorage`) that POSTs same-origin to a standalone `website/feedback-submit.php`
> (Caddy-proxied, token-gated, no DB/auth) which appends `{ts,device_id,text,ip,ua}`
> JSONL to the `derbynet_data` volume. Every submission recorded (no dedup) so the
> manual post-mortem can spot spammers. Retrieve via `derbyvps.sh feedback show|dump`.
> See [PUBLIC_STATS.md](PUBLIC_STATS.md) "Audience feedback form". This subsumes much
> of P6's intent for capturing spectator signal (page-view counter below remains open).

Items below are ranked roughly by "user-value per hour of work".

---

## P1 — Top 5 picks (highest ROI)

### 1. Tighten cadence to ~10 s — ✅ SUPERSEDED (2026-06-15)
Replaced by event-driven push + render-on-change + ~4 s version-bump poll
(end-to-end ≈ 5–12 s, better than the 10 s target without the 3×-cellular
cost). Original deploy-only plan kept below for history.

| File | Change |
|---|---|
| `extras/imaging/derbypi/rootfs/etc/systemd/system/derbynet-cloud-sync.timer` | `OnUnitActiveSec=10s` (requires reflash or `scp+daemon-reload`) |
| `installer/docker-cloud/docker-compose.yml` | `REFRESH_SECONDS=10` in stats-gen service env |
| All 5 templates | `<meta http-equiv="refresh" content="30">` → `content="10"` |
| `installer/docker-cloud/Caddyfile` | `max-age=7, stale-while-revalidate=14` |

**Tradeoff:** 3× cellular SSH connects/min on the Pi. Watch render-cost
scaling — at >80 racers, render starts to compete with the 10 s budget;
see P3-#3 (render refactor) for the fix.

### 2. Save last pinny in `localStorage` + one-tap return
~15 lines of JS in `template-myraces.html`. On a returning visit show
`Last: 0042 ↩` as a quick-tap above the keypad. Removes the only real
friction in the My Races flow. No server change.

### 3. Live "data age" indicator
~10 lines of JS, share across templates. Reads the `{{UPDATED}}` timestamp
from the footer, ticks "updated 3 s ago … 4 s ago …" in place. Massive
trust signal for near-zero effort — when the page looks stuck, users can
see *exactly* how stale they're looking at.

### 4. "Event ended" graceful state
Catches the awkward post-final-heat dead-air. When `health.json.db_mtime`
is fresh **and** the last completion was >5 min ago **and** HEAT_NOW ==
max(heat), switch the schedule/recent headers to "🏁 Final Results". (The
version-bump poll already stops reloading once the data stops changing, so no
refresh teardown is needed — just a render.sh hook + a CSS variant.)

### 5. SSE push instead of polling — ✅ SUPERSEDED (2026-06-15)
Achieved the goal (reload only on change, low mobile data) via version-bump
polling of `version.txt` instead of true SSE — static-file Caddy can't hold an
`EventSource` stream open, so a polling heartbeat is the right fit here.
Original note kept below for history.

Bigger lift (~½ day). Replace `<meta refresh>` with `EventSource` against a
tiny `events.txt` file that stats-gen `touch`es each render — Caddy serves
it with `Content-Type: text/event-stream`. Page reloads only when the file
ticks. **Correct** architectural move long-term; lets latency drop to
sub-second and mobile data plummet.

---

## P2 — Pinny / "My Races" UX

| Item | Effort | Notes |
|---|---|---|
| **Multi-pinny following list** (up to 5 siblings) — saved in `localStorage`, page rotates through them or shows them side-by-side on a single "family view" | S | Frequently asked at PWD-style events. Build on top of P1-#2. |
| **"Up next" hint** on per-racer page — "Your next race: heat 13 (~9 min)" pulled from heat-number delta × estimated heat cadence | XS | Spectators know whether to grab coffee. Heat cadence can be derived from `MAX(completed) - MIN(completed)` divided by completed-heat-count. |
| **Share button** on per-racer page — `navigator.share()` with copy-to-clipboard fallback | XS | One-tap family WhatsApp. |
| **Pre-validate pinny against valid list** in the keypad JS | XS | Don't navigate to a known-bad pinny page; show inline "Pinny #9999 isn't racing this round". Requires embedding the valid-pinny JSON in the keypad page (small — <2 KB for 200 racers). |

## P3 — Resilience / failure modes

| Item | Effort | Notes |
|---|---|---|
| **Stale-data banner** — if `health.json.db_mtime` is >2 min old, show "⚠ Track connection degraded — last update Xm ago" | S | Honest signal when the Pi cellular is flaky. |
| **Render refactor: one SQL query + awk-emits-files** | M | Replaces the per-racer SQL loop. Brings 200-racer render under 5 s. Only worth doing once event size pushes past ~80 racers OR before P1-#1 cadence change at large events. |
| **Atomic dir swap robustness** — current `mv me me.old && mv .../me me` has a brief window where requests 404 between the two mvs. Use `renameat2(RENAME_EXCHANGE)` or a symlink swap. | XS | Edge-case polish; only matters at sub-second cadences. |

## P4 — Discoverability

| Item | Effort | Notes |
|---|---|---|
| **Vanity short-URL** — `live.soapboxderbynet.com/<eventslug>` → 302 to current token. Operator controls slug in `.env`. | S | Memorable when QR is lost; doesn't compromise the obscurity-gate. |
| **PWA manifest + add-to-home-screen** | S | Returning users open it like an app. Service worker optional. |
| **`/robots.txt` at the token path** | XS | Currently only header-level — also serve an empty allow-none robots.txt for belt-and-suspenders. |

## P5 — Data / depth

| Item | Effort | Notes |
|---|---|---|
| **Cross-round / series standings** — points totals across all rounds for a given pinny | M | Requires understanding the elimination tournament config (see `website/inc/elimination-configs/`). |
| **Head-to-head heat preview** — per-racer "vs this lineup" before each upcoming race | M | |
| **Light/dark mode** via `prefers-color-scheme` | XS | Currently locked `light`. Decision is intentional for outdoor sun visibility — document or relax. |

## P6 — Operational

| Item | Effort | Notes |
|---|---|---|
| **Anonymous page-view counter** — Caddy logs already exist; a per-render aggregation into `health.json` would surface load | S | Useful for sizing future events. |
| **Multiple tokens per event** — staff token vs spectator token, different cache TTLs | S | Currently one token for everyone. |
| **Restart-without-rotate** — derbyvps.sh has no `restart` subcommand; we did a manual `docker compose restart caddy` post-deploy because Caddyfile is bind-mounted. Add `derbyvps.sh restart [service]`. | XS | Avoids the manual-SSH step. |

---

## Out of scope (intentionally)

- Backend / dynamic endpoint for My Races — the pre-rendered static model is
  load-bearing for the no-rate-limit posture; do not undo it.
- PII expansion — pinny-only on every public-stats surface (see
  `feedback_public_stats_no_pii.md` in Claude memory). This is locked.
- Token rotation before 2026-06-22 — QR already distributed (see
  `project_live_token_locked.md` in Claude memory).
