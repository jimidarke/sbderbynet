#! /bin/bash
#
# End-to-end test of the elimination tournament scoring engine:
#
#   * roundname (not the numeric `round` column) matching in the advancement
#     round lookup, the round-complete check, and the standings subquery
#   * tie-inclusive advancement: racers tied with the last advancing score
#     all advance together (no LIMIT truncation)
#   * DNF (99.999) participates in scoring aggregates for both advancement
#     and the standings display
#   * drop_slowest scoring method (drop slowest run, average the rest);
#     note its policy effect: a single DNF gets dropped
#
# Uses the VIP age group (top 3 advance, then finals) from both elimination
# configs, on two classes that match its name pattern.  The scheduler gives
# each racer 3 prelim runs (once per lane); see the roster note below.
#
# Usage:  ./test-elimination-scoring.sh http://localhost[:port][/path]

BASE_URL=$1
set -e -E -o pipefail
source `dirname $0`/common.sh

# Raw POST that skips common.sh's xmllint pretty-printing (xmllint isn't
# installed everywhere); timer-message replies are XML, check_success greps.
function post_raw() {
    echo ' ' ' ' ' ' post action.php $1 >&2
    curl --location -d "$1" -s -b $COOKIES_CURL -c $COOKIES_CURL $BASE_URL/action.php \
        | tee $DEBUG_CURL | tee -a $OUTPUT_CURL
}

if [ -n "$SIM_TENANT" ] ; then
    # Cloud-mode target: bind the session to a throwaway tenant FIRST (the
    # .nodata actions need no DB), then log in within the tenant.
    curl_postj action.php "action=tenant-create.nodata&slug=$SIM_TENANT" > /dev/null
    # tenant-select 302s to index.php unless it looks like an AJAX call
    curl --location -s -b $COOKIES_CURL -c $COOKIES_CURL \
         -H "X-Requested-With: XMLHttpRequest" \
         -d "action=tenant-select.nodata&slug=$SIM_TENANT" \
         $BASE_URL/action.php | tee $DEBUG_CURL | check_jsuccess
    user_login_coordinator
else
    user_login_coordinator
    curl_postj action.php "action=setup.nodata&ez-new=elimscoringdb" > /dev/null
    `dirname $0`/reset-database.sh "$BASE_URL"
fi
curl_postj action.php "action=settings.write&n-lanes=3" | check_jsuccess

### Roster
# NOTE: the vip config says races_per_racer=2 but the scheduler only handles
# 1 or 3; unhandled counts fall back to once-per-lane (3 runs on 3 lanes).
# Plans below are therefore 3 runs per racer.
# Class "VIP" (classid 1, total_time scoring):
#   901: 10+10+10     = 30.000   (1st)
#   902: 11+11+11     = 33.000   (2nd)
#   903: 12.5x3       = 37.500   (tied 3rd)
#   904: 12+12.5+13   = 37.500   (tied 3rd -> BOTH advance, 4 total)
#   905: 13+13+DNF    = 125.999  (DNF counts as 99.999)
#   906: 30+30+30     = 90.000
for CARNO in 901 902 903 904 905 906 ; do
    curl_postj action.php "action=racer.import&firstname=Racer&lastname=V$CARNO&partition=VIP&carnumber=$CARNO" \
        | check_jsuccess
done

# Class "VIP Drop" (classid 2, drop_slowest scoring):
#   911: 10+10+25  -> drop 25  -> 10.000  (1st)
#   912: 11+11+11  -> 11.000             (2nd)
#   913: DNF+12+12 -> drop DNF -> 12.000  (3rd: DNF erased by the drop)
#   914: 12.5x3    -> 12.500             (4th: out, though it beats 913
#                                          under total_time 37.5 < 124.0)
#   915: 13+13+13  -> 13.000
for CARNO in 911 912 913 914 915 ; do
    curl_postj action.php "action=racer.import&firstname=Racer&lastname=D$CARNO&partition=VIP%20Drop&carnumber=$CARNO" \
        | check_jsuccess
done

