# Ad-Hoc Racing — Edge-Case & Hardening Backlog

Captured 2026-06-21 after ad-hoc ("come-as-you-are") mode was a **big success at
the 2026-06-20 Friday practice** (the official 2026-06-21 race day was
rain-cancelled). Owner wants ad-hoc to potentially become the **default mode for
practice days** — so the rough edges that less-rehearsed operators could hit on a
casual practice day are worth hardening first.

**Code is currently kept as-is — none of the below is implemented yet.** This is a
ranked to-do list. The mode itself is field-proven; the full feature spec and the
inline copy of this table live in [ADHOC.md](ADHOC.md).

## Why ad-hoc is already safe (no action needed)

The data-isolation design is solid: a **separate `adhoc.sqlite3`** selected by an
atomic, allowlisted, fail-safe-to-official marker (`inc/db-marker.inc`);
best-single-time per-age-group scoring; **PII-scrubbed** cloud surfacing (pinny +
time only). Confirmed already-handled: non-numeric / `0000` / blank pinny rejected,
leading-zero normalization, duplicate-in-same-heat dedup, byes / fewer racers than
lanes, single-racer heat, zero-racers rejected, DNF excluded from the leaderboard,
ties stably ordered, heat re-run (reinstate), server restart mid-ad-hoc (marker +
counters persist), kiosk + cloud surfacing.

## Backlog (ranked for practice-day-default readiness)

The gaps are **operator-error catches**, not data-safety bugs. Each needs code
verification before implementation.

| # | Case | Status today | Risk | Suggested hardening | Effort |
|---|------|--------------|------|---------------------|--------|
| 1 | **Enable ad-hoc while an official heat is armed/racing** | GAP — `action.adhoc.mode.inc` builds + flips the marker unconditionally | Marker flips immediately; the next result write lands in the ad-hoc DB instead of the official heat | Before `adhoc_build()`, refuse (or confirm) if `get_racing_state()` is non-zero or an official round has results | S |
| 2 | **Oversized pinny (e.g. `999999999`)** | GAP — server regex `^[0-9]+$` accepts any length | `display_pinny` stored full-width breaks the 4-digit `pinny_display()` assumption on kiosk + cloud | Cap at 4 digits / reject `> 9999` in both `coordinator-adhoc.js` and `adhoc_arm_heat()` | S |
| 3 | **Timer fires for a bye/unknown lane** | GAP — `write-heat-results.inc` silently ignores lanes with no RaceChart row | Silent data loss; operator never learns a time was dropped | Warn (`derby_log_warn`) when a reported lane has no entry for the heat | S |
| 4 | **Exit ad-hoc while an ad-hoc heat is armed/racing** | PARTIAL — exit stops racing state but gives no warning | Marker flips back to official; an in-flight ad-hoc heat is orphaned and its timer result is misrouted | In `coordinator-adhoc.js` exit, check poll `NowRacingState`; confirm "A heat is armed — exit anyway?" | M |
| 5 | **Same pinny re-entered under a different age group** | PARTIAL — allowed (legit for re-runs), no warning | Splits one car's results across two age-group leaderboards | On arm, warn if `display_pinny` previously raced under a different `agegroup_classid` | M |
| 6 | **Duplicate POST / browser refresh mid-heat-setup** | PARTIAL — arm increments the heat counter, so a re-POST mints a duplicate heat | Stray empty/duplicate heat in the feed | Idempotency token on the heat-setup form, or dedup identical consecutive arms | M |
| 7 | **Pinny collides with a real roster car number** | PARTIAL — roster-less model means no DB conflict, but the same printed number can mean two cars | Operator / spectator confusion if a roster pinny re-enters as an ad-hoc pinny | Optional: warn if `display_pinny` matches any official `RegistrationInfo.carnumber` | S |

**Recommended order:** #1 → #2 → #3 first (all small, high-value safety/clarity
catches), then #4 and #5 (operator-confirm polish). #6 and #7 are nice-to-have.

## Promoting ad-hoc to the practice-day default (separate from the above)

Not started — open question for whoever picks this up: where the default would be
expressed (a per-event flag? a build-time default? a practice-vs-competition event
type?), and how an operator opts back into rostered/elimination racing. Decide the
UX before wiring it. The hardening items above are prerequisites for trusting
ad-hoc as the unsupervised default.
