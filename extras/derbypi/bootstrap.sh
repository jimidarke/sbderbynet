#!/bin/bash
# DerbyPi Bootstrap Script — EXPERT / DEVELOPMENT PATH
# ====================================================
#
# ┌──────────────────────────────────────────────────────────────────────┐
# │  RACE-DAY RECOVERY: use the pre-built SD image and the USB stick,    │
# │  NOT this script. See docs/SD_CARD_RECOVERY.md and                   │
# │  extras/imaging/INSTRUCTIONS.md.                                     │
# │                                                                      │
# │  This script is the expert/development path. It installs Ansible,    │
# │  clones the repo into /opt/derbynet-repo, and runs the playbook —    │
# │  multi-step and internet-required. It exists for cases where you've  │
# │  SSH'd into a stock Raspberry Pi OS image and want to bring it up    │
# │  without flashing a custom SD card.                                  │
# └──────────────────────────────────────────────────────────────────────┘
#
# Usage (after reviewing the script first):
#   wget https://raw.githubusercontent.com/jimidarke/sbderbynet/<pinned-sha>/extras/derbypi/bootstrap.sh
#   chmod +x bootstrap.sh
#   sudo ./bootstrap.sh
#
# DO NOT pipe `curl | sudo bash`. The script lives in a public repo and a
# repo/DNS compromise would run arbitrary code on your Pi. Always download,
# verify, then run.

set -e

# Configuration
GIT_REPO="https://github.com/jimidarke/sbderbynet.git"
GIT_BRANCH="master"
REPO_DIR="/opt/derbynet-repo"
ANSIBLE_PLAYBOOK="extras/derbypi/ansible/playbook.yml"
ANSIBLE_PULL_INTERVAL=30  # minutes
ANSIBLE_PULL_DELAY=5      # minutes random delay

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo_error "This script must be run as root (use sudo)"
    exit 1
fi

echo "============================================================"
echo "  DerbyPi Bootstrap Script"
echo "============================================================"
echo ""
echo "This script will:"
echo "  1. Install Ansible and Git"
echo "  2. Clone the SBDerbyNet repository"
echo "  3. Run the Ansible playbook"
echo "  4. Set up ansible-pull for automatic updates"
echo ""
echo "Repository: $GIT_REPO"
echo "Branch: $GIT_BRANCH"
echo ""

# Confirm before proceeding
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo_info "Step 1: Updating package lists..."
apt-get update

echo_info "Step 2: Installing Ansible and Git..."
apt-get install -y ansible git python3-pip

# Install ansible collections
echo_info "Step 3: Installing Ansible collections..."
ansible-galaxy collection install community.general ansible.posix

echo_info "Step 4: Cloning SBDerbyNet repository..."
if [[ -d "$REPO_DIR" ]]; then
    echo_warn "Repository directory exists, pulling latest..."
    cd "$REPO_DIR"
    git fetch origin
    git checkout "$GIT_BRANCH"
    git reset --hard "origin/$GIT_BRANCH"
else
    git clone --branch "$GIT_BRANCH" "$GIT_REPO" "$REPO_DIR"
fi

echo_info "Step 5: Running Ansible playbook..."
cd "$REPO_DIR"
ansible-playbook "$ANSIBLE_PLAYBOOK" --connection=local -i localhost,

echo_info "Step 6: Setting up ansible-pull systemd timer..."

# Create ansible-pull service
cat > /etc/systemd/system/ansible-pull.service << 'EOF'
[Unit]
Description=Ansible Pull - Update DerbyPi Configuration
Documentation=https://github.com/jimidarke/sbderbynet
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/ansible-pull \
    -U https://github.com/jimidarke/sbderbynet.git \
    -C master \
    -d /opt/derbynet-repo \
    -i localhost, \
    --connection=local \
    extras/derbypi/ansible/playbook.yml
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ansible-pull

# Don't fail the whole deployment if network is down
SuccessExitStatus=0 2
EOF

# Create ansible-pull timer
cat > /etc/systemd/system/ansible-pull.timer << EOF
[Unit]
Description=Run ansible-pull every ${ANSIBLE_PULL_INTERVAL} minutes
Documentation=https://github.com/jimidarke/sbderbynet

[Timer]
OnBootSec=5min
OnUnitActiveSec=${ANSIBLE_PULL_INTERVAL}min
RandomizedDelaySec=${ANSIBLE_PULL_DELAY}min
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
systemctl daemon-reload
systemctl enable ansible-pull.timer
systemctl start ansible-pull.timer

echo ""
echo "============================================================"
echo -e "${GREEN}  DerbyPi Bootstrap Complete!${NC}"
echo "============================================================"
echo ""
echo "The server is now configured. Services status:"
echo ""
systemctl status mosquitto nginx php*-fpm derbyrace derbytime --no-pager --lines=0 || true
echo ""
echo "ansible-pull timer:"
systemctl status ansible-pull.timer --no-pager --lines=0 || true
echo ""
echo "Verify the installation:"
echo "  curl http://localhost/derbynet/"
echo "  mosquitto_pub -h localhost -t 'derbynet/test' -m 'hello'"
echo ""
echo "View logs:"
echo "  journalctl -u derbyrace -f"
echo "  tail -f /var/log/derbynet.log"
echo ""
echo "Manual ansible-pull:"
echo "  sudo systemctl start ansible-pull.service"
echo ""

# Display public key if it exists
if [[ -f /var/lib/derbynet/keys/device.pub ]]; then
    echo "============================================================"
    echo "DEVICE PUBLIC KEY (for SaaS registration):"
    echo "============================================================"
    cat /var/lib/derbynet/keys/device.pub
    echo "============================================================"
fi

echo ""
echo "A reboot may be required for RTC and boot config changes."
echo "Run: sudo reboot"
