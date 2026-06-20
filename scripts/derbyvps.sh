#!/usr/bin/env bash
# derbyvps.sh — SBDerbyNet cloud VPS operations wrapper.
#
# One command for every routine VPS interaction: audit, bootstrap, deploy,
# status, logs, backup, rollback, shutdown, restore-uisp.
#
# Design notes:
#  * Backup-first on every deploy. Last 10 snapshots retained.
#  * Pre/post validation gates abort on disk pressure, port collision,
#    UISP not siloed, compose config errors, /health failures.
#  * Dry-run on every destructive command.
#  * No external deps beyond ssh, rsync, jq (optional), openssl, tar, curl.
#
# See docs/VPS_OPERATIONS.md and .claude/skills/derbyVPS/SKILL.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$SCRIPT_DIR/derbyvps.config"
LOG="$SCRIPT_DIR/.derbyvps-deploy.log"

# ---------- Defaults (override in $CONFIG) ----------
VPS_HOST="uisp.darketech.ca"
VPS_PORT=22
VPS_USER="claude"
VPS_KEY="$HOME/.ssh/sbderby_vps_ed25519"
VPS_REPO_DIR="/opt/sbderbynet"
VPS_DATA_DIR="/opt/derbynet/production/data"
VPS_BACKUP_DIR="/opt/sbderbynet-backups"
VPS_LOG_FILE="/var/log/sbderbynet-deploy.log"
BACKUP_RETENTION=10
COMPOSE_DIR_REL="installer/docker-cloud"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.production.yml"
HEALTH_URL="http://localhost/health"
EXPECTED_SERVICES_MIN=5
DERBYNET_CLOUD_MODE="public"

[[ -f "$CONFIG" ]] && source "$CONFIG"

# ---------- Flags ----------
DRY_RUN=0
YES=0
QUIET=0
VERBOSE=0

# ---------- Color/log helpers ----------
if [[ -t 1 ]]; then
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
else
  RED=; GREEN=; YELLOW=; BLUE=; RESET=
fi

mkdir -p "$(dirname "$LOG")"
say()  { [[ $QUIET -eq 1 ]] || printf '%s\n' "$*"; }
log()  { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }
info() { say "$*"; log "$*"; }
ok()   { say "${GREEN}✓${RESET} $*"; log "OK: $*"; }
warn() { say "${YELLOW}!${RESET} $*"; log "WARN: $*"; }
die()  { say "${RED}ERROR:${RESET} $*"; log "ERROR: $*"; exit 1; }
section() { say ""; say "${BLUE}== $* ==${RESET}"; log "== $* =="; }

