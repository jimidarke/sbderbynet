# Pull-Forward System

Handle last-minute driver withdrawals by pulling racers from later heats to fill empty lanes.

## Why This Exists

This is a kids' race. Kids get sick, scared, show up late, or just don't want to race anymore. The schedule is generated after check-in with only present racers, but things change between scheduling and racing. An empty lane on a 3-lane track is a wasted run and looks bad. The pull-forward system fills that gap by moving a racer from a later heat into the empty slot, then cascading that gap forward until it falls off the end of the schedule.

## How It Works

When a racer drops out mid-event, the coordinator has two options:

1. **Simple dropout** -- remove the racer, leave empty lanes (existing behavior)
2. **Pull forward** -- remove the racer and fill each gap from the nearest later heat

Pull-forward is a chain of positional swaps. No racer gains or loses races. If Bob drops from Heat 5, Justin moves from Heat 7 into Bob's slot. Justin's old slot in Heat 7 gets filled by someone from Heat 9. That gap cascades forward until it reaches the last heat, where it becomes a trailing bye (empty lane).

```
BEFORE:                        AFTER (Bob drops from Heat 5):

Heat 5: John, Bob, Sally       Heat 5: John, Justin, Sally    <-- Justin fills Bob's spot
Heat 6: Maria, Derek, Kim      Heat 6: Maria, Derek, Kim      (unchanged)
Heat 7: Justin, Pat, Lisa   -> Heat 7: Alex, Pat, Lisa        <-- Alex fills Justin's spot
Heat 8: Alex, Sam, Tony        Heat 8: [bye], Sam, Tony       <-- trailing bye
```

> **Hardware handling of bye lanes (race server v0.9.3+):** A bye is not written
> to `RaceChart`, so the coordinator poll only reports the populated lanes — and
> the empty slot can land in **any** lane (the `[bye]` above is lane 1, not the
> last lane). The race server treats the **physical** lane count
> (`RaceInfo.lane_count`) as the source of truth for the display: it publishes a
> pinny to every physical lane each heat, showing `"----"` on the empty lane so
> the finish timer never displays a stale number from a previous heat. Race
> completion counts only the **populated** lanes, so the heat finishes without
> waiting on the empty lane. See the race server `derbyRace.py` changelog and
> [COORDINATOR_POLL_API.md](COORDINATOR_POLL_API.md) (`race_info.lane_count`).

---

## Use Cases

### UC-1: Mid-Event Dropout (Primary Case)

**Situation:** Racing is underway. A racer scheduled for upcoming heats can no longer race.

**Trigger:** Coordinator taps **Pull Forward…** in the running round's
control block on the coordinator page. This opens a dedicated tablet-friendly
page (`pull-forward.php`).

**Flow:**
1. The page lists racers in the running round who still have unraced heats,
   sorted by car number, with a badge showing remaining heat count.
2. Coordinator taps the dropout racer. The page runs a dry-run pull-forward
   against current chart state and renders the simulated result inline.
3. The simulation is faithful: the same `pull_forward()` algorithm runs again
   on Apply, against current state — so what's previewed is what will commit
   (modulo any heat that completes between preview and Apply, which the
   server handles correctly by re-deriving the moves).
4. Coordinator taps **Apply** or **Apply + Announce** (broadcasts to
   staging area), or **Discard** to abort.
5. On success: schedule updates atomically; coordinator page reloads with
   the **Undo Pull Forward** button briefly highlighted.

**Outcome:** Every heat stays full (or as full as possible). Pulled racers race earlier than originally scheduled. The gap cascades to the tail of the schedule.

### UC-2: Dropout with Partial Results

**Situation:** Racer completed Heats 1 and 3 but is scheduled for Heats 5 and 7. They can't continue.

**What happens:** Only the unraced heats (5, 7) are affected. Completed results are immutable. The system finds gaps only in heats where `finishtime IS NULL`, fills those by pulling forward, and leaves the completed heats untouched.

### UC-3: Multiple Dropouts

**Situation:** Two kids drop out within a few minutes of each other.

**What happens:** Each pull-forward is a separate operation. The coordinator triggers them sequentially. The second pull-forward sees the already-modified schedule (from the first) and fills gaps accordingly. The system handles this naturally because it always works on the current state of the race chart.

### UC-4: Dropout Near End of Schedule

**Situation:** A racer drops out with only 1-2 heats remaining in the round.

**What happens:** There may not be enough later heats to pull from. The system fills what it can. Any remaining gaps become trailing byes (empty lanes). This is acceptable since the event is nearly over.

### UC-5: Dropout from Final Heat

**Situation:** Racer drops from the very last heat. No later heats exist.

**What happens:** No pull-forward is possible. The gap stays as a bye. The preview modal shows zero moves and the trailing bye. The coordinator can still accept (to remove the racer and record the state) or cancel and use DNF instead.

### UC-6: Racer Returns After Dropout

**Situation:** A kid was pulled from the schedule but changes their mind and wants to race.

**If no affected heats have run yet:** Coordinator clicks "Undo Pull Forward" to restore the original schedule exactly as it was.

