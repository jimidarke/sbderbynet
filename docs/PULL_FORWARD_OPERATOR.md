# Pull-Forward — Race-Day Operator Card

A one-page reference for the coordinator. For mechanics and edge cases see
[PULL_FORWARD.md](PULL_FORWARD.md).

## When to use it

Use pull-forward whenever a kid won't race their remaining heats and the
schedule still has unraced heats with empty lanes that need filling. An empty
lane on a 3-lane track is a wasted run.

## How to trigger it

1. On the **coordinator page**, in the running round's control block, tap
   **Pull Forward…**. This opens the dedicated `pull-forward.php` page.
2. The page shows the **roster of racers with unraced heats remaining** in
   the running round, sorted by car number, with a badge showing how many
   heats each racer still has.
3. Tap the row of the racer who is dropping out. The page runs a server-side
   simulation (dry-run) and renders the result inline below the roster.
4. Review the simulation, then tap one of the action buttons at the bottom.

## The simulated result

Shows:
- Dropout racer name + car number, and how many gaps will be filled.
- A **Schedule Changes** table: which racer moves into which lane in which
  heat, and which later heat they came from.
- **Empty Lanes After Pull-Forward**: gaps that couldn't be filled (cascade
  reached the end of the schedule).
- **Fairness Warnings**: consecutive heats, repeat lane usage. Read these.
  They are not blocking — you decide whether to accept.
- A side-effect note: applying will also un-check inspection for the dropout
  racer, so they cannot be re-scheduled by mistake.

You can tap a different racer at any time to re-simulate; nothing is
committed until you tap Apply.

Three buttons at the bottom (large, sticky):
- **Apply** — commits the changes and returns you to the coordinator page.
- **Apply + Announce** — commits *and* broadcasts a staging announcement
  (e.g. "Justin (#17) please report to staging - moved to Heat 5") to all
  kiosk displays for ~30 seconds.
- **Discard** — returns to the coordinator page without changes.

After Apply, the coordinator page briefly highlights the **Undo Pull
Forward** button so you can verify and revert if surprised.

## Undo

After Accept, an **Undo Pull Forward** button appears in the round controls.

**Undo is available** until any moved heat records a result. Once a heat
that was touched by the pull-forward gets raced, the button **disappears
silently** — undo is no longer possible. Hovering shows the same rule.

If a kid changes their mind after the undo window has closed, use the existing
**Add Latecomer / reschedule** flow (`inject_new_racer`) instead.

## When pull-forward isn't the right tool

| Situation | Use instead |
|---|---|
| Racer is at the start line, refuses to go, heat is about to run | **DNF** the heat, then pull-forward their *future* heats |
| Pre-event dropout (no heats run yet) | Standard `racer.dropout` — full reschedule is cleaner |
| Last heat of the round | Pull-forward shows zero moves; just accept to record the dropout, or use DNF |
| Pull-forward page errors / unreachable | Open browser devtools on coordinator.php and call `showPullForwardModal(<racerid>, <roundid>)` — the deprecated modal is retained one release as a fallback. |

## Quick checks before the event

- Open the coordinator page on the operator tablet in **portrait** orientation.
  Confirm the **Pull Forward…** button appears in the running round's control
  block once a heat has been raced.
- Tap it. Confirm `pull-forward.php` loads, lists the roster sorted by car
  number, and tap targets are large enough for one-thumb operation.
- Pick a test racer; confirm the simulation renders inline. Tap **Apply +
  Announce** and confirm: (a) you land back on the coordinator page,
  (b) the schedule reflects the move, (c) the **Undo Pull Forward** button
  pulses briefly, (d) the broadcast appears on the staging kiosk.
- Race a heat that was touched by the pull-forward; confirm the undo button
  disappears.

## If something goes wrong mid-event

1. **Pull Forward… button missing on coordinator** — the round may not be the
   running round, or all heats have already raced. Confirm the round is
   selected and at least one unraced heat remains.
2. **Page shows "No active round"** — set a round on the coordinator page
   first.
3. **"No remaining heats" inline message** — the selected racer has no unraced
   heats. Pick a different racer or hit the back button.
4. **Apply error banner** — schedule was NOT changed. Re-tap the racer and
   try Apply again. If it persists, fall back to the deprecated modal via
   devtools (see table above).
5. **Undo failed with "has_results"** — at least one moved heat already
   raced. You can't undo. Treat the new schedule as authoritative.
6. **Broadcast didn't appear on kiosks** — kiosk poller may be stalled.
   Re-trigger via the broadcast tool or just re-announce verbally. The
   schedule change itself is already applied.

## Files behind this (for the technical lead)

- `website/inc/schedule-adjuster.inc` — algorithm
- `website/ajax/action.schedule.pullforward.inc` — AJAX endpoint (dry-run + execute)
- `website/ajax/action.schedule.pullforward.undo.inc` — undo endpoint
- `website/pull-forward.php` — dedicated operator page (primary entry)
- `website/js/pull-forward.js` — page logic (selection, simulation, apply)
- `website/css/pull-forward.css` — portrait-tablet styling
- `website/js/coordinator-poll.js` — entry button render + undo button render
- `website/js/coordinator-controls.js` — deprecated modal helpers (one-release fallback)
- `testing/test-pull-forward.sh` — server tests (9 scenarios; Test 4 also asserts the broadcast message surfaces on the kiosk poll endpoint)
- `testing/puppeteer/pull-forward-test.js` — UI tests (page-driven scenarios + simulation-fidelity check)
