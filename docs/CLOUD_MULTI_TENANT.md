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

## Caveats / known limits

- **Roles are global.** `config-roles.inc` is shared across all tenants — the
  RaceCoordinator password is the same in every sandbox. Per-tenant role
  config would require moving role definitions into the tenant DB.
- **No race-day hardware on cloud.** The Python race server, MQTT bridges,
  and finish-timer hardware never run on cloud; they remain single-DB on
  the Pi via `DERBYNET_DB_PATH`.
- **AJAX without a session** (e.g. someone scripting `action.php` from
  outside a browser) hits the same redirect-to-picker path as today's setup
  flow. Programmatic API users should obtain a session cookie first.