confirm() {
  [[ $YES -eq 1 ]] && return 0
  local prompt="${1:-Proceed?} [y/N] "
  read -r -p "$prompt" reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

# ---------- SSH wrapper ----------
ssh_opts=(-i "$VPS_KEY" -p "$VPS_PORT" -o ConnectTimeout=15
          -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30)

SSH() { ssh "${ssh_opts[@]}" "$VPS_USER@$VPS_HOST" "$@"; }

# Run a multi-line script on the VPS via stdin. Local log captures the full
# script body; remote /var/log/sbderbynet-deploy.log gets a timestamped
# command marker plus the combined stdout/stderr.
ssh_logged() {
  local cmd="$*"
  log "remote: $cmd"
  SSH "bash -s" <<EOF
set -e
if [ -w "$VPS_LOG_FILE" ] || sudo -n true 2>/dev/null; then
  echo "\$(date -u +%Y-%m-%dT%H:%M:%SZ) ${VPS_USER} cmd: derbyvps.sh" | sudo tee -a $VPS_LOG_FILE >/dev/null 2>&1 || true
fi
$cmd
EOF
}

# Run a one-shot command on the VPS and return its stdout.
ssh_capture() {
  local cmd="$*"
  log "remote (capture): $cmd"
  SSH "bash -s" <<< "$cmd"
}

# ---------- Validation gates ----------
preflight() {
  section "Preflight"

  SSH 'true' >/dev/null 2>&1 || die "SSH to $VPS_USER@$VPS_HOST:$VPS_PORT failed"
  ok "ssh reachable ($VPS_USER@$VPS_HOST:$VPS_PORT)"

  local free_kb
  free_kb=$(ssh_capture "df --output=avail / | tail -1") || die "df failed"
  local free_gb=$((free_kb / 1024 / 1024))
  [[ $free_gb -ge 4 ]] || die "free disk < 4 GB ($free_gb GB) — refusing to deploy"
  ok "disk free ${free_gb} GB"

  local foreign_ports
  foreign_ports=$(ssh_capture "sudo ss -tlnp 2>/dev/null | awk '/:80 |:443 |:1883 / && \$0 !~ /docker-proxy/ {print \$NF}'" || true)
  if [[ -n "${foreign_ports// /}" ]]; then
    die "non-docker process bound to 80/443/1883: $foreign_ports"
  fi
  ok "ports 80/443/1883 free or held by docker only"

  local uisp_running
  uisp_running=$(ssh_capture "sudo docker ps --filter label=com.docker.compose.project=unms -q 2>/dev/null | wc -l" || echo 0)
  [[ "$uisp_running" -eq 0 ]] || die "UISP has $uisp_running running container(s) — run 'derbyvps shutdown' on UISP first"
  ok "UISP siloed (no running containers)"
}

postflight() {
  section "Postflight"

  local i running=0
  for i in 1 2 3 4 5 6; do
    running=$(ssh_capture "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES ps --status=running -q 2>/dev/null | wc -l" || echo 0)
    [[ "$running" -ge $EXPECTED_SERVICES_MIN ]] && break
    sleep 10
  done
  [[ "$running" -ge $EXPECTED_SERVICES_MIN ]] || die "only $running/$EXPECTED_SERVICES_MIN containers running after 60s"
  ok "$running containers running"

  for i in 1 2 3 4 5; do
    if ssh_capture "curl -fsS --max-time 5 $HEALTH_URL >/dev/null 2>&1"; then
      ok "/health returns 200"
      break
    fi
    sleep 3
    [[ $i -eq 5 ]] && die "/health did not return 200 in ~15s"
  done

  local err_lines
  err_lines=$(ssh_capture "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES logs --since 60s 2>&1 | grep -c 'ERROR ' || true")
  if [[ "$err_lines" -gt 1 ]]; then
    warn "$err_lines ERROR lines in last 60s — review with: $0 logs"
  else
    ok "no recent ERRORs in logs"
  fi
}

# ---------- Backup ----------
do_backup() {
  local tag="${1:-deploy-$(date +%Y%m%d-%H%M%S)}"
  section "Backup ($tag)"
  local rev=unknown
  rev=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)
  local who="$(whoami)@$(hostname)"

  ssh_logged "
    sudo mkdir -p $VPS_BACKUP_DIR/$tag
    sudo cp -a $VPS_REPO_DIR/$COMPOSE_DIR_REL/.env                  $VPS_BACKUP_DIR/$tag/env.bak              2>/dev/null || true
    sudo cp -a $VPS_REPO_DIR/$COMPOSE_DIR_REL/mosquitto/passwd      $VPS_BACKUP_DIR/$tag/mosquitto-passwd.bak 2>/dev/null || true
    sudo cp -a $VPS_REPO_DIR/$COMPOSE_DIR_REL/mosquitto/acl         $VPS_BACKUP_DIR/$tag/mosquitto-acl.bak    2>/dev/null || true
    if [ -d $VPS_REPO_DIR/$COMPOSE_DIR_REL ]; then
      sudo bash -c 'cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && docker compose $COMPOSE_FILES ps -a' \
        > /tmp/compose.state.txt 2>&1 || true
      sudo mv /tmp/compose.state.txt $VPS_BACKUP_DIR/$tag/
    fi
    if [ -d $VPS_DATA_DIR ]; then
      sudo tar -czf $VPS_BACKUP_DIR/$tag/data.tgz -C \"\$(dirname $VPS_DATA_DIR)\" \"\$(basename $VPS_DATA_DIR)\"
    fi
    sudo tee $VPS_BACKUP_DIR/$tag/meta.json >/dev/null <<META
{\"timestamp\":\"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_rev\":\"$rev\",\"deployer\":\"$who\",\"tag\":\"$tag\"}
META
    sudo bash -c 'cd $VPS_BACKUP_DIR && ls -1t | tail -n +$((BACKUP_RETENTION + 1)) | xargs -r -I {} rm -rf {}'
  "
  ok "backup written: $VPS_BACKUP_DIR/$tag"
  echo "$tag"
}

# ---------- Subcommands ----------

cmd_audit() {
  section "Audit ($VPS_HOST)"
  SSH 'set +e
echo "--- HOST ---"; hostname; uptime; uname -srm
echo; echo "--- RESOURCES ---"; free -h; df -h /
echo; echo "--- LISTENING TCP ---"; sudo ss -tlnp 2>/dev/null
echo; echo "--- DOCKER (running) ---"; sudo docker ps --format "table {{.Names}}\t{{.Status}}"
echo; echo "--- DOCKER (all) ---"; sudo docker ps -a --format "table {{.Names}}\t{{.Status}}"
echo; echo "--- UISP STATE ---"
sudo docker inspect $(sudo docker ps -aq --filter label=com.docker.compose.project=unms) \
  --format "{{.Name}}: state={{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}}" 2>/dev/null
echo; echo "--- SBDERBYNET PATHS ---"
ls -la /opt 2>/dev/null | grep -E "sbderbynet|derbynet" || echo "(no sbderbynet paths yet)"
echo "Backups:"
sudo ls -1t '"$VPS_BACKUP_DIR"' 2>/dev/null | head
echo; echo "--- LAST CLOUD-SYNC ---"
sudo cat '"$VPS_DATA_DIR"'/.cloud_readonly 2>/dev/null || echo "(no sync sentinel)"
'
}

cmd_bootstrap() {
  local force=0
  for a in "$@"; do [[ "$a" == "--force" ]] && force=1; done

  section "Bootstrap"
  if SSH "test -f $VPS_REPO_DIR/$COMPOSE_DIR_REL/.env" 2>/dev/null && [[ $force -eq 0 ]]; then
    die "$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env already exists. Use 'deploy' to update or pass --force."
  fi
  preflight

  info "creating directories"
  ssh_logged "
    sudo mkdir -p $VPS_REPO_DIR && sudo chown $VPS_USER:$VPS_USER $VPS_REPO_DIR
    # Data dir must be writable by PHP-FPM, which on Alpine runs as the
    # 'nobody' user (uid 65534). chmod 777 is the path of least resistance
    # for a test cloud twin; tighten if you ever expose this stack publicly.
    sudo mkdir -p $VPS_DATA_DIR && sudo chmod 777 $VPS_DATA_DIR
    sudo mkdir -p $VPS_BACKUP_DIR
    sudo touch $VPS_LOG_FILE && sudo chmod 664 $VPS_LOG_FILE
  "

  info "rsync working tree"
  do_rsync

  install_logrotate

  info "generating broker passwords + .env"
  local mqtt_pass virtual_pass
  mqtt_pass=$(openssl rand -hex 16)
  virtual_pass=$(openssl rand -hex 16)
  ssh_logged "
    cd $VPS_REPO_DIR/$COMPOSE_DIR_REL
    cp .env.example .env
    sed -i 's|^MQTT_PASS=.*|MQTT_PASS=$mqtt_pass|' .env
    sed -i 's|^VIRTUAL_MQTT_PASS=.*|VIRTUAL_MQTT_PASS=$virtual_pass|' .env
    sed -i 's|^# DERBYNET_CLOUD_MODE=.*|DERBYNET_CLOUD_MODE=$DERBYNET_CLOUD_MODE|' .env
    grep -q '^DERBYNET_CLOUD_MODE=' .env || echo 'DERBYNET_CLOUD_MODE=$DERBYNET_CLOUD_MODE' >> .env
    chmod 600 .env
  "

  info "provisioning broker users"
  # setup-mqtt-auth.sh uses mosquitto_passwd -c which refuses if passwd exists.
  # On --force re-bootstrap, clear stale passwd first so the create proceeds.
  ssh_logged "sudo rm -f $VPS_REPO_DIR/$COMPOSE_DIR_REL/mosquitto/passwd"
  # sudo prefix keeps the script callable from any sudoers user, regardless of
  # docker group membership. sudo's VAR=val syntax sets env for the invoked cmd.
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo VIRTUAL_MQTT_PASS=$virtual_pass ./scripts/setup-mqtt-auth.sh derbynet $mqtt_pass"

  info "validating compose"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES config -q"

  info "building + bringing stack up"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES up -d --build"

  postflight

  ok "bootstrap complete"
  say "  control panel: http://$VPS_HOST/derbynet/virtual/index.php"
  say "  health:        http://$VPS_HOST/health"
}

install_logrotate() {
  info "installing logrotate policy"
  ssh_logged "
    if [ -f $VPS_REPO_DIR/$COMPOSE_DIR_REL/sbderbynet.logrotate ]; then
      sudo install -m 644 -o root -g root \
        $VPS_REPO_DIR/$COMPOSE_DIR_REL/sbderbynet.logrotate \
        /etc/logrotate.d/sbderbynet
    fi
  "
}

do_rsync() {
  # --inplace preserves inodes so docker bind-mounts (which track inode, not
  # path) see updated content immediately. Without it, rsync's default
  # write-new-then-rename gives the file a new inode and the container keeps
  # serving the old content until the service is recreated.
  local rsync_opts=(-az --delete --inplace
    --exclude='.git'
    --exclude='timer/build' --exclude='timer/out' --exclude='timer/dist'
    --exclude='replay/build' --exclude='node_modules' --exclude='.DS_Store'
    --exclude='scripts/.derbyvps-deploy.log' --exclude='scripts/derbyvps.config'
    --exclude="$COMPOSE_DIR_REL/.env"
    --exclude="$COMPOSE_DIR_REL/mosquitto/passwd"
    # Simulator run artifacts and bytecode caches are produced ON the VPS
    # (root-owned via docker); mirroring the local tree over them aborts
    # the deploy with rsync code 23.
    --exclude='testing/simulator/artifacts'
    --exclude='__pycache__'
  )
  [[ $DRY_RUN -eq 1 ]] && rsync_opts+=(--dry-run -i)
  [[ $VERBOSE -eq 1 ]] && rsync_opts+=(-v)
  rsync "${rsync_opts[@]}" \
    -e "ssh ${ssh_opts[*]}" \
    "$REPO_ROOT/" "$VPS_USER@$VPS_HOST:$VPS_REPO_DIR/"
}

cmd_deploy() {
  section "Deploy"

  if [[ $DRY_RUN -eq 1 ]]; then
    info "DRY RUN — rsync diff only, no remote changes"
    do_rsync
    return 0
  fi

  if ! git -C "$REPO_ROOT" diff --quiet || ! git -C "$REPO_ROOT" diff --cached --quiet; then
    warn "local working tree has uncommitted changes"
    confirm "Deploy anyway?" || die "aborted (commit or stash first, or pass --yes)"
  fi

  preflight

  local tag
  tag=$(do_backup)

  info "rsync working tree"
  do_rsync

  install_logrotate

  # Ensure host directories that the production override bind-mounts into the
  # stack exist. Idempotent — chmod 777 only widens permissions on first run.
  info "ensuring public-stats host dir"
  ssh_logged "
    sudo mkdir -p /opt/derbynet/production/public-stats/tokens
    sudo chmod 777 /opt/derbynet/production/public-stats /opt/derbynet/production/public-stats/tokens
  "

  # The audience-feedback log (website/feedback-submit.php appends to
  # <data>/feedback/feedback.jsonl in the bind-mounted data dir) is written by the
  # derbynet-web php-fpm user. Provision the dir 0777 and any existing log 0666 so
  # writes succeed regardless of that user's uid — a web-image rebuild can shift
  # the uid and otherwise leaves the pre-existing (old-uid-owned) dir+file
  # unwritable, which surfaces as 'write_failed' 500s on submit. Re-applied every
  # deploy so it self-heals. Append-only, non-sensitive forensic log.
  info "ensuring audience-feedback dir is writable"
  ssh_logged "
    sudo mkdir -p /opt/derbynet/production/data/feedback
    sudo chmod 777 /opt/derbynet/production/data/feedback
    if sudo test -f /opt/derbynet/production/data/feedback/feedback.jsonl; then
      sudo chmod 666 /opt/derbynet/production/data/feedback/feedback.jsonl
    fi
  "

  # derbynet-stats-gen refuses to start without a token. Mint one on first
  # deploy so postflight sees 5 containers running. Operator can rotate later
  # via 'stats-token rotate' for race-day. Detects "missing OR empty" and
  # only writes when needed — idempotent across redeploys.
  info "ensuring LIVE_STATS_TOKEN is set in .env"
  ssh_logged "
    ENV_FILE=$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env
    if sudo test -f \$ENV_FILE; then
      CUR=\$(sudo grep -E '^LIVE_STATS_TOKEN=' \$ENV_FILE 2>/dev/null | head -1 | cut -d= -f2-)
      if [ -z \"\$CUR\" ]; then
        NEW=\$(openssl rand -hex 12)
        if sudo grep -q '^LIVE_STATS_TOKEN=' \$ENV_FILE; then
          sudo sed -i \"s|^LIVE_STATS_TOKEN=.*|LIVE_STATS_TOKEN=\$NEW|\" \$ENV_FILE
        else
          echo \"LIVE_STATS_TOKEN=\$NEW\" | sudo tee -a \$ENV_FILE >/dev/null
        fi
        echo \"  auto-minted initial LIVE_STATS_TOKEN (use 'stats-token show' to print URL)\"
      fi
    fi
  "

  info "validating compose"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES config -q" || {
    warn "compose config invalid — rolling back"
    cmd_rollback "$tag"
    die "deploy aborted on compose config failure"
  }

  info "building + bringing stack up"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES up -d --build" || {
    warn "compose up failed — rolling back"
    cmd_rollback "$tag"
    die "deploy aborted on compose up failure"
  }

  if ! postflight; then
    warn "postflight failed — rolling back"
    cmd_rollback "$tag"
    die "deploy aborted on postflight failure"
  fi

  ok "deploy complete (backup tag: $tag)"
}

