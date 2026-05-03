# Pull-Forward — Race-Day Operator Card

A one-page reference for the coordinator. For mechanics and edge cases see
[PULL_FORWARD.md](PULL_FORWARD.md).

## When to use it

Use pull-forward whenever a kid won't race their remaining heats and the
schedule still has unraced heats with empty lanes that need filling. An empty
lane on a 3-lane track is a wasted run.

## How to trigger it

1. Click the dropout button next to the racer on the **coordinator page**.
2. **First confirm** — *"Remove this racer from the schedule?"*
   - **OK**: continue.
   - **Cancel**: do nothing.
3. **Second confirm** — *"Pull forward a replacement?"*
   - **OK**: opens the pull-forward preview modal (recommended).
   - **Cancel**: removes the racer and leaves empty lanes (legacy behavior).

## The preview modal

Shows:
- Dropout racer name + car number, and how many gaps will be filled.
- A **Schedule Changes** table: which racer moves into which lane in which
  heat, and which later heat they came from.
- **Trailing Empty Lanes**: gaps that couldn't be filled (cascade reached the
  end of the schedule).
- **Fairness Warnings**: consecutive heats, repeat lane usage. Read these.
  They are not blocking — you decide whether to accept.

Three buttons:
- **Accept** — applies the changes silently.
- **Accept + Announce** — applies the changes *and* broadcasts a staging
  announcement (e.g. "Justin (#17) please report to staging - moved to
  Heat 5") to all kiosk displays for ~30 seconds.
- **Cancel** — close, no changes.

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
| Coordinator UI is unreachable / pull-forward modal errors | Fall back to plain dropout (Cancel on second confirm). Kiosks still update. Schedule is intact, just with empty lanes. |

## Quick checks before the event

- Open coordinator page; confirm the dropout flow shows **two** confirm
  dialogs (the second one is the pull-forward prompt).
- Trigger one dry-run pull-forward on a test racer. Confirm the modal
  populates and the broadcast announcement reaches the staging kiosk.
- Confirm the undo button appears after Accept and disappears after the
  next heat result.

## If something goes wrong mid-event

1. **Modal doesn't appear / second confirm missing** — pull-forward JS may not
   have loaded. Cancel the dropout and use plain dropout. File a post-event
   bug, don't try to debug live.
2. **"no_gaps" error** — the racer has no remaining unraced heats. They've
   already finished the round; nothing to pull forward.
3. **Undo failed with "has_results"** — at least one moved heat already
   raced. You can't undo. Treat the new schedule as authoritative.
4. **Broadcast didn't appear on kiosks** — kiosk poller may be stalled.
   Re-trigger via the broadcast tool or just re-announce verbally. The
   schedule change itself is already applied.

## Files behind this (for the technical lead)

- `website/inc/schedule-adjuster.inc` — algorithm
- `website/ajax/action.schedule.pullforward.inc` — AJAX endpoint
- `website/ajax/action.schedule.pullforward.undo.inc` — undo endpoint
- `website/js/coordinator-controls.js` — modal logic + dropout handler
- `website/js/coordinator-poll.js` — undo button render
- `testing/test-pull-forward.sh` — server tests (9 scenarios; Test 4 also asserts the broadcast message surfaces on the kiosk poll endpoint)
- `testing/puppeteer/pull-forward-test.js` — UI tests (11 scenarios)