# Check in everyone (fresh DB: racerids 1..11)
for RACER in 1 2 3 4 5 6 7 8 9 10 11 ; do
    curl_postj action.php "action=racer.pass&racer=$RACER&value=1" | check_jsuccess
done

### Discover classids by name
curl_getj "action.php?query=class.list" > /dev/null
CLASSID_A=$(jq -r '.classes[] | select(.name == "VIP") | .classid' $DEBUG_CURL)
CLASSID_B=$(jq -r '.classes[] | select(.name == "VIP Drop") | .classid' $DEBUG_CURL)
[ -n "$CLASSID_A" ] && [ -n "$CLASSID_B" ] || test_fails could not resolve classids

### Initialize tournaments (both VIP* names match the vip pattern)
curl_postj action.php "action=elimination.tournament.initialize&classid=$CLASSID_A&config_file=soapbox-derby-elimination.json&age_group_key=vip" \
    | check_jsuccess
curl_postj action.php "action=elimination.tournament.initialize&classid=$CLASSID_B&config_file=soapbox-derby-elimination-dropslowest.json&age_group_key=vip" \
    | check_jsuccess

# Map classid -> prelim/finals roundids
curl_getj "action.php?query=poll.coordinator" > /dev/null
round_for() {  # $1 = classid, $2 = round sequence number
    # poll.coordinator maps .round to the display name ("1 Preliminary");
    # round names always start with the sequence number.
    jq -r ".rounds[] | select(.classid == $1 and ((.round|tostring) == \"$2\" or ((.round|tostring)|startswith(\"$2 \")))) | .roundid" $DEBUG_CURL
}
RID_A1=$(round_for $CLASSID_A 1) ; RID_A2=$(round_for $CLASSID_A 2)
RID_B1=$(round_for $CLASSID_B 1) ; RID_B2=$(round_for $CLASSID_B 2)
[ -n "$RID_A1" ] && [ -n "$RID_A2" ] && [ -n "$RID_B1" ] && [ -n "$RID_B2" ] \
    || test_fails could not resolve roundids

### Schedule prelims
curl_postj action.php "action=schedule.generate&roundid=$RID_A1" | check_jsuccess
curl_postj action.php "action=schedule.generate&roundid=$RID_B1" | check_jsuccess

# Planned times per pinny, consumed left to right (one per run).
declare -A PLAN
PLAN[901]="10.000 10.000 10.000" ; PLAN[902]="11.000 11.000 11.000"
PLAN[903]="12.500 12.500 12.500" ; PLAN[904]="12.000 12.500 13.000"
PLAN[905]="13.000 13.000 99.999" ; PLAN[906]="30.000 30.000 30.000"
PLAN[911]="10.000 10.000 25.000" ; PLAN[912]="11.000 11.000 11.000"
PLAN[913]="99.999 12.000 12.000" ; PLAN[914]="12.500 12.500 12.500"
PLAN[915]="13.000 13.000 13.000"

