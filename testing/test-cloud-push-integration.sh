#!/bin/bash
# test-cloud-push-integration.sh — End-to-end integration test for the PHP
# event-driven cloud-push hooks, run against a REAL DerbyNet instance in Docker.
#
# Proves the two things unit tests can't:
#   PHASE 1 (trigger file ABSENT, i.e. a normal non-Pi box): the hooks are a
#           true no-op — schedule.generate / heat.select / result.write all
#           still succeed, and nothing is created. The hooks cannot break racing.
#   PHASE 2 (trigger file PRESENT, mode 0666, as tmpfiles.d sets on the Pi):
#           each distinct hook site actually FIRES — write_chart,
#           set_current_heat, write_heat_results each bump the trigger mtime.
#
# Builds the stock server image from installer/docker/Dockerfile against the
# CURRENT working tree (so it runs your modified website/), pinned to Alpine
# 3.20 (the upstream Dockerfile's php-fpm83 assumption; bare `alpine` has since
# moved to php 8.4). Skips cleanly if Docker is unavailable.
#
# Usage: ./test-cloud-push-integration.sh        (KEEP=1 to leave the container up)

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${IMAGE:-derbynet_cloudpush_test}"
CT="${CONTAINER:-derbynet_cloudpush_itest}"
PORT="${PORT:-8099}"
B="http://localhost:$PORT"
TRIG=/run/derbynet-cloud-sync.trigger
PASS=0; FAIL=0
ok()  { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

command -v docker >/dev/null || { echo "SKIP: docker not installed"; exit 0; }
docker info >/dev/null 2>&1 || { echo "SKIP: docker daemon not running (start it, then re-run)"; exit 0; }
command -v jq >/dev/null || { echo "SKIP: jq not installed"; exit 0; }

# ---- build image from the current tree --------------------------------------
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "building $IMAGE from installer/docker/Dockerfile (Alpine 3.20 pin)..."
    DF=$(mktemp)
    sed 's/^FROM alpine$/FROM alpine:3.20/' "$REPO/installer/docker/Dockerfile" > "$DF"
    docker build -t "$IMAGE" -f "$DF" "$REPO" >/tmp/cloudpush-build.log 2>&1 \
        || { echo "FATAL: image build failed; see /tmp/cloudpush-build.log"; tail -10 /tmp/cloudpush-build.log; exit 2; }
    rm -f "$DF"
fi

# ---- run container ----------------------------------------------------------
docker rm -f "$CT" >/dev/null 2>&1 || true
docker run -d --name "$CT" -p "$PORT:80" "$IMAGE" >/dev/null
cleanup() { [ "${KEEP:-0}" = "1" ] || docker rm -f "$CT" >/dev/null 2>&1; }
trap cleanup EXIT

for i in $(seq 1 30); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "$B/index.php" 2>/dev/null)" != "000" ] && break
    sleep 1
done
# The stock image's web-root data dir must be writable by the php-fpm user.
docker exec "$CT" sh -c "mkdir -p /var/www/html/Data && chmod -R 777 /var/www/html/Data"

# ---- helpers ----------------------------------------------------------------
J=$(mktemp); DB="itest$$"
post() { curl -s -b "$J" -c "$J" -d "$2" "$B/$1"; }
succ() { post action.php "$1" | jq -e '.outcome.summary=="success"' >/dev/null 2>&1; }

# ---- bootstrap a small checked-in roster across 3 rounds --------------------
echo "===== bootstrap (db=$DB) ====="
post action.php "action=role.login&name=RaceCoordinator&password=doyourbest" >/dev/null
post action.php "action=setup.nodata&ez-new=$DB" >/dev/null
post action.php "action=role.login&name=RaceCoordinator&password=doyourbest" >/dev/null
n=1
for part in Aces Bees Cees; do
    for k in 1 2 3; do
        post action.php "action=racer.import&firstname=R$n&lastname=L$n&partition=$part&carnumber=$((100 + n))" >/dev/null
        n=$((n + 1))
    done
done
for id in $(seq 1 9); do post action.php "action=racer.pass&racer=$id&value=1" >/dev/null; done
succ "action=settings.write&n-lanes=4" && echo "  $((n - 1)) racers imported + checked in, 4 lanes" \
    || { echo "  FATAL: bootstrap failed (could not configure event)"; rm -f "$J"; exit 2; }

# ---- PHASE 1: trigger absent → hooks must not break racing -------------------
echo "===== PHASE 1: trigger ABSENT — hooks must not break racing ====="
docker exec "$CT" sh -c "rm -f $TRIG"
succ "action=schedule.generate&roundid=1"        && ok "schedule.generate (write_chart) succeeds"        || bad "schedule.generate failed"
succ "action=heat.select&roundid=1&now_racing=1" && ok "heat.select (set_current_heat) succeeds"          || bad "heat.select failed"
succ "action=result.write&lane1=8.888"           && ok "result.write (write_heat_results) succeeds"       || bad "result.write failed"
docker exec "$CT" sh -c "test ! -e $TRIG"        && ok "trigger still absent (no-op path confirmed)"      || bad "trigger created unexpectedly"

# ---- PHASE 2: trigger present → each hook must fire --------------------------
echo "===== PHASE 2: trigger PRESENT — each hook must fire ====="
docker exec "$CT" sh -c "touch $TRIG && chmod 666 $TRIG"
fire() {  # $1=action params  $2=label  (uses an unraced round so write_chart is clean)
    docker exec "$CT" sh -c "touch -d @1000000000 $TRIG"
    succ "$1" || { bad "$2 action did not succeed"; return; }
    m=$(docker exec "$CT" stat -c %Y "$TRIG")
    [ "$m" != "1000000000" ] && ok "$2 fired the trigger (mtime $m)" || bad "$2 did NOT fire the trigger"
}
fire "action=schedule.generate&roundid=2"        "schedule.generate/write_chart"
fire "action=heat.select&roundid=2&now_racing=1" "heat.select/set_current_heat"
fire "action=result.write&lane1=7.777"           "result.write/write_heat_results"

rm -f "$J"
echo
echo "cloud-push PHP integration: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