**If affected heats have already run:** Undo is no longer possible. The racer must be re-added using the existing "Add Latecomer" / reschedule flow (`inject_new_racer`), which finds slots in unraced heats.

### UC-7: Current-Heat Dropout (Start Line Refusal)

**Situation:** Racer is at the start line and refuses to go. The heat is about to run.

**What happens:** Pull-forward is not practical here -- there's no time. Use the existing DNF mechanism. Mark the racer's current heat as DNF. If they have future heats, the coordinator can then trigger pull-forward for those remaining heats.

### UC-8: Pre-Race Dropout (Before Any Heats Run)

**Situation:** A racer drops out before the first heat is run.

**What happens:** The existing `handle_racer_dropout()` path is cleaner in this case -- it deletes the racer from the chart and triggers a full reschedule with optimal weighting. Pull-forward is designed for mid-event use when a full reschedule would disrupt already-recorded results.

### UC-9: Dropout with Broadcast

**Situation:** Coordinator pulls forward a replacement and needs the staging crew to know about the change.

**What happens:** Clicking "Accept + Announce" sends a broadcast message (e.g., "Justin (#17) please report to staging - moved to Heat 5") that appears on all kiosk displays for 30 seconds. This uses the existing broadcast messaging system.

---

## Coordinator Workflow

```
Coordinator taps "Pull Forward…" on the running round (coordinator.php)
         |
         v
  pull-forward.php opens — roster of racers with unraced heats
         |
         v
  Coordinator taps a racer
         |
         v
  Inline simulated result appears below the roster
  +-----------------------------------------------+
  | PULL FORWARD - Fill Schedule Gaps              |
  |                                                |
  | Dropout: Bob Smith (#42) - 2 gap(s) to fill   |
  |                                                |
  | Schedule Changes:                              |
  | Fill Heat | Lane | Racer Moved    | From Heat  |
  | Heat 5    | 2    | Justin (#17)   | Heat 7     |
  | Heat 7    | 1    | Alex (#31)     | Heat 9     |
  |                                                |
  | Remaining Empty Lanes:                         |
  | Heat 9 Lane 1                                  |
  |                                                |
  | Fairness Warnings:                             |
  | ! Justin races in consecutive heats 4 and 5   |
  |                                                |
  | [Apply]  [Apply + Announce]  [Discard]         |
  +-----------------------------------------------+
         |
         v
  Schedule updated. Kiosks reload. Coordinator page returns with
  "Undo Pull Forward" button briefly pulsed for visibility.
  Undo is available until any affected heat records results.
```

---

## Algorithm

The pull-forward algorithm runs in 5 phases:

### Phase 1: Identify Gaps
Find all unraced heats containing the dropout racer. Remove them (create byes). Sort by heat number ascending so the soonest gaps are filled first.

### Phase 2: Fill Each Gap
For each gap at (Heat H, Lane L), search later heats for the best candidate:

- **Hard constraint:** Candidate must not already be in Heat H
- **Proximity score:** Prefer the closest later heat (lower distance = better)
- **Windowed rest penalty:** Same shape as initial scheduling (`schedule_ordered.inc`).
  For each `d` in `1..min_heat_gap-1`, if the candidate already races in heat
  `H-d` or `H+d`, add `5000 × (min_heat_gap - d + 1) / min_heat_gap` to the
  score. Back-to-back (`d=1`) costs the full 5000 — matching legacy behaviour
  for classes where `min_heat_gap = 0` collapses the window to 2.
- **Lane penalty (+200):** Candidate already used Lane L in another heat

Select the best-scoring candidate. Move them into the gap. Their old slot becomes a new gap.

The `min_heat_gap` value is read from the round's class (`Classes.min_heat_gap`)
so pull-forward stays consistent with however that class was initially
scheduled. When the algorithm can't honour the window (typical near the tail
of the schedule), the soft penalty just biases against the worst options
rather than refusing to fill the gap — a `gap-too-tight` fairness warning
surfaces so the coordinator sees the trade-off before tapping Apply.

### Phase 3: Cascade
Repeat Phase 2 for each newly created gap. The cascade propagates forward through the schedule until no candidates remain (gap reaches the last heat). No depth limit.

### Phase 4: Compression
Run `squeeze_out_byes()` to dissolve any heats that are entirely empty. Renumber heats if needed to keep numbering contiguous.

### Phase 5: Validation
Verify no racer appears twice in any single heat. Report fairness warnings (consecutive races, lane repeats) to the coordinator for review.

---

## Fairness

Pull-forward intentionally disrupts the optimized schedule. The original scheduling weights (avoid_consecutive=5000, avoid_same_lane=200, group_weighted_cars=100, plus the per-class `min_heat_gap`) produced a carefully balanced heat chart, and pull-forward will violate some of those constraints. This is accepted because:

- An empty lane is worse than a slightly imbalanced schedule
- The alternative (full reschedule) would invalidate already-recorded results
- The system warns the coordinator about specific violations so they can make informed decisions
- Race counts stay the same for every racer -- pull-forward is positional, not additive

