# Testing Day — 2026-06-13 Session Notes

Operational log of a race-system validation session: resolving local git
divergence, validating the pulled code, bringing the race-day Pi into code
compliance via surgical update, and reconnoitring the cloud-sync / public-
monitoring path. Point-in-time record (sibling to
[RACE_SYSTEM_AUDIT_2026-05.md](RACE_SYSTEM_AUDIT_2026-05.md) and
[SIMULATION_REPORT_2026-06.md](SIMULATION_REPORT_2026-06.md)).

## 1. Git state resolved — GitHub is source of truth

Local `master` had diverged: **1 local commit ahead, 9 behind** `origin/master`.
Per direction that the thoroughly-tested GitHub code is the source of truth:

- Local commit `1f113db9` (`feat(analytics): spectator visitor analytics via
  Caddy log + GoAccess`) was preserved on branch
  **`backup/local-analytics-2026-06-13`** (not deleted — safe to drop later).
- `master` was `git reset --hard` to `origin/master` → now at
  **`6ece5c7d`**, working tree clean.

## 2. Validation of the pulled code

Standalone tests (no server required) — both **PASS**:

- **Simulator self-test** (`testing/simulator/selftest.py`): 36/36 green —
  scoring primitives, micro6 oracle for both scoring methods, withdrawn-racer
  exclusion, finals/awards ordering, planner determinism, tie injection. This
  is the elimination engine the pulled commits rewrote.
- **JS syntax** (esprima `parseScript` over all first-party `.js`): 108/108
  clean. Only `website/js/vendor/mqtt.min.js` (minified vendor bundle) doesn't
  parse as a plain script — pre-existing, unrelated.

The PHP integration suite (~50 `test-*.sh` + Puppeteer E2E) was **not run** —
it requires a live PHP instance and re-tests code already validated upstream
(see `docs/SIMULATION_REPORT_2026-06.md`, 100/100 campaigns). Standing up a
local stack surfaced reusable gotchas (see §6).

## 3. Pi code compliance — surgical update applied

The race-day Pi (`derbypi`, 192.168.100.10, reachable over the race wifi) is a
**bare PHP appliance** (nginx + php8.4-fpm, **not** Docker), **image-baked with
no git checkout on device**. Layout:

| Thing | Path |
|---|---|
| Webroot (served under `/derbynet`) | `/var/www/html/derbynet/` (owner `derbynet:www-data`) |
| Infra / race server | `/var/lib/infra/` (owner `derbynet:derbynet`), unit `derbyrace.service` |
| Data root (tenant = `<year>/<event>`) | `/var/lib/derbynet/` — active: `2026/DerbyTest`, schema v17 |
| Active-tenant switch | `/var/www/html/derbynet/local/config-database.inc` (hard-codes the DB path) |
| Image provenance | `/etc/derby-image-sha`, `/etc/derby-image-built-at`, `/etc/derby-role` |

**Drift:** Pi imaged from **`e07ee621`** (2026-05-21); `master` is `6ece5c7d`.
Five commits touched Pi code dirs since the image: `61b917dd` (elimination
scoring toggle governs advancement), `443f692d` (race-server lane-count fix),
`194b4382` (unify advancement engine + simulator), `061de2ad` (zero-pad pinny +
public splash), `007d1aba` (public-stats DNS + state-dir fixes).

**Applied** (surgical `rsync -rlc`, **no `--delete`**, excluding
`.git`/`*.md`/`node_modules`/`local/`/`Data/`/`__pycache__`; ssh user `derbynet`
owns both trees so no sudo for the copy):

- **Webroot:** 55 files (modified + 4 new: `welcome.php`,
  `inc/elimination-advancement.inc`, `js/pinny.js`,
  `inc/elimination-configs/soapbox-derby-elimination-dropslowest.json`) →
  `/var/www/html/derbynet/`.
- **Infra:** 3 files (`server/cloud-sync.sh`, `server/derbyRace.py`,
  `server/derbydb.py`) → `/var/lib/infra/`.
- Restarted `php8.4-fpm` + `derbyrace.service`.

**Verified:** post-update checksum dry-run = **0 differing files** on both trees;
`index.php`/`welcome.php`/`coordinator.php` → HTTP 200, `checkin.php` → 302
(login redirect); `derbyrace` active with **0 restarts** (no crash loop).

### Reproducing the surgical update

```sh
# from repo root, after `git reset --hard origin/master`
rsync -rlc -i --exclude='.git' --exclude='*.md' --exclude='node_modules' \
  --exclude='local/' --exclude='Data/' \
  ./website/ derbypi:/var/www/html/derbynet/
rsync -rlc -i --exclude='.git' --exclude='*.md' --exclude='__pycache__' --exclude='*.pyc' \
  ./extras/soapbox/infra/ derbypi:/var/lib/infra/
ssh derbypi 'sudo systemctl restart php8.4-fpm derbyrace.service'
# Never use --delete (would wipe runtime local/ and data). ant `generated`
# artifacts are gitignored and not generated on deploy — omitting them matches
# the image, so they are not needed for parity.
```