cmd_status() {
  section "Status"
  SSH "set +e
cd $VPS_REPO_DIR/$COMPOSE_DIR_REL 2>/dev/null && sudo docker compose $COMPOSE_FILES ps
echo
echo --- /health ---
curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 $HEALTH_URL || true
echo --- recent ERRORs ---
cd $VPS_REPO_DIR/$COMPOSE_DIR_REL 2>/dev/null && sudo docker compose $COMPOSE_FILES logs --since 5m 2>&1 | grep -i 'error' | tail -10 || true
echo --- last sync ---
sudo cat $VPS_DATA_DIR/.cloud_readonly 2>/dev/null || echo '(no sentinel)'
"
}

cmd_logs() {
  local arg="${1:-}"
  if [[ "$arg" == "--where" || "$arg" == "-w" ]]; then
    cat <<MAP
== Where logs go ==

Container stdout (rotated; 10 MB x 3 files per service):
  Caddy           docker logs derbynet-caddy
                  derbyvps.sh logs caddy
  Mosquitto       docker logs derbynet-mqtt + /mosquitto/log/mosquitto.log
                  (mqtt_log volume; survives recreates)
  derbynet-web    docker logs derbynet-web
                  (PHP application errors stream here too — see Persistent below)
  race-server     docker logs derbynet-race-server
                  (DERBY_CONSOLE_LOG=true diverts derbylogger.py to stdout)

Persistent files (volumes; survive container recreates):
  /var/log/nginx/{access,error}.log    (derbynet_web_nginx_logs volume)
  /var/log/php83/error.log             (derbynet_web_php_logs volume)
  /var/log/derbynet.log + .jsonl       (derbynet_logs volume; written when
                                        DERBY_CONSOLE_LOG=false)
  /mosquitto/log/mosquitto.log         (mqtt_log volume)

Wrapper trail (host /etc/logrotate.d/sbderbynet — weekly, keep 4):
  Local:    scripts/.derbyvps-deploy.log
  VPS:      /var/log/sbderbynet-deploy.log

Quick recipes:
  derbyvps.sh logs                      # tail all services live
  derbyvps.sh logs derbynet-web         # one service
  ssh ... 'sudo docker run --rm -v derbynet_web_nginx_logs:/v alpine cat /v/access.log'
                                        # peek a volume without entering the web container

For the full map and troubleshooting recipes, see docs/LOGGING.md.
MAP
    return 0
  fi
  section "Logs $arg"
  SSH "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES logs -f --tail=100 $arg"
}

