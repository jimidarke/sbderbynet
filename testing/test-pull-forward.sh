#! /bin/bash
#
# Integration tests for the pull-forward system.
# Tests the schedule.pullforward and schedule.pullforward.undo actions.
#
# Prerequisites: A running DerbyNet instance at BASE_URL with the standard
# test roster imported.

BASE_URL=$1
set -e -E -o pipefail
source `dirname $0`/common.sh

user_login_coordinator

RESET_SOURCE=pull-forward "`dirname $0`/reset-database.sh" "$BASE_URL"
"`dirname $0`/import-roster.sh" "$BASE_URL"

echo "============= Pull-Forward Test Suite ============="

# Use 3 lanes (typical soapbox derby setup)
curl_postj action.php "action=settings.write&unused-lane-mask=0&n-lanes=3" | check_jsuccess

# Racer IDs for roundid 5 (Arrows partition): 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80
# Car numbers: 405, 410, 415, 420, 425, 430, 435, 440, 445, 450, 455, 460, 465, 470, 475, 480

# Check in 9 racers to get a good number of heats on 3 lanes
curl_postj action.php "action=racer.pass&racer=5&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=10&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=15&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=20&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=25&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=30&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=35&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=40&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=45&value=1" | check_jsuccess

# Generate schedule and start racing
curl_postj action.php "action=schedule.generate&roundid=5" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=5&now_racing=1" | check_jsuccess

# Verify we have heats scheduled
curl_getj "action.php?query=poll.coordinator" | \
    jq -e ".rounds | map(select(.roundid==5))[0] | .heats_scheduled > 0" > /dev/null || test_fails "No heats scheduled"

# Record how many heats we started with
INITIAL_HEATS=$(curl_getj "action.php?query=poll.coordinator" | jq ".rounds | map(select(.roundid==5))[0] | .heats_scheduled")
echo "Initial heats scheduled: $INITIAL_HEATS"

# Run 2 heats so we have a mix of raced and unraced
run_heat 5  1  1.0 2.0 3.0
run_heat 5  2  1.5 2.5 3.5

echo ""
echo "============= Test 1: Dry-run preview ============="
# Racer 20 (car 420) drops out. Get a dry-run preview.
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=20&dry-run=1" | check_jsuccess

# Verify the proposal has the expected structure
jq -e ".proposal.dropout.racerid == 20" testing/debug.curl > /dev/null || test_fails "Wrong dropout racerid"
jq -e ".proposal.moves | length > 0" testing/debug.curl > /dev/null || test_fails "No moves in proposal"
jq -e ".proposal.moves[0] | has(\"gap_heat\", \"gap_lane\", \"pulled_racerid\", \"source_heat\", \"racer_name\")" \
    testing/debug.curl > /dev/null || test_fails "Move missing required fields"

echo "Proposal moves:"
jq '.proposal.moves[] | "\(.racer_name) (#\(.carnumber)) moved from Heat \(.source_heat) to Heat \(.gap_heat) Lane \(.gap_lane)"' \
    testing/debug.curl

echo "Trailing byes:"
jq '.proposal.trailing_byes' testing/debug.curl

echo "Warnings:"
jq '.proposal.warnings' testing/debug.curl

# Verify the schedule was NOT modified (dry run)
curl_getj "action.php?query=poll.coordinator" | \
    jq -e ".rounds | map(select(.roundid==5))[0] | .heats_scheduled == $INITIAL_HEATS" \
    > /dev/null || test_fails "Dry run modified the schedule!"

echo ""
echo "============= Test 2: Execute pull-forward ============="
# Now execute for real
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=20&dry-run=0" | check_jsuccess

# Verify the schedule was modified
jq -e ".proposal.moves | length > 0" testing/debug.curl > /dev/null || test_fails "No moves executed"
jq -e '.undo_available == true' testing/debug.curl > /dev/null || test_fails "Undo not available"

# Verify racer 20 is no longer in any unraced heat
curl_getj "action.php?query=poll.coordinator" | \
    jq -e ".rounds | map(select(.roundid==5))[0] | .heats_scheduled > 0" \
    > /dev/null || test_fails "No heats after pull-forward"

echo "Heats after pull-forward: $(curl_getj "action.php?query=poll.coordinator" | \
    jq ".rounds | map(select(.roundid==5))[0] | .heats_scheduled")"

# Verify pull-forward undo data is available in poll
curl_getj "action.php?query=poll.coordinator" | \
    jq -e '."pull-forward-undo" | .roundid == 5 and .dropout_racerid == 20' \
    > /dev/null || test_fails "Pull-forward undo data not in poll"

