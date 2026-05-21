#!/bin/bash
# derby-firstboot.sh — universal first-boot dispatcher.
#
# Runs once on first boot via /etc/systemd/system/derby-firstboot.service.
# Role is determined by /etc/derby-role (baked at image build time).
# Identity is /boot/firmware/derbyid.txt (operator-editable on Windows).
#
# Per-role hooks live at /usr/local/sbin/derby-firstboot-<role>.sh and are
# invoked after the common steps below. After successful completion, the
# service self-disables so this script never runs again on the same SD.

set -uo pipefail

LOG=/var/log/derby-firstboot.log
ROLE_FILE=/etc/derby-role
ID_FILE=/boot/firmware/derbyid.txt

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

if [[ ! -f $ROLE_FILE ]]; then
    log "FATAL: $ROLE_FILE missing — image build is broken."
    exit 1
fi
ROLE=$(< "$ROLE_FILE")
log "starting first-boot for role=$ROLE"

# 1. Identity
if [[ ! -f $ID_FILE ]]; then
    log "WARN: $ID_FILE missing, using placeholder"
    DERBYID=CHANGE-ME
else
    DERBYID=$(tr -d '[:space:]' < "$ID_FILE")
fi
log "derbyid=$DERBYID"

# 2. Hostname (only set if operator filled it in)
if [[ $DERBYID != CHANGE-ME && $DERBYID != "" ]]; then
    hostnamectl set-hostname "$DERBYID"
    sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$DERBYID/" /etc/hosts || \
        echo -e "127.0.1.1\t$DERBYID" >> /etc/hosts
    log "hostname set to $DERBYID"
fi

# 3. SSH host-key regeneration is handled by the shipped
#    regenerate_ssh_host_keys.service (enabled at build time in
#    _common/customize.sh, self-disables after running). The keys were
#    wiped during the build so the unit will produce per-card uniques on
#    first boot ahead of this script.

# 4. Per-role hook
HOOK=/usr/local/sbin/derby-firstboot-${ROLE}.sh
if [[ -x $HOOK ]]; then
    log "running role hook: $HOOK"
    if ! "$HOOK" >> "$LOG" 2>&1; then
        log "FATAL: role hook $HOOK failed; leaving service enabled for retry"
        exit 1
    fi
else
    log "no role-specific hook found at $HOOK (ok for some roles)"
fi

# 5. Self-disable
systemctl disable derby-firstboot.service
log "first-boot complete; service disabled"

# 6. Reboot so any kernel/config changes take effect cleanly
log "rebooting in 5s..."
sync
sleep 5
reboot