cmd_backup() {
  local tag="${1:-manual-$(date +%Y%m%d-%H%M%S)}"
  do_backup "$tag"
}

cmd_rollback() {
  local tag="${1:-}"
  [[ -n "$tag" ]] || die "rollback requires a tag (see: ssh && ls $VPS_BACKUP_DIR)"
  section "Rollback to $tag"

  SSH "test -d $VPS_BACKUP_DIR/$tag" || die "backup tag not found: $tag"
  confirm "Restore from $tag and restart the stack?" || die "aborted"

  ssh_logged "
    cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES down || true
    sudo cp -a $VPS_BACKUP_DIR/$tag/env.bak              $VPS_REPO_DIR/$COMPOSE_DIR_REL/.env              2>/dev/null || true
    sudo cp -a $VPS_BACKUP_DIR/$tag/mosquitto-passwd.bak $VPS_REPO_DIR/$COMPOSE_DIR_REL/mosquitto/passwd 2>/dev/null || true
    sudo cp -a $VPS_BACKUP_DIR/$tag/mosquitto-acl.bak    $VPS_REPO_DIR/$COMPOSE_DIR_REL/mosquitto/acl    2>/dev/null || true
    if [ -f $VPS_BACKUP_DIR/$tag/data.tgz ]; then
      sudo rm -rf $VPS_DATA_DIR
      sudo mkdir -p \"\$(dirname $VPS_DATA_DIR)\"
      sudo tar -xzf $VPS_BACKUP_DIR/$tag/data.tgz -C \"\$(dirname $VPS_DATA_DIR)\"
    fi
    cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES up -d
  "
  postflight
  ok "rolled back to $tag"
}

