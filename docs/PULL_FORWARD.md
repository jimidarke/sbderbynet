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

---

## Use Cases

### UC-1: Mid-Event Dropout (Primary Case)

**Situation:** Racing is underway. A racer scheduled for upcoming heats can no longer race.

**Trigger:** Coordinator clicks the dropout button on the coordinator page.

**Flow:**
1. System asks: "Remove this racer from the schedule?"
2. System asks: "Pull forward a replacement from upcoming heats?"
3. If yes: preview modal shows which racers move where, any fairness warnings, and trailing byes
4. Coordinator clicks "Accept" or "Accept + Announce" (broadcasts to staging area)
5. Schedule updates atomically. All kiosk displays reload.

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
Coordinator clicks "Dropout" on a racer
         |
         v
   "Remove from schedule?"
    Yes /          \ No
       /            \ (cancel, no action)
      v
   "Pull forward a replacement?"
    Yes /              \ No
       /                \ (standard dropout -- empty lanes)
      v
  Preview Modal
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
  | [Accept]  [Accept + Announce]  [Cancel]        |
  +-----------------------------------------------+
         |
         v
  Schedule updated. Kiosks reload.
  "Undo Pull Forward" button appears until affected heats record results.
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
- **Consecutive penalty (+5000):** Candidate would race back-to-back (in Heat H-1 or H+1)
- **Lane penalty (+200):** Candidate already used Lane L in another heat

Select the best-scoring candidate. Move them into the gap. Their old slot becomes a new gap.

### Phase 3: Cascade
Repeat Phase 2 for each newly created gap. The cascade propagates forward through the schedule until no candidates remain (gap reaches the last heat). No depth limit.

### Phase 4: Compression
Run `squeeze_out_byes()` to dissolve any heats that are entirely empty. Renumber heats if needed to keep numbering contiguous.

### Phase 5: Validation
Verify no racer appears twice in any single heat. Report fairness warnings (consecutive races, lane repeats) to the coordinator for review.

---

## Fairness

Pull-forward intentionally disrupts the optimized schedule. The original scheduling weights (avoid_consecutive=5000, avoid_same_lane=200, group_weighted_cars=100) produced a carefully balanced heat chart, and pull-forward will violate some of those constraints. This is accepted because:

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
| `website/coordinator.php` | Pull-forward preview modal HTML |
| `website/js/coordinator-controls.js` | `showPullForwardModal()`, `executePullForward()`, `undoPullForward()` |
| `website/js/coordinator-poll.js` | Undo button rendering from poll data |
| `website/css/coordinator.css` | Modal and button styles |
| `website/inc/events.inc` | `EVENT_PULL_FORWARD` (501), `EVENT_PULL_FORWARD_UNDO` (502) |
| `testing/test-pull-forward.sh` | Integration test suite (9 scenarios) |

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

The integration test (`testing/test-pull-forward.sh`) covers:

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