## 4. OPEN ITEM — host-config drift NOT applied

Three baked `/etc` files on the Pi changed since the image (commit `007d1aba`).
A code-tree rsync does **not** carry these. Status at end of session:

- `etc/resolv.conf` — **already compliant** on the Pi (identical nameservers
  `1.1.1.1`/`8.8.8.8`/`1.0.0.1` + options; only the comment header differs). No
  action needed.
- `etc/default/derbynet-cloud-sync` — Pi still has old `STATE_FILE=/run/derbynet-cloud-sync.state`
  (new: `/run/derbynet-cloud-sync/state`). **NOT applied.**
- `etc/systemd/system/derbynet-cloud-sync.service` — Pi still missing the
  `RuntimeDirectory=derbynet-cloud-sync` / `RuntimeDirectoryMode=0755` lines
  (the fix for the cloud-sync state-dir bug). **NOT applied.**

These two are a paired robustness fix; cloud-sync currently works without them
(see §5), so they are low-urgency. To apply: copy both repo files to the Pi
`/etc`, `systemctl daemon-reload`, then `systemctl start derbynet-cloud-sync`.
Other image-rootfs drift (`finishtimer/*`, `_common/customize.sh`,
`build-images.yml`) is satellite-/build-only and out of scope for the central Pi.

## 5. Cloud-sync / VPS access — discovery (Phase 2 parked)

The intended Phase-2 work (pull the **stalbert** official tenant SQLite from the
VPS and inject it into the Pi) is **parked** — the admin wrapper key
(`~/.ssh/sbderby_vps_ed25519`, used by `scripts/derbyvps.sh`) was **not present**
on this workstation, and none of the other local keys authenticate to the VPS.

However, recon found the unblock: **the Pi already holds a working VPS
credential.** `derbynet-cloud-sync.service` successfully pushes on its timer:

```
synced /var/lib/derbynet/2026/DerbyTest/derbynet.sqlite3
  -> claude@uisp.darketech.ca:/opt/derbynet/production/data/derbynet.sqlite3
```

- Working VPS user is **`claude`** (the `derbyVPS` skill is correct; an in-session
  guess of `root` was wrong).
- The deploy key lives on the Pi at **`/etc/derbynet/cloud-sync-key`** (pinned
  `known_hosts` at `/etc/derbynet/cloud-sync-known_hosts`). It may be restricted
  to the cloud-sync command — verify before assuming arbitrary SSH.
- Cloud-sync target is a **flat** path `…/data/derbynet.sqlite3`, not a per-tenant
  dir — relevant when reconciling the Pi's `<year>/<event>` scheme against the
  cloud `tenants/<slug>` scheme.

## 6. Local PHP test-harness gotchas (for next time)

Standing up the web app locally to run the shell suite needs:

- **PHP isn't installed by default.** `sudo apt-get install -y php-cli
  php-sqlite3 php-gd php-curl php-xml php-mbstring` (got 8.3.6).
- **`testing/*.sh` are committed with CRLF** (a former Windows dev). They won't
  run under bash as-is — run from a CR-stripped mirror (`sed -i 's/\r$//'`), or
  permanently fix with `.gitattributes` (`*.sh text eol=lf`) + renormalize.
- **PHP's built-in server doesn't copy custom env into `$_SERVER`**, but DerbyNet
  reads `$_SERVER['DERBYNET_DATA_DIR']`/`['DERBYNET_CONFIG_DIR']`. `getenv()`
  works, so run with `-d auto_prepend_file=<shim>` where the shim mirrors those
  vars from `getenv()` into `$_SERVER`.
- Serve with `php -S 127.0.0.1:8080 -t website` (env `DERBYNET_DATA_DIR` +
  `DERBYNET_CONFIG_DIR` set to temp dirs), bootstrap via
  `action.php` `action=setup.nodata&ez-new=<name>`. Harness needs `jq`.

## 7. Network path note

Confirmed internet via the derbynet path: workstation is dual-homed —
`enp1s0` (home LAN, `192.168.1.119`, default route metric **100**) and `wlp2s0`
(race wifi, `192.168.100.205`, gateway `192.168.100.1`, metric **600**). The
derbynet path egresses via its **LTE uplink** — a public IP distinct from the
home ISP's, confirming the two uplinks are genuinely separate. Because ethernet
wins the default route, anything that must use the LTE link has to bind
`wlp2s0` explicitly.

## Open items / next steps

1. **Phase 2 (stalbert DB injection)** — get a VPS-capable key (or reuse the
   Pi's cloud-sync key if it permits arbitrary SSH), pull a consistent
   `.backup` snapshot of the stalbert tenant DB, back up the Pi's current DB,
   inject, and repoint `local/config-database.inc`.
2. **Apply §4 cloud-sync host-config fix** (optional, low-urgency).
3. **Validate the public-monitoring link** end-to-end once the cloud side is
   reachable.
4. Optionally delete `backup/local-analytics-2026-06-13` once confirmed unneeded.