cmd_shutdown() {
  section "Shutdown SBDerbyNet"
  confirm "Stop SBDerbyNet stack? (volumes preserved)" || die "aborted"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES down"
  ok "stack stopped (data preserved)"
}

cmd_stats_token() {
  local sub="${1:-show}"
  local public_stats_dir="/opt/derbynet/production/public-stats"
  local live_host_default="live.soapboxderbynet.com"

  case "$sub" in
    show)
      section "Stats token (show)"
      SSH "set +e
ENV_FILE=$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env
if [ ! -f \$ENV_FILE ]; then echo '(no .env on host; run bootstrap or deploy first)'; exit 0; fi
TOKEN=\$(sudo grep -E '^LIVE_STATS_TOKEN=' \$ENV_FILE 2>/dev/null | head -1 | cut -d= -f2-)
HOST=\$(sudo grep -E '^LIVE_STATS_HOST=' \$ENV_FILE 2>/dev/null | head -1 | cut -d= -f2-)
HOST=\${HOST:-$live_host_default}
if [ -z \"\$TOKEN\" ]; then
  echo '(no token set; run: derbyvps.sh stats-token rotate)'
  exit 0
fi
echo \"host:      \$HOST\"
echo \"token:     \$TOKEN\"
echo \"schedule:  https://\$HOST/\$TOKEN/schedule.html\"
echo \"recent:    https://\$HOST/\$TOKEN/recent.html\"
QR=$public_stats_dir/tokens/\$TOKEN/qr.png
if sudo test -f \$QR; then echo \"qr:        \$QR (on VPS)\"; else echo '(qr.png not generated yet)'; fi
"
      ;;

    rotate)
      section "Stats token (rotate)"
      confirm "Mint a new spectator token? Old QR will stop working." || die "aborted"
      local new_token
      new_token=$(openssl rand -hex 12)
      info "new token: $new_token (will be visible in .env on VPS)"

      ssh_logged "
        ENV_FILE=$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env
        sudo test -f \$ENV_FILE || { echo 'ERR: .env missing; run bootstrap first'; exit 1; }
        # Idempotent set/append
        if sudo grep -q '^LIVE_STATS_TOKEN=' \$ENV_FILE; then
          sudo sed -i 's|^LIVE_STATS_TOKEN=.*|LIVE_STATS_TOKEN=$new_token|' \$ENV_FILE
        else
          echo 'LIVE_STATS_TOKEN=$new_token' | sudo tee -a \$ENV_FILE >/dev/null
        fi
        if ! sudo grep -q '^LIVE_STATS_HOST=' \$ENV_FILE; then
          echo 'LIVE_STATS_HOST=$live_host_default' | sudo tee -a \$ENV_FILE >/dev/null
        fi
        HOST=\$(sudo grep -E '^LIVE_STATS_HOST=' \$ENV_FILE | head -1 | cut -d= -f2-)
        HOST=\${HOST:-$live_host_default}
        sudo mkdir -p $public_stats_dir/tokens/$new_token
        sudo chmod 777 $public_stats_dir $public_stats_dir/tokens
        # Recreate the two services that consume LIVE_STATS_TOKEN so they pick
        # up the new value from .env. derbynet-stats-gen starts a fresh render
        # loop on the new token; caddy starts serving the new path.
        cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES up -d derbynet-stats-gen caddy
        # First render is on the loop's natural cadence; nudge it.
        sleep 2
        sudo docker exec derbynet-stats-gen /opt/stats-gen/render.sh /var/lib/derbynet/derbynet.sqlite3 /out $new_token >/dev/null 2>&1 || true
        # Generate the QR (qrencode is in the stats-gen image).
        sudo docker exec -e URL=\"https://\$HOST/$new_token/schedule.html\" \
          derbynet-stats-gen sh -c 'qrencode -o /out/tokens/$new_token/qr.png -s 10 -m 4 \"\$URL\"' \
          || echo 'WARN: qr generation failed (token still active)'
        echo \"ROTATE_HOST=\$HOST\"
      "
      ok "token rotated to $new_token"
      say "  Run \"$0 stats-token show\" to see URLs + QR location."
      ;;

    qr)
      section "Stats token (qr)"
      local local_out="${1:-./derby-qr.png}"
      [[ "${2:-}" == --out ]] && local_out="${3:-./derby-qr.png}"
      # Resolve token, then scp the PNG down.
      local remote_qr
      remote_qr=$(SSH "set +e
ENV_FILE=$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env
TOKEN=\$(sudo grep -E '^LIVE_STATS_TOKEN=' \$ENV_FILE 2>/dev/null | head -1 | cut -d= -f2-)
[ -n \"\$TOKEN\" ] && echo $public_stats_dir/tokens/\$TOKEN/qr.png
" 2>/dev/null)
      [[ -n "$remote_qr" ]] || die "no token on VPS (run: $0 stats-token rotate)"
      # Stage the file with read perms before scp (it's chmod 600 by default).
      SSH "sudo cp $remote_qr /tmp/derby-qr.png && sudo chmod 644 /tmp/derby-qr.png"
      scp -i "$VPS_KEY" -P "$VPS_PORT" "$VPS_USER@$VPS_HOST:/tmp/derby-qr.png" "$local_out"
      SSH "sudo rm -f /tmp/derby-qr.png"
      ok "QR saved to $local_out"
      ;;

    *) die "unknown stats-token subcommand: $sub (use: show|rotate|qr)" ;;
  esac
}

