# Pull-Forward

Handle last-minute driver withdrawals by pulling racers from later heats to fill empty lanes.

=== "Operator quick-card"

    ## When to use it

    Whenever a kid won't race their remaining heats and the schedule still has unraced heats with empty lanes. An empty lane on a 3-lane track is a wasted run.

    ## Trigger it

    1. On the **coordinator page**, in the running round's control block, tap **Pull Forward…**. This opens the dedicated `pull-forward.php` page.
    2. The page lists racers in the running round who still have unraced heats, sorted by car number, with a badge showing how many heats each racer still has.
    3. Tap the row of the racer who is dropping out. Server-side simulation (dry-run) runs and renders inline below the roster.
    4. Review, then tap an action button.

    ![Pull-forward operator page — TODO screenshot](../images/placeholder-pullforward-operator.png)

    ## The simulated result

    Shows:

    - Dropout racer name + car number, and how many gaps will be filled.
    - **Schedule Changes** table: which racer moves into which lane in which heat, and which later heat they came from.
    - **Empty Lanes After Pull-Forward**: gaps that couldn't be filled.
    - **Fairness Warnings**: consecutive heats, repeat lane usage. Read these — they're not blocking; you decide.
    - A side-effect note: applying un-checks inspection for the dropout racer, so they can't be rescheduled by mistake.

    Tap a different racer at any time to re-simulate; nothing commits until **Apply**.

    Three sticky buttons:

    - **Apply** — commit and return to coordinator page.
    - **Apply + Announce** — commit *and* broadcast a staging announcement (e.g. *"Justin (#17) please report to staging - moved to Heat 5"*) on all kiosk displays for ~30 s.
    - **Discard** — return without changes.

    After Apply, the coordinator page briefly highlights **Undo Pull Forward** so you can verify and revert if surprised.

    ## Undo

    Available until any moved heat records a result. Once a touched heat is raced, the button **disappears silently**. After that, use the **Add Latecomer / reschedule** flow (`inject_new_racer`) if a kid changes their mind.

    ## When pull-forward isn't the right tool

    | Situation | Use instead |
    |---|---|
    | Racer at the start line, refuses to go, heat about to run | **DNF** the heat, then pull-forward their *future* heats |
    | Pre-event dropout (no heats run) | Standard `racer.dropout` — full reschedule is cleaner |
    | Last heat of the round | Pull-forward shows zero moves; just accept to record the dropout, or use DNF |
    | Pull-forward page errors / unreachable | DevTools on coordinator.php → call `showPullForwardModal(<racerid>, <roundid>)` — deprecated modal retained one release as fallback |

    ## Pre-event quick checks

    - Open the coordinator page on the operator tablet in **portrait**. Confirm **Pull Forward…** appears in the running round's control block once a heat has been raced.
    - Tap it. Confirm `pull-forward.php` loads, lists the roster sorted by car number, and tap targets are large enough for one-thumb operation.
    - Pick a test racer; confirm the simulation renders inline. Tap **Apply + Announce** and confirm: you land back on the coordinator page, the schedule reflects the move, **Undo Pull Forward** pulses briefly, the broadcast appears on the staging kiosk.
    - Race a heat that was touched by the pull-forward; confirm the undo button disappears.

    ## If something goes wrong

    1. **Pull Forward… button missing** — round isn't the running round, or all heats raced. Select round, ensure at least one unraced heat remains.
    2. **"No active round"** — set a round on the coordinator page first.
    3. **"No remaining heats" inline message** — selected racer has no unraced heats. Pick a different one.
    4. **Apply error banner** — schedule was NOT changed. Retry. Persists ⇒ deprecated-modal fallback (devtools).
    5. **Undo failed with `has_results`** — at least one moved heat already raced; can't undo. Treat the new schedule as authoritative.
    6. **Broadcast didn't appear on kiosks** — kiosk poller stalled. Re-trigger via broadcast tool or announce verbally. The schedule change itself is applied.

