# Cloud Multi-Tenant (Per-Session Sandbox Databases)

On the cloud VPS only, each browser session picks its own SQLite database
("sandbox") on first arrival. Pi deployments are unaffected and continue to
use the single global `config-database.inc`.

## Where files live

- Tenant root: `${DERBYNET_TENANTS_DIR}` (default `/var/lib/derbynet/tenants`)
- One subdir per tenant, named by slug: `<tenants-root>/<slug>/`
- SQLite file: `<tenants-root>/<slug>/derbynet.sqlite3`
- Standard media subdirs (`racers/`, `cars/`, `videos/`, `logs/`, `imagery/`,
  `slides/`) are created at provisioning time

## Slug rules (security boundary)

`^[a-z0-9][a-z0-9-]{0,31}$` — lowercase alphanumerics and hyphens, first char
alphanumeric, 1–32 chars. Validated by `valid_tenant_slug()` in
`website/inc/cloud-tenant.inc`. **The slug is read from request input only at
selection/creation time**; for every subsequent request it comes from
`$_SESSION['tenant_slug']`.

## Resource limits

- `TENANT_MAX = 50` (`website/inc/cloud-tenant.inc`). Creation past the cap
  returns `cap-reached`.

## Operator tasks

- **Delete a sandbox:** `rm -rf /var/lib/derbynet/tenants/<slug>` on the VPS.
  Active sessions pointing at it will be redirected back to the picker on the
  next request.
- **List sandboxes:** `ls /var/lib/derbynet/tenants/` or hit `/action.php?query=tenant-list.nodata`.
- **Bulk prune idle:** none built in. Recommend a cron: anything where
  `derbynet.sqlite3 mtime > N days` is fair game.

## MQTT topic scheme (cloud-only)

The cloud broker is shared across every sandbox, so topic names have to
encode tenancy or sibling sandboxes will read each other's events. Cloud
publishes therefore use a tenant-prefixed scheme; the Pi keeps the legacy
unprefixed shape so real-hardware firmware is unaffected.

| Legacy (Pi, unchanged)                | Cloud (tenant-prefixed)                       |
| ------------------------------------- | --------------------------------------------- |
| `derbynet/race/state`                 | `derbynet/t/<slug>/race/state`                |
| `derbynet/race/time`                  | `derbynet/t/<slug>/race/time`                 |
| `derbynet/status` (server LWT)        | `derbynet/status` (still server-level) **and** `derbynet/t/<slug>/status` (per-tenant) |
| `derbynet/device/<hwid>/state`        | `derbynet/t/<slug>/device/<hwid>/state`       |
| `derbynet/device/<hwid>/telemetry`    | `derbynet/t/<slug>/device/<hwid>/telemetry`   |
| `derbynet/device/<hwid>/status`       | `derbynet/t/<slug>/device/<hwid>/status`      |
| `derbynet/lane/<n>/led`               | `derbynet/t/<slug>/lane/<n>/led`              |
| `derbynet/lane/<n>/pinny`             | `derbynet/t/<slug>/lane/<n>/pinny`            |
| `derbynet/ledsign/<zone>/message`     | `derbynet/t/<slug>/ledsign/<zone>/message`    |
| `derbynet/ledsign/broadcast`          | `derbynet/t/<slug>/ledsign/broadcast`         |
| `derbynet/alerts/<category>`          | `derbynet/t/<slug>/alerts/<category>`         |

`<slug>` is exactly the validated session tenant slug — it never appears
in a topic without first passing the regex above.

The race-server selects mode at boot via `DERBYNET_TENANT_MODE`:

- `multi` (cloud default in compose) — single MQTT connection subscribes
  `derbynet/t/+/device/+/{state,telemetry}` and dispatches each message to
  the matching `derbyRace` context. Per-tenant `DerbyDatabase`, API
  client (with the `X-DerbyNet-Tenant` header pair), and `AlertHandler`
  are created lazily on first sight of a known slug.
- unset / `single` (Pi default) — legacy single-class flow, legacy
  unprefixed topics, one process bound to one tenant via
  `DERBYNET_TENANT`.

## How sandbox isolation actually works

Three components have to agree, or sandboxes leak:

1. **Browser bridge.** `website/virtual/_guard.inc::virtual_active_tenant()`
   reads `$_SESSION['tenant_slug']` after the cloud-mode + permission gate
   runs. Each virtual page emits
   ```html
   <script>window.DERBYNET_TENANT = "<slug>";</script>
   ```
   *before* loading `virtual-common.js`.
   `VirtualCommon.topic('device', hwid, 'state')` then builds
   `derbynet/t/<slug>/device/<hwid>/state` and **throws** if the bridge
   wasn't emitted — silent global publishes are exactly the bug we're
   closing.
2. **Broker ACL.** `installer/docker-cloud/mosquitto/acl` constrains the
   `virtual-device` user to publish/subscribe only under `derbynet/t/+/...`.
   A leaked browser cred can target *any* tenant, but it cannot escape
   the prefix to write legacy real-hardware topics.
3. **Race-server router.** `derbyRace.RaceServer.on_message` parses the
   slug out of segment `[2]`, validates it against the same regex PHP
   uses (see slug-parity test below), and refuses to materialise a
   `RaceContext` for a slug whose `derbynet.sqlite3` doesn't exist on
   disk. Bad slug → message dropped with a warning, no DB write anywhere.

If any one of those three drifts, the others stop being load-bearing —
hence the parity test.

## Slug regex parity test

`testing/test-tenant-slug-parity.py` extracts the `TENANT_SLUG_RE` literal
from both `website/inc/cloud-tenant.inc` and
`extras/soapbox/infra/server/derbyRace.py`, runs a fixture set through
PHP's PCRE and Python's `re`, and exits non-zero on any disagreement.
Run it on every PR that touches either file:

```
python3 testing/test-tenant-slug-parity.py
```

Failure modes it catches: PHP accepts a slug Python rejects (browser
publishes are silently dropped by the router) or vice versa (PHP
provisions a sandbox the race-server refuses to address).

## Caveats / known limits

- **Roles are global.** `config-roles.inc` is shared across all tenants — the
  RaceCoordinator password is the same in every sandbox. Per-tenant role
  config would require moving role definitions into the tenant DB.
- **No race-day hardware on cloud.** Real timer firmware (Pi) talks on
  the unprefixed legacy topics; it must never connect to the cloud
  broker. Browser virtual hardware is the only cloud-side publisher and
  is gated to `derbynet/t/+/device/B_*/...` by ACL.
- **AJAX without a session** (e.g. someone scripting `action.php` from
  outside a browser) hits the same redirect-to-picker path as today's setup
  flow. Programmatic API users should obtain a session cookie first, or
  send the `X-DerbyNet-Tenant` + `X-DerbyNet-Internal-Token` header pair
  (Caddy strips both from external traffic).
