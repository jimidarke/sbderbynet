# Kiosk display system

How the SBDerbyNet kiosk pages are styled, what rules every kiosk follows,
and where to look when one of them is misbehaving.

## Why this exists

There are 22 kiosk templates under `website/kiosks/*.kiosk`. Until recently
each one duplicated the same boilerplate (body shell, font stack, banner
height math, table sizing) and the duplications had drifted — different
banner-height literals in different files, conflicting `overflow` rules
between body and wrappers, occasional `table-layout: fixed` declarations
that caused racer names to wrap and inflate rows past the viewport.

The fix was structural: promote `css/kiosks.css` into a **canonical kiosk
base** and make per-kiosk CSS layout-only.

## The central stylesheet — `css/kiosks.css`

Loaded by every kiosk (directly via `<link>` or transitively via dispatch
to `ondeck.php` / `racer-results.php`). Provides:

| Section | What it gives every kiosk |
|---|---|
| **`:root` tokens** | `--banner-h: 64px` (matches `global.css` banner), `--status-bar-h: 6vh`, brand/accent colours, ink/surface/rule colours, race-state colours (`--state-stage`, `--state-race`, `--state-pause`, `--state-fault`). |
| **`body.kiosk`** | The single-viewport shell: `margin: 0`, `height: 100vh`, `overflow: hidden`, system font stack, tabular-nums by default. Hides legacy `.banner_version` / `.aside`. |
| **`.kiosk-stage`** | Below-banner area: `height: calc(100vh - var(--banner-h))`, `overflow: hidden`. `.kiosk-stage--with-statusbar` subtracts both banner + status bar. |
| **`.kiosk-statusbar`** | Race-state strip with `data-state="staging|racing|paused|fault"` driving colour. Used by now-racing today; available for any kiosk. |
| **`.kiosk-table`** | Default table primitive — auto layout (never `fixed`), tabular-nums, alternating-row background, brand-coloured `<th>`. |
| **Identity guardrail** | `.kiosk-table td.identity` (and the standalone `.kiosk-cell-identity` class) gets `white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 1px`. Long names truncate; rows never inflate. |
| **Numeric guardrail** | `td.numeric` / `.kiosk-cell-numeric`: right-aligned tabular nums, no-wrap. |
| **`.kiosk-card`** | Surface for racer/result cards — radius, border, shadow tokens. |
| **Type helpers** | `.kiosk-num` (tabular-nums), `.kiosk-eyebrow` (small uppercase label). |

### Hard rules every kiosk follows

1. **One viewport, no scroll.** `body.kiosk` is `100vh × 100vw` with
   `overflow: hidden`. If content doesn't fit, fix the layout — never
   add a scrollbar.
2. **Banner height has one source of truth.** Use `var(--banner-h)`,
   never the literal `64px`.
3. **Identity columns never wrap.** Tag racer-name / racer-label cells
   with `class="identity"` (or apply `td.name` styles in now-racing). The
   guardrail makes the previous `table-layout: fixed` regression
   structurally impossible.
4. **No `table-layout: fixed`** on `.kiosk-table` by default. Opt in with
   `<colgroup>` if a specific kiosk needs explicit column widths.

## Per-kiosk file map

| Kiosk template | Backing PHP / include | Per-kiosk CSS |
|---|---|---|
| `now-racing.kiosk` | self-contained | `css/now-racing.css` |
| `now-racing-columnar.kiosk`, `…-reversed.kiosk` | `inc/columnar-now-racing.inc` | `css/now-racing-columnar.css` |
| `ondeck.kiosk` | `ondeck.php` (`$as_kiosk = true`) | `css/ondeck.css` |
| `results-by-racer.kiosk` | `racer-results.php` (`$as_kiosk = true`) | `css/racer-results.css` |
| `elimination-results.kiosk`, `elimination-standings.kiosk` | self-contained | `css/elimination-kiosks.css` |
| `standings.kiosk` | self-contained | (none — uses base) |
| `award-presentations.kiosk` | self-contained | `css/award-presentations-kiosk.css` |
| `welcome.kiosk`, `map.kiosk`, `rules.kiosk`, `flag.kiosk`, `derbynet.kiosk`, `identify.kiosk`, `qrcode.kiosk`, `scale-MPH.kiosk`, `please-check-in.kiosk` | self-contained | (legacy `.full_page_center` / `.kiosk_title` / `.kiosk_heading` from base) |
| `intermission.kiosk`, `slideshow.kiosk`, `sponsors.kiosk` | `shared-slideshow.php` | `css/slideshow.css` |
| `hls-video-stream.kiosk` | self-contained | (inline style — fullscreen video) |

