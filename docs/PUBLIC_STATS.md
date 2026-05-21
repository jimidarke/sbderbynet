# Public Spectator Pages — Operator Runbook

Two prerendered HTML pages served from the cloud-twin, behind an obfuscated
token URL. Designed for race-day spectators viewing on phones via QR code.

- **Schedule** — full lineup for the active round (heat #, lane #, pinny #,
  with the current heat highlighted and finished heats showing place + time).
- **Recent** — last 3 completed heats with placements and times.

No personally identifiable data leaves the cloud — the generator only reads
`carnumber` (pinny) from `RegistrationInfo`; first/last name fields are never
touched. Pages refresh every ~30 s via an HTML `<meta refresh>`; no JS, no
external assets.

## URL shape

```
https://live.soapboxderbynet.com/<TOKEN>/schedule.html
https://live.soapboxderbynet.com/<TOKEN>/recent.html
```

`<TOKEN>` is a 24-hex-char random string. Wrong-token and bare-host requests
return a flat 404 with no body content that hints the route exists.

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

## How it's built

| Component | Container | Source |
|-----------|-----------|--------|
| Static page generator | `derbynet-stats-gen` | `installer/docker-cloud/Dockerfile.stats` + `stats-gen/*.sh` |
| Renderer SQL queries | (same) | `stats-gen/render.sh` — reads RaceInfo, Rounds, RaceChart, RegistrationInfo |
| HTML templates | (same) | `stats-gen/template-{schedule,recent}.html` |
| Public routing | `derbynet-caddy` | `installer/docker-cloud/Caddyfile` (`live.soapboxderbynet.com` block) |
| Bind-mount | VPS host | `/opt/derbynet/production/public-stats/` |
| Token store | VPS host | `installer/docker-cloud/.env` (`LIVE_STATS_TOKEN=…`) |

Generator runs as a non-root `stats` user, reads `derbynet.sqlite3` read-only,
writes its tmp directory inside `/out/tokens/.tmp.*` then `mv`s into place
(atomic per-file). No PHP, no DB writes, no MQTT — fully decoupled from the
race-control surface.

## Architecture notes

- Caching: `Cache-Control: public, max-age=20, stale-while-revalidate=40` means
  100 phones effectively share one file read every ~20 s regardless of refresh
  jitter. Caddy gzips on the wire (~3 KB per page).
- Index hygiene: `X-Robots-Tag: noindex, nofollow` and `<meta name="robots">`
  keep accidental crawls out of search results.
- DerbyPi impact: zero. The generator only reads the cloud-twin's replica DB.
- Tenant scope: the generator reads the canonical `derbynet.sqlite3` (Pi-sync
  target). It does NOT understand `DERBYNET_TENANT_MODE=multi` sandboxes; if
  you ever route the Pi sync into a per-tenant subdir, update `DB_PATH` in
  `docker-compose.yml`.