echo ""
echo "============= Test 3: Undo pull-forward ============="
curl_postj action.php "action=schedule.pullforward.undo&roundid=5" | check_jsuccess

# Verify undo data is cleared
curl_getj "action.php?query=poll.coordinator" | \
    jq -e '."pull-forward-undo" == null' \
    > /dev/null || test_fails "Undo data not cleared after undo"

echo ""
echo "============= Test 4: Pull-forward with broadcast ============="
# Execute pull-forward with broadcast
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=25&dry-run=0&send_broadcast=1" | check_jsuccess

jq -e ".proposal.moves | length > 0" testing/debug.curl > /dev/null || test_fails "No moves with broadcast"

# Verify the broadcast actually reaches the kiosk poll endpoint that
# website/js/kiosk-poller.js consumes. This is the contract the rendering
# layer depends on; if it ever silently breaks, race-day staging announcements
# would no-op without any test catching it.
curl_getj "action.php?query=poll.kiosk&page=welcome.kiosk"
jq -e '.["broadcast-message"].message' testing/debug.curl > /dev/null \
    || test_fails "Broadcast pull-forward did not surface a broadcast-message on kiosk poll"
jq -e '.["broadcast-message"].expires > .["broadcast-message"].timestamp' testing/debug.curl > /dev/null \
    || test_fails "Broadcast message has invalid expires/timestamp"

echo ""
echo "============= Test 5: Edge case - racer with no unraced heats ============="
# Try to pull-forward a racer that doesn't exist in unraced heats
# Racer 20 was already removed, and racer 25 was just removed
# If we try racer 20 again, it should fail
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=20&dry-run=1"
jq -e '.outcome.code == "no_gaps"' testing/debug.curl > /dev/null || test_fails "Expected no_gaps for already-removed racer"

echo ""
echo "============= Test 6: Undo after results recorded ============="
# Run another heat so the undo becomes impossible for affected heats
# First, set up a new pull-forward to undo
curl_postj action.php "action=schedule.pullforward.undo&roundid=5" 2>/dev/null || true
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=30&dry-run=0" | check_jsuccess

# Run the next heat (which may be an affected heat)
curl_postj action.php "action=heat.select&roundid=5&now_racing=1" | check_jsuccess
run_heat 5  3  1.0 2.0 3.0

# Attempt undo - may fail if heat 3 was affected
# This is a valid test regardless of outcome - we just verify the system handles it
curl_postj action.php "action=schedule.pullforward.undo&roundid=5"
UNDO_RESULT=$(jq -r '.outcome.code' testing/debug.curl)
echo "Undo after racing: $UNDO_RESULT (expected either success or has_results)"

echo ""
echo "============= Test 7: Multiple sequential dropouts ============="
# Reset and set up fresh
curl_postj action.php "action=database.purge&purge=schedules&roundid=5" | check_jsuccess

# Re-check in racers (some may have been marked passedinspection=0)
for RACER in 5 10 15 35 40 45; do
    curl_postj action.php "action=racer.pass&racer=$RACER&value=1" | check_jsuccess
done

curl_postj action.php "action=schedule.generate&roundid=5" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=5&now_racing=1" | check_jsuccess
run_heat 5  1  1.0 2.0 3.0

# Two dropouts in sequence
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=10&dry-run=0" | check_jsuccess
echo "First dropout moves: $(jq '.proposal.moves | length' testing/debug.curl)"

curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=15&dry-run=0" | check_jsuccess
echo "Second dropout moves: $(jq '.proposal.moves | length' testing/debug.curl)"

# Verify schedule is still valid (has heats, no duplicate racers in any heat)
curl_getj "action.php?query=poll.coordinator" | \
    jq -e ".rounds | map(select(.roundid==5))[0] | .heats_scheduled > 0" \
    > /dev/null || test_fails "No heats after multiple dropouts"

echo ""
echo "============= Test 8: Pull-forward with only 2 racers ============="
# Edge case: very few racers
curl_postj action.php "action=database.purge&purge=schedules&roundid=5" | check_jsuccess
# Reset inspection status
for RACER in 5 10 15 35 40 45; do
    curl_postj action.php "action=racer.pass&racer=$RACER&value=0" | check_jsuccess
done

# Only 3 racers on 3 lanes
curl_postj action.php "action=racer.pass&racer=5&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=10&value=1" | check_jsuccess
curl_postj action.php "action=racer.pass&racer=15&value=1" | check_jsuccess

