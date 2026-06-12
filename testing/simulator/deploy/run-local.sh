#!/bin/bash
# Run a simctl command against the LOCAL docker-cloud twin.
#
#   cd installer/docker-cloud && docker compose up -d   # first
#   testing/simulator/deploy/run-local.sh doctor
#   testing/simulator/deploy/run-local.sh run --seed 1 --tenant sim-01

set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
COMPOSE_DIR="$REPO/installer/docker-cloud"

IMAGE=$(docker inspect derbynet-race-server --format '{{.Config.Image}}')
NET=$(docker inspect derbynet-race-server --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')

docker run --rm --network "$NET" \
    --env-file "$COMPOSE_DIR/.env" \
    -e DERBYNET_API_BASE=http://derbynet-web \
    -e MQTT_BROKER=mqtt -e MQTT_PORT=1883 \
    -e SIM_CONFIGS_DIR=/configs \
    -e SIM_ARTIFACTS_DIR=/sim/artifacts \
    -v derbynet_data:/var/lib/derbynet \
    -v "$HERE":/sim \
    -v "$REPO/website/inc/elimination-configs":/configs:ro \
    --entrypoint python3 \
    "$IMAGE" /sim/simctl.py "$@"