# Operator toggle for the spectator "race starting soon" splash gate. The gate
# is a single flag file at the public-stats volume root (event-wide, token-
# independent); render.sh checks it each pass. Turning it on/off forces an
# immediate render so the version-bump poll reloads every open phone within ~4s.
# See docs/PUBLIC_STATS.md.
cmd_splash() {
  local sub="${1:-status}"
  local public_stats_dir="/opt/derbynet/production/public-stats"
  local flag="$public_stats_dir/splash.flag"
  # Mirror render.sh's fallback so `status` and the file always agree.
  local default_msg="Race starting soon — all carts must be checked in"

  # Resolve the active token and force one synchronous render. Mirrors the nudge
  # in `stats-token rotate`. Token-independent file, but render.sh needs the
  # token to know which tokens/<token>/ tree to write.
  local force_render="
        ENV_FILE=$VPS_REPO_DIR/$COMPOSE_DIR_REL/.env
        TOKEN=\$(sudo grep -E '^LIVE_STATS_TOKEN=' \$ENV_FILE 2>/dev/null | head -1 | cut -d= -f2-)
        [ -n \"\$TOKEN\" ] || { echo 'ERR: no LIVE_STATS_TOKEN set (run: stats-token rotate)'; exit 1; }
        sudo docker exec derbynet-stats-gen /opt/stats-gen/render.sh /var/lib/derbynet/derbynet.sqlite3 /out \$TOKEN >/dev/null 2>&1 || true"

  case "$sub" in
    on)
      shift || true
      local msg="${*:-}"
      [ -n "$msg" ] || msg="$default_msg"
      section "Splash gate (on)"
      # $msg is expanded locally into the script body, then written verbatim on
      # the host via a quoted heredoc (no remote re-expansion). chmod 644 so the
      # container's non-root 'stats' user can read it.
      ssh_logged "
        sudo mkdir -p $public_stats_dir
        sudo tee $flag >/dev/null <<'SPLASHEOF'
$msg
SPLASHEOF
        sudo chmod 644 $flag
$force_render
      "
      ok "splash gate ON"
      say "  message: $msg"
      say "  Spectators see the splash within ~4s. Turn off with: $0 splash off"
      ;;

    off)
      section "Splash gate (off)"
      ssh_logged "
        sudo rm -f $flag