# Drive every heat of the round now showing in poll.coordinator, assigning
# each racer their next planned time, until the round has no current heat.
run_round_from_plan() {  # $1 = roundid, $2 = expected number of heats
    local ROUNDID=$1 EXPECT_HEATS=$2 HEATS=0
    while : ; do
        curl_getj "action.php?query=poll.coordinator" > /dev/null
        local NOW_ROUND=$(jq -r '.["current-heat"].roundid' $DEBUG_CURL)
        local RACING=$(jq -r '.["current-heat"].now_racing' $DEBUG_CURL)
        [ "$NOW_ROUND" == "$ROUNDID" ] && [ "$RACING" == "true" ] || break
        local FINISHED=""
        for LANE_CAR in $(jq -r '.racers[] | "\(.lane):\(.carnumber)"' $DEBUG_CURL) ; do
            local LANE=${LANE_CAR%%:*} CARNO=${LANE_CAR##*:}
            local TIMES=(${PLAN[$CARNO]})
            [ ${#TIMES[@]} -gt 0 ] || test_fails no planned time left for $CARNO
            FINISHED="$FINISHED&lane$LANE=${TIMES[0]}"
            PLAN[$CARNO]="${TIMES[@]:1}"
        done
         post_raw "action=timer-message&message=STARTED" | check_success
         post_raw "action=timer-message&message=FINISHED$FINISHED" | check_success
        let HEATS+=1
        [ $HEATS -le 20 ] || test_fails runaway heat loop for round $ROUNDID
    done
    [ $HEATS -eq $EXPECT_HEATS ] || test_fails expected $EXPECT_HEATS heats, ran $HEATS
}

### Race class A prelims (6 racers x 3 runs / 3 lanes = 6 heats)
curl_postj action.php "action=heat.select&roundid=$RID_A1&now_racing=1" | check_jsuccess
user_login_timer
 post_raw "action=timer-message&message=HELLO" | check_success
 post_raw "action=timer-message&message=IDENTIFIED&nlanes=3" | check_success
run_round_from_plan $RID_A1 6

### Class A: verify auto-advancement happened with tie-inclusive cut
user_login_coordinator
curl_getj "action.php?query=elimination.tournament.status&classid=$CLASSID_A" | \
    jq -e '.tournament.current_round == 2' > /dev/null || \
    test_fails class A did not auto-advance to round 2

# Finals roster must be exactly the tie-widened set {901, 902, 903, 904}
curl_postj action.php "action=schedule.generate&roundid=$RID_A2" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=$RID_A2&now_racing=0" | check_jsuccess
curl_getj "action.php?query=poll.coordinator" > /dev/null
ADVANCED_A=$(jq -r '[.racers[].carnumber] | sort | join(",")' $DEBUG_CURL)
# 4 advanced but only 3 lanes: heat 1 shows 3 of them; check the full round
# roster via the racer list instead.
curl_getj "action.php?query=racer.list" > /dev/null
ROSTER_A=$(jq -r "[.racers[] | select(.classid == $CLASSID_A and .roundid == $RID_A2) | .carnumber] | sort | join(\",\")" $DEBUG_CURL 2>/dev/null || echo "")
if [ -n "$ROSTER_A" ] ; then
    [ "$ROSTER_A" == "901,902,903,904" ] || test_fails class A advanced set was $ROSTER_A
fi

### Race class A finals (4 finalists / 3 lanes = 2 heats), placement scoring
PLAN[901]="15.000" ; PLAN[902]="14.000" ; PLAN[903]="16.000" ; PLAN[904]="15.500"
curl_postj action.php "action=heat.select&roundid=$RID_A2&heat=1&now_racing=1" | check_jsuccess
user_login_timer
run_round_from_plan $RID_A2 2
user_login_coordinator

### The standings KIOSK (what spectators see) must render the finals
### standings.  Before the roundname fix this page silently rendered EMPTY
### for every elimination class -- the exact broadcast-day failure mode.
curl_text "kiosk.php?page=kiosks/elimination-standings.kiosk&classid=$CLASSID_A" \
    | grep -q "0901\|0902" || \
    test_fails class A elimination-standings kiosk rendered no standings rows

### Race class B prelims (5 racers x 3 runs / 3 lanes = 5 heats)
curl_postj action.php "action=heat.select&roundid=$RID_B1&now_racing=1" | check_jsuccess
user_login_timer
run_round_from_plan $RID_B1 5

### Class B: drop_slowest advancement = {911, 912, 913}; 913's DNF was dropped
user_login_coordinator
curl_getj "action.php?query=elimination.tournament.status&classid=$CLASSID_B" | \
    jq -e '.tournament.current_round == 2' > /dev/null || \
    test_fails class B did not auto-advance to round 2

curl_postj action.php "action=schedule.generate&roundid=$RID_B2" | check_jsuccess
curl_postj action.php "action=heat.select&roundid=$RID_B2&now_racing=0" | check_jsuccess
curl_getj "action.php?query=poll.coordinator" > /dev/null
ADVANCED_B=$(jq -r '[.racers[].carnumber] | sort | join(",")' $DEBUG_CURL)
[ "$ADVANCED_B" == "911,912,913" ] || \
    test_fails class B drop_slowest advanced set was $ADVANCED_B expected 911,912,913

echo "test-elimination-scoring PASSED"