## Race-state status bar

Used by `now-racing.kiosk` today via `<div id="race-status-bar" data-state="…">`.
JS in `js/now-racing.js → updateRaceStatusDisplay()` sets the `data-state`
attribute based on the polled timer state:

| `data-state` | Meaning | Colour |
|---|---|---|
| `idle` | No active heat / waiting | `--state-idle` (grey) |
| `staging` | Cars on the line | `--state-stage` (amber) |
| `racing` | Heat in progress | `--state-race` (green) |
| `paused` | Operator paused | `--state-pause` (grey) |
| `fault` | Timer trouble | `--state-fault` (red, pulsing) |

Any other kiosk wanting the same indicator can adopt the
`.kiosk-statusbar` class instead of redefining `#race-status-bar`.

## Results-by-racer paginator

`js/results-by-racer-paginator.js` builds racer cards from the new
`racer_summaries` block on `query=poll.results` (see
`docs/COORDINATOR_POLL_API.md`), sorts by car number, and paginates to fit
the viewport with an 8 s auto-advance and 400 ms cross-fade. Banner
height is read from `--banner-h` via `getComputedStyle`, so changing the
banner height in `css/kiosks.css` (and `global.css`) is the only place
that needs to know.

## What's intentionally untouched

These kiosks have their own viewport models and were left alone in this
pass — touching them is its own change with its own risk profile.

- `kiosk-dashboard.css` — coordinator-only control panel, not a public
  kiosk.
- `hls-video-stream.kiosk` — fullscreen video uses absolute positioning
  by design.
- `slideshow.css` (intermission / slideshow / sponsors) — image-carrier
  with intentional absolute-px offsets for caption positioning.
- `now-racing-columnar.css` — already viewport-disciplined with `vh`
  units; structurally different from the row-oriented main board.
- `please-check-in.kiosk` JS column reflow — the hardcoded `top: 128px`
  was removed from the redesign target list because reworking the JS
  reflow logic alongside the CSS migration is out of scope for one pass.

## Follow-up items

Open at the end of 2026-05-09:

1. **`please-check-in.kiosk` `top: 128px`** — replace with
   `top: calc(var(--banner-h) + 4rem)` so it tracks banner-height
   changes. Also audit the JS column-fit reflow loop for Pi performance.
2. **`elimination-kiosks.css` brand-token adoption** — only the
   `.standings-container` `calc()` was migrated. The hardcoded
   `#1e3c72`, `#2a5298`, `#28a745`, `#dc3545` should move to
   `--brand` / `--state-race` / `--state-fault` for consistency. Cosmetic
   only; no behaviour change.
3. **Slideshow caption offsets** — `slideshow.css` uses `bottom: 10px` /
   `bottom: 50px` literals. Convert to `vh` for consistency with other
   kiosks.
4. **Visual smoke pass on Pi** — verify each kiosk on an actual Pi-driven
   TV at 720p and 1080p; confirm no scrollbars, no clipped rows. We've
   only validated 1080p Chromium so far.
5. **Tournament rehearsal** — drive an elimination tournament through one
   round and confirm `elim-results` / `elim-standings` still render
   correctly with the new `.standings-container` calc.
6. **Possible: `body.kiosk` adoption for the slideshow/intermission/
   sponsors set** — they currently bypass the central body shell. Low
   priority; their existing layout works.

## Verification recipes

- **Static syntax**: `php -l website/<file>` per modified PHP/kiosk;
  `node -c website/js/<file>` per modified JS.
- **Curl smoke**: `bash testing/test-visit-each-page.sh <BASE_URL>`
  (returns non-zero if any kiosk emits a PHP `Notice|Warning|Fatal`).
- **Visual at the cloud**: open
  `https://uisp.darketech.ca/derbynet/kiosk.php?name=<kiosk-name>` for
  each, with `Ctrl+Shift+R` to bust the CSS cache.
- **Dry-run before deploy**: `bash scripts/derbyvps.sh deploy --dry-run`
  to preview the rsync file list.

## Backup tags from this work

| Tag | Purpose |
|---|---|
| `deploy-20260509-171357` | Initial kiosk refresh (now-racing, ondeck, results-by-racer paginator). |
| `deploy-20260509-171940` | Fix for `table-layout: fixed` name-wrap regression on now-racing. |
| `deploy-20260509-175758` | Central kiosk stylesheet + viewport-discipline guardrails (this doc). |

Rollback any of them with `bash scripts/derbyvps.sh rollback <tag>`.