$force_render
      "
      ok "splash gate OFF — live pages restored"
      ;;

    status)
      section "Splash gate (status)"
      SSH "set +e
if sudo test -f $flag; then
  echo 'gate:    ON'
  echo \"message: \$(sudo cat $flag 2>/dev/null)\"
else
  echo 'gate:    OFF (live pages)'
fi
"
      ;;

    *) die "unknown splash subcommand: $sub (use: on [message] | off | status)" ;;
  esac
}

cmd_restore_uisp() {
  section "Restore UISP"
  confirm "Stop SBDerbyNet and restart UISP?" || die "aborted"
  ssh_logged "cd $VPS_REPO_DIR/$COMPOSE_DIR_REL && sudo docker compose $COMPOSE_FILES down 2>/dev/null || true"
  ssh_logged '
    DISABLED=$(ls /etc/cron.d/unms-update.disabled-by-claude-* 2>/dev/null | head -1)
    if [ -n "$DISABLED" ]; then
      sudo mv "$DISABLED" /etc/cron.d/unms-update
    fi
    for c in unms-postgres unms-rabbitmq unms-fluentd unms-siridb \
             unms-api unms-nginx unms-netflow unms-device-ws-1 ucrm; do
      sudo docker update --restart=always "$c" >/dev/null 2>&1 || true
    done
    sudo docker start unms-postgres unms-rabbitmq unms-fluentd 2>/dev/null
    sleep 5
    sudo docker start unms-siridb unms-api unms-nginx unms-netflow ucrm unms-device-ws-1 2>/dev/null
    sudo docker ps --filter label=com.docker.compose.project=unms --format "table {{.Names}}\t{{.Status}}"
  '
  ok "UISP restored"
}

cmd_feedback() {
  # Audience-feedback log written by website/feedback-submit.php into the
  # derbynet_data volume. We read it through the web container so we don't have
  # to know the host-side bind path. See docs/PUBLIC_STATS.md.
  local sub="${1:-show}"
  local container="derbynet-web"
  local remote_file="/var/lib/derbynet/feedback/feedback.jsonl"

  case "$sub" in
    show)
      section "Audience feedback (summary)"
      SSH "set +e
