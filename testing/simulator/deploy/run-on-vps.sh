#!/bin/bash
# Upload the simulator to the VPS and run a simctl command inside the docker
# network, with the derbynet_data volume mounted.
#
# Usage:
#   ./run-on-vps.sh doctor
#   ./run-on-vps.sh template build
#   ./run-on-vps.sh pool init --count 4
#   ./run-on-vps.sh run --seed 1 --scenario happy_path --tenant sim-01
#   ./run-on-vps.sh campaign run --plan /sim/campaigns/smoke.json
#
# Long campaigns: prefix with NOHUP=1 to run detached under nohup on the VPS.

set -euo pipefail

VPS_HOST="${VPS_HOST:-uisp.darketech.ca}"
VPS_USER="${VPS_USER:-claude}"
VPS_KEY="${VPS_KEY:-$HOME/.ssh/sbderby_vps_ed25519}"
REPO_DIR="${VPS_REPO_DIR:-/opt/sbderbynet}"
SIM_DIR="$REPO_DIR/testing/simulator"
COMPOSE_DIR="$REPO_DIR/installer/docker-cloud"

HERE="$(cd "$(dirname "$0")/.." && pwd)"
SSH=(ssh -i "$VPS_KEY" -o ConnectTimeout=15 -o ServerAliveInterval=30 "$VPS_USER@$VPS_HOST")

echo "== sync simulator to $VPS_HOST:$SIM_DIR =="
rsync -az --delete \
      --exclude 'artifacts/v*' --exclude 'artifacts/repro' --exclude 'artifacts/pf-*' --exclude 'artifacts/campaign-*' --exclude 'artifacts/*.sha256' \
      -e "ssh -i $VPS_KEY" \
      "$HERE/" "$VPS_USER@$VPS_HOST:/tmp/simulator-sync/"
"${SSH[@]}" "sudo mkdir -p '$SIM_DIR' && sudo rsync -a --delete --exclude artifacts /tmp/simulator-sync/ '$SIM_DIR/' && sudo mkdir -p '$SIM_DIR/artifacts'"

echo "== run: simctl $* =="
# Resolve the race-server image (has python3 + paho-mqtt + requests) and the
# compose network; pull MQTT/internal-token env from the compose .env.
"${SSH[@]}" "bash -s" <<EOF
set -euo pipefail
IMAGE=\$(sudo docker inspect derbynet-race-server --format '{{.Config.Image}}')
NET=\$(sudo docker inspect derbynet-race-server --format '{{range \$k, \$v := .NetworkSettings.Networks}}{{\$k}}{{end}}')
RUN=(sudo docker run --rm --network "\$NET" \
     --env-file "$COMPOSE_DIR/.env" \
     -e DERBYNET_API_BASE=http://derbynet-web \
     -e MQTT_BROKER=mqtt -e MQTT_PORT=1883 \
     -e SIM_CONFIGS_DIR=/configs \
     -e SIM_ARTIFACTS_DIR=/sim/artifacts \
     -v /opt/derbynet/production/data:/var/lib/derbynet \
     -v "$SIM_DIR":/sim \
     -v "$REPO_DIR/website/inc/elimination-configs":/configs:ro \
     --entrypoint python3 \
     "\$IMAGE" /sim/simctl.py $*)
if [ "\${NOHUP:-${NOHUP:-}}" = "1" ]; then
  LOG="$SIM_DIR/artifacts/run-\$(date +%Y%m%d-%H%M%S).log"
  sudo bash -c "nohup \${RUN[*]} > '\$LOG' 2>&1 &"
  echo "detached; log: \$LOG"
else
  "\${RUN[@]}"
fi
EOF