---

## Undo

Every pull-forward stores a snapshot of the unraced chart before making changes. The "Undo Pull Forward" button appears in the coordinator UI and restores the exact original schedule.

**Undo is available** until any affected heat records results (finishtime or finishplace). Once a heat that was touched by the pull-forward gets raced, undo is no longer possible and the button disappears.

Undo also restores the dropout racer's `passedinspection` flag so they can be rescheduled.

---

## Files

| File | Role |
|---|---|
| `website/inc/schedule-adjuster.inc` | `ScheduleAdjuster` class with `pull_forward()`, scoring, and snapshot methods |
| `website/ajax/action.schedule.pullforward.inc` | AJAX endpoint: dry-run preview and execute |
| `website/ajax/action.schedule.pullforward.undo.inc` | AJAX endpoint: undo |
| `website/pull-forward.php` | Dedicated operator page (primary entry) — roster query, layout |
| `website/js/pull-forward.js` | Page logic: `pfSelectRacer()`, `renderProposal()`, `pfApply()`, `pfDiscard()` |
| `website/css/pull-forward.css` | Portrait-tablet styling, sticky action bar |
| `website/coordinator.php` | Deprecated pull-forward modal HTML (one-release fallback) |
| `website/js/coordinator-controls.js` | Deprecated modal helpers + `undoPullForward()` |
| `website/js/coordinator-poll.js` | "Pull Forward…" entry button + Undo button rendering |
| `website/css/coordinator.css` | Entry / undo button styles, post-apply pulse animation |
| `website/inc/events.inc` | `EVENT_PULL_FORWARD` (501), `EVENT_PULL_FORWARD_UNDO` (502) |
| `testing/test-pull-forward.sh` | Integration test suite (9 scenarios) |
| `testing/puppeteer/pull-forward-test.js` | Puppeteer UI test suite (11 scenarios) |

## API

### `schedule.pullforward` (POST)

| Parameter | Required | Description |
|---|---|---|
| `roundid` | Yes | Round to operate on |
| `dropout_racerid` | Yes | Racer being removed |
| `dry-run` | No | If truthy, return preview without committing |
| `send_broadcast` | No | If truthy, send staging announcement on execute |
| `trace` | No | If truthy, include algorithm trace in response |

**Response:** `proposal` object with `dropout`, `moves[]`, `trailing_byes[]`, `warnings[]`, `heats_affected`. On execute: `undo_available: true`.

### `schedule.pullforward.undo` (POST)

| Parameter | Required | Description |
|---|---|---|
| `roundid` | Yes | Round to restore |

**Fails with `has_results`** if any affected heat has recorded results since the pull-forward.

---

## Test Scenarios

### Integration Tests (Server-Side)

The integration test (`testing/test-pull-forward.sh`) exercises the PHP backend via curl:

| # | Scenario | Validates |
|---|----------|-----------|
| 1 | Dry-run preview | Proposal structure, schedule unchanged |
| 2 | Execute pull-forward | Moves applied, undo data available |
| 3 | Undo | Schedule restored, undo data cleared |
| 4 | Execute with broadcast | Broadcast message sent alongside changes |
| 5 | Already-removed racer | Returns `no_gaps` error |
| 6 | Undo after results recorded | Graceful failure when heats already raced |
| 7 | Multiple sequential dropouts | Two dropouts in a row, schedule stays valid |
| 8 | Minimal racers (3 on 3 lanes) | Trailing byes when no one to pull forward |
| 9 | Permission check | Non-coordinator role gets `notauthorized` |

Run with:
```bash
./testing/test-pull-forward.sh http://localhost:8080
```

### UI Tests (Frontend)

The Puppeteer test (`testing/puppeteer/pull-forward-test.js`) exercises the coordinator UI using mocked AJAX responses:

| # | Scenario | Validates |
|---|----------|-----------|
| 1 | Modal populates correctly | Dropout info, moves table, trailing byes, and warnings render from proposal data |
| 2 | Empty proposal | "No racers available" message when no candidates exist |
| 3 | Clean proposal | Warnings and trailing byes sections hidden when empty |
| 4 | Cancel button | Modal closes without triggering any AJAX call |
| 5 | Accept button | Sends `schedule.pullforward` with `dry-run: false`, `send_broadcast: 0` |
| 6 | Accept + Announce | Sends `send_broadcast: 1` flag |
| 7 | showPullForwardModal | Sends dry-run AJAX and opens modal with response |
| 8 | Undo button appears | Renders when poll data includes `pull-forward-undo` |
| 9 | Undo button absent | Hidden when poll has no `pull-forward-undo` |
| 10 | Undo button click | Sends `schedule.pullforward.undo` with correct roundid |
| 11 | Modal re-population | Clears stale data when showing a new proposal |
| 11b | `gap-too-tight` warning rendering | Warning text includes gap (e.g. "within 3 heats") and the class-min ("class minimum is 6"), and does *not* render as a legacy consecutive warning |

Run with:
```bash
node testing/puppeteer/pull-forward-test.js http://localhost/derbynet
```