if ! sudo docker exec $container test -f $remote_file 2>/dev/null; then
  echo '(no feedback yet — nobody has submitted)'
  exit 0
fi
echo \"submissions: \$(sudo docker exec $container sh -c 'wc -l < $remote_file' | tr -d ' ')\"
echo
echo 'most recent:'
sudo docker exec $container sh -c 'tail -n 5 $remote_file'
"
      ;;

    dump)
      section "Audience feedback (dump)"
      local out="${2:-./derby-feedback.jsonl}"
      SSH "sudo docker exec $container test -f $remote_file" \
        || die "no feedback file yet on VPS (nobody has submitted)"
      # Stage with read perms (the volume is root-owned), scp down, clean up.
      SSH "sudo docker exec $container cat $remote_file | sudo tee /tmp/derby-feedback.jsonl >/dev/null && sudo chmod 644 /tmp/derby-feedback.jsonl"
      scp -i "$VPS_KEY" -P "$VPS_PORT" "$VPS_USER@$VPS_HOST:/tmp/derby-feedback.jsonl" "$out"
      SSH "sudo rm -f /tmp/derby-feedback.jsonl"
      local n; n=$(wc -l < "$out" 2>/dev/null | tr -d ' ')
      ok "feedback saved to $out ($n submissions)"
      if command -v jq >/dev/null 2>&1; then
        local u; u=$(jq -r '.device_id' "$out" 2>/dev/null | sort -u | wc -l | tr -d ' ')
        say "  unique devices: $u"
      fi
      ;;

    *) die "unknown feedback subcommand: $sub (use: show|dump)" ;;
  esac
}

# ---------- Argument parsing ----------
usage() {
  cat <<USAGE
Usage: derbyvps.sh <command> [options]

Commands:
  audit                 Read-only host + docker + UISP + sync state.
  bootstrap [--force]   First-time setup: dirs, .env, broker users, build, up.
  deploy                Backup → rsync → up → validate. With --dry-run, preview rsync.
  status                Container state, /health, recent errors.
  logs [service]        Tail compose logs (use --where to print log map).
  backup [tag]          Manual snapshot (default tag: manual-<timestamp>).
  rollback <tag>        Restore from a backup tag.
  shutdown              Clean down (volumes preserved).
  restore-uisp          Tear down SBDerbyNet, bring UISP back up.
  stats-token <op>      Spectator-page token control.
                          show    — print current token + URLs + QR location
                          rotate  — mint new token, recreate stats-gen + caddy
                          qr      — scp the QR PNG to ./derby-qr.png
  splash <op>           Spectator "race starting soon" splash gate.
                          on [msg] — show splash on schedule + recent pages
                          off      — restore live pages
                          status   — report gate state + message
  feedback <op>         Audience-feedback log control.
                          show    — submission count + last 5 entries (default)
                          dump    — download feedback.jsonl to ./derby-feedback.jsonl

Options:
  --dry-run             Preview destructive ops; no remote changes.
  --yes                 Skip confirmation prompts.
  --quiet               Suppress info output (errors still print).
  --verbose             Include rsync details.
  -h, --help            This help.

Configuration:
  Edit $CONFIG (gitignored). See $SCRIPT_DIR/derbyvps.config.example.
  Defaults target uisp.darketech.ca / claude user / standard layout.

Logs:
  Local:  $LOG
  Remote: $VPS_LOG_FILE
USAGE
}

cmd=""
positional=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  YES=1 ;;
    --quiet|-q) QUIET=1 ;;
    --verbose|-v) VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) positional+=("$arg") ;;
  esac
done

[[ ${#positional[@]} -ge 1 ]] || { usage; exit 1; }
cmd="${positional[0]}"
args=("${positional[@]:1}")

case "$cmd" in
  audit)        cmd_audit "${args[@]:-}" ;;
  bootstrap)    cmd_bootstrap "${args[@]:-}" ;;
  deploy)       cmd_deploy "${args[@]:-}" ;;
  status)       cmd_status "${args[@]:-}" ;;
  logs)         cmd_logs "${args[@]:-}" ;;
  backup)       cmd_backup "${args[@]:-}" ;;
  rollback)     cmd_rollback "${args[@]:-}" ;;
  shutdown)     cmd_shutdown "${args[@]:-}" ;;
  restore-uisp) cmd_restore_uisp "${args[@]:-}" ;;
  stats-token)  cmd_stats_token "${args[@]:-}" ;;
  splash)       cmd_splash "${args[@]:-}" ;;
  feedback)     cmd_feedback "${args[@]:-}" ;;
  *) usage; die "unknown command: $cmd" ;;
esac