=== "Technical reference"

    ## Why this exists

    This is a kids' race. Kids get sick, scared, show up late, or just don't want to race. The schedule is generated after check-in with only present racers, but things change between scheduling and racing. An empty lane on a 3-lane track is a wasted run and looks bad. Pull-forward fills that gap by moving a racer from a later heat into the empty slot, then cascading the gap forward until it falls off the end of the schedule.

    ## How it works

    Pull-forward is a chain of positional swaps. No racer gains or loses races. If Bob drops from Heat 5, Justin moves from Heat 7 into Bob's slot. Justin's old slot in Heat 7 gets filled by someone from Heat 9. That gap cascades forward until it reaches the last heat, where it becomes a trailing bye.

    ```
    BEFORE:                        AFTER (Bob drops from Heat 5):

    Heat 5: John, Bob, Sally       Heat 5: John, Justin, Sally    <-- Justin fills Bob
    Heat 6: Maria, Derek, Kim      Heat 6: Maria, Derek, Kim      (unchanged)
    Heat 7: Justin, Pat, Lisa   -> Heat 7: Alex, Pat, Lisa        <-- Alex fills Justin
    Heat 8: Alex, Sam, Tony        Heat 8: [bye], Sam, Tony       <-- trailing bye
    ```

    ## Algorithm (5 phases)

    1. **Identify gaps** — find unraced heats containing the dropout racer; remove them (create byes); sort ascending so soonest gaps are filled first.
    2. **Fill each gap** — for each `(Heat H, Lane L)`, search later heats for the best candidate:
        - **Hard constraint**: candidate not already in Heat H.
        - **Proximity score**: prefer the closest later heat.
        - **Consecutive penalty (+5000)**: candidate would race back-to-back.
        - **Lane penalty (+200)**: candidate already used Lane L.
        - Selected candidate moves into the gap; their old slot becomes a new gap.
    3. **Cascade** — repeat phase 2 for each newly-created gap until no candidates remain (gap reaches the last heat). No depth limit.
    4. **Compression** — `squeeze_out_byes()` dissolves entirely-empty heats; renumber to keep numbering contiguous.
    5. **Validation** — verify no racer appears twice in any heat. Report fairness warnings (consecutive races, lane repeats) for the coordinator to review.

    ## Use cases

    - **UC-1 Mid-event dropout** (primary): coordinator triggers pull-forward; cascade fills the schedule; tail becomes a bye.
    - **UC-2 Dropout with partial results**: only unraced heats affected. Completed results immutable.
    - **UC-3 Multiple dropouts**: each pull-forward is a separate operation; second sees the first's modified state.
    - **UC-4 Near end of schedule**: not enough later heats to pull from; remaining gaps become trailing byes.
    - **UC-5 Final-heat dropout**: no later heats, no pull-forward; preview shows zero moves and a trailing bye.
    - **UC-6 Racer returns**: undo if no affected heat ran yet; otherwise use Add Latecomer.
    - **UC-7 Start-line refusal**: not practical to pull-forward in seconds — DNF the heat, then pull-forward future heats.
    - **UC-8 Pre-event dropout**: prefer `handle_racer_dropout()` (full reschedule with optimal weighting). Pull-forward is for mid-event.
    - **UC-9 Dropout with broadcast**: **Apply + Announce** sends a 30-second kiosk broadcast.

    ## Fairness

    Pull-forward intentionally disrupts the optimized schedule. Original weights (`avoid_consecutive=5000, avoid_same_lane=200, group_weighted_cars=100`) produced a balanced chart; pull-forward will violate some. Accepted because:

    - An empty lane is worse than a slightly imbalanced schedule.
    - The alternative (full reschedule) would invalidate already-recorded results.
    - The system warns the coordinator about specific violations.
    - Race counts stay the same for every racer — pull-forward is positional, not additive.

    ## Undo

    Every pull-forward stores a snapshot of the unraced chart before changes. The Undo button restores the exact original schedule. Available **until** any affected heat records results (`finishtime` or `finishplace`). Once a touched heat races, undo is no longer possible and the button disappears. Undo also restores the dropout racer's `passedinspection` flag.

    ## Files

    | File | Role |
    |---|---|
    | `website/inc/schedule-adjuster.inc` | `ScheduleAdjuster` class with `pull_forward()`, scoring, snapshot |
    | `website/ajax/action.schedule.pullforward.inc` | AJAX: dry-run preview and execute |
    | `website/ajax/action.schedule.pullforward.undo.inc` | AJAX: undo |
    | `website/pull-forward.php` | Dedicated operator page (primary entry) |
    | `website/js/pull-forward.js` | Page logic |
    | `website/css/pull-forward.css` | Portrait-tablet styling, sticky action bar |
    | `website/coordinator.php` | Deprecated modal HTML (one-release fallback) |
    | `website/js/coordinator-controls.js` | Deprecated modal helpers + `undoPullForward()` |
    | `website/js/coordinator-poll.js` | Entry + Undo button rendering |
    | `website/inc/events.inc` | `EVENT_PULL_FORWARD` (501), `EVENT_PULL_FORWARD_UNDO` (502) |
    | `testing/test-pull-forward.sh` | Integration test suite (9 scenarios) |
    | `testing/puppeteer/pull-forward-test.js` | Puppeteer UI test suite (11 scenarios) |

    ## API

    ### `schedule.pullforward` (POST)

    | Parameter | Required | Description |
    |---|---|---|
    | `roundid` | yes | Round to operate on |
    | `dropout_racerid` | yes | Racer being removed |
    | `dry-run` | no | If truthy, return preview without committing |
    | `send_broadcast` | no | If truthy, send staging announcement on execute |
    | `trace` | no | If truthy, include algorithm trace |

    Response: `proposal` with `dropout`, `moves[]`, `trailing_byes[]`, `warnings[]`, `heats_affected`. On execute, `undo_available: true`.

    ### `schedule.pullforward.undo` (POST)

    | Parameter | Required | Description |
    |---|---|---|
    | `roundid` | yes | Round to restore |

    Fails with `has_results` if any affected heat recorded results since the pull-forward.

    ## Test scenarios

    **Integration** (`testing/test-pull-forward.sh`): 9 scenarios — dry-run preview, execute, undo, broadcast, already-removed, undo-after-results, sequential dropouts, minimal racers, permission check.

    **UI** (`testing/puppeteer/pull-forward-test.js`): 11 scenarios — modal populates, empty proposal, clean proposal, cancel, accept, accept+announce, dry-run + open, undo button rendering, undo click, modal re-population.

    Run:

    ```bash
    ./testing/test-pull-forward.sh http://localhost:8080
    node testing/puppeteer/pull-forward-test.js http://localhost/derbynet
    ```