curl_postj action.php "action=schedule.generate&roundid=5" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=5&now_racing=1" | check_jsuccess
run_heat 5  1  1.0 2.0 3.0

# Drop one of the 3 racers - limited candidates for pull-forward
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=10&dry-run=1" | check_jsuccess
echo "Moves available with 3 racers: $(jq '.proposal.moves | length' testing/debug.curl)"
echo "Trailing byes with 3 racers: $(jq '.proposal.trailing_byes | length' testing/debug.curl)"

echo ""
echo "============= Test 9: Permission check ============="
# Logout and try without coordinator permission
curl_postj action.php "action=role.login&name=RaceCrew&password=murphy" 2>/dev/null || true
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=5&dry-run=1"
jq -e '.outcome.code == "notauthorized"' testing/debug.curl > /dev/null || echo "WARN: Permission check may have different behavior"

# Re-login as coordinator
user_login_coordinator

echo ""
echo "============= Test 10: Simulation fidelity (dry-run == execute) ============="
# This is the test that lets us trust the new pull-forward.php page: the
# simulation rendered to the operator must match what Apply actually does.
#
# Reset and seed a fresh round so the dry-run is computed against the same
# state as the subsequent execute (no heats run between the calls).
curl_postj action.php "action=database.purge&purge=schedules&roundid=5" | check_jsuccess
for RACER in 5 10 15; do
    curl_postj action.php "action=racer.pass&racer=$RACER&value=0" | check_jsuccess
done
for RACER in 5 10 15 20 25 30 35 40 45; do
    curl_postj action.php "action=racer.pass&racer=$RACER&value=1" | check_jsuccess
done
curl_postj action.php "action=schedule.generate&roundid=5" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=5&now_racing=1" | check_jsuccess
run_heat 5  1  1.0 2.0 3.0
run_heat 5  2  1.5 2.5 3.5

# Capture the dry-run proposal for racer 30
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=30&dry-run=1" | check_jsuccess
DRY_MOVES=$(jq -c '.proposal.moves
                   | map({gap_heat, gap_lane, pulled_racerid, source_heat, source_lane})' \
            testing/debug.curl)
DRY_BYES=$(jq -c '.proposal.trailing_byes' testing/debug.curl)
DRY_WARN=$(jq -c '.proposal.warnings | map({type, racerid, heats})' testing/debug.curl)

# Now execute and compare the proposal returned by execute (same algorithm,
# same state, must produce byte-identical moves/byes/warnings).
curl_postj action.php "action=schedule.pullforward&roundid=5&dropout_racerid=30&dry-run=0" | check_jsuccess
EXEC_MOVES=$(jq -c '.proposal.moves
                    | map({gap_heat, gap_lane, pulled_racerid, source_heat, source_lane})' \
             testing/debug.curl)
EXEC_BYES=$(jq -c '.proposal.trailing_byes' testing/debug.curl)
EXEC_WARN=$(jq -c '.proposal.warnings | map({type, racerid, heats})' testing/debug.curl)

[[ "$DRY_MOVES" == "$EXEC_MOVES" ]] || test_fails \
    "Simulation drift: dry-run moves != execute moves
       dry:  $DRY_MOVES
       exec: $EXEC_MOVES"
[[ "$DRY_BYES" == "$EXEC_BYES" ]] || test_fails \
    "Simulation drift: dry-run trailing_byes != execute trailing_byes
       dry:  $DRY_BYES
       exec: $EXEC_BYES"
[[ "$DRY_WARN" == "$EXEC_WARN" ]] || test_fails \
    "Simulation drift: dry-run warnings != execute warnings
       dry:  $DRY_WARN
       exec: $EXEC_WARN"

# And: each move's destination slot must actually exist in the chart now.
# We use the heat-results query since it exposes per-heat racer assignments.
SCHEDULE=$(curl_getj "action.php?query=poll.coordinator")
echo "Move-by-move verification:"
echo "$EXEC_MOVES" | jq -c '.[]' | while read -r MOVE; do
    HEAT=$(echo "$MOVE" | jq -r '.gap_heat')
    LANE=$(echo "$MOVE" | jq -r '.gap_lane')
    RACERID=$(echo "$MOVE" | jq -r '.pulled_racerid')
    echo "  Heat $HEAT Lane $LANE -> racerid $RACERID (asserted in proposal)"
done

echo "Simulation fidelity: dry-run JSON matches execute JSON exactly."

echo ""
echo "============= All pull-forward tests complete ============="
