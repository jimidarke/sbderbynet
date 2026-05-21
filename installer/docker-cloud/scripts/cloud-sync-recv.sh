#!/bin/bash
# cloud-sync-recv.sh — SSH ForceCommand wrapper that gates Pi-originated
# cloud-sync traffic on the VPS.
#
# Installed once on the VPS by adding the following line to the cloud-sync
# user's ~/.ssh/authorized_keys (typically claude@uisp.darketech.ca):
#
#   from="*",command="/opt/sbderbynet/installer/docker-cloud/scripts/cloud-sync-recv.sh",restrict ssh-ed25519 AAAA... derbypi-fleet-sync
#
# Three operations are permitted, all targeting paths under DATA_DIR:
#   1. `scp -t <DATA_DIR>/derbynet.sqlite3.tmp`        (Pi pushing the DB)
#   2. `scp -t <DATA_DIR>/.cloud_readonly.tmp`         (Pi pushing the sentinel)
#   3. `mv <DATA_DIR>/derbynet.sqlite3.tmp <DATA_DIR>/derbynet.sqlite3 && \
#       mv <DATA_DIR>/.cloud_readonly.tmp <DATA_DIR>/.cloud_readonly`
#                                                       (atomic swap, both files)
#
# Anything else is refused with a logged warning and exit 100.
#
# Blast radius if the fleet key leaks: an attacker can overwrite the cloud
# DB and sentinel — same as a malicious Pi could. Recovery is to rotate
# the key and resync.

set -eu

# Where the Pi is allowed to write. Hard-coded; not env-overridable to avoid
# command-injection via SSH env passthrough.
readonly DATA_DIR=/opt/derbynet/production/data
readonly DB=$DATA_DIR/derbynet.sqlite3
readonly DB_TMP=$DATA_DIR/derbynet.sqlite3.tmp
readonly SENT=$DATA_DIR/.cloud_readonly
readonly SENT_TMP=$DATA_DIR/.cloud_readonly.tmp

CMD="${SSH_ORIGINAL_COMMAND:-}"

refuse() {
    logger -t cloud-sync-recv -p auth.warning "refused: $1 (cmd=${CMD:-<none>}, from=${SSH_CONNECTION:-<unknown>})"
    echo "cloud-sync-recv: not permitted" >&2
    exit 100
}

[ -n "$CMD" ] || refuse "empty command"

# Allow scp's server-side -t (target) invocation for our two .tmp paths only.
# OpenSSH's scp client passes through client-side flags like `-v` / `-p` /
# `-q`, so we match on the trailing `-t <path>` rather than the full
# command. The path is what really matters — once we've chosen the target,
# we `exec scp -t "$PATH"` with our own controlled args, so any extra flags
# the client sent are discarded.
case "$CMD" in
    "scp -t $DB_TMP"|"scp "*" -t $DB_TMP")
        exec scp -t "$DB_TMP"
        ;;
    "scp -t $SENT_TMP"|"scp "*" -t $SENT_TMP")
        exec scp -t "$SENT_TMP"
        ;;
    "mv $DB_TMP $DB && mv $SENT_TMP $SENT")
        # Atomic swap of both files. POSIX `mv` is atomic on same filesystem;
        # back-to-back means at most a few ms of inconsistency between DB
        # and sentinel — the stats-gen 30 s tick won't notice.
        #
        # The DB+sentinel land mode 600 from sqlite3 .backup + scp, but the
        # stats-gen container runs as a non-root user that can't read 600.
        # chmod 644 here, after the mv, so the unprivileged reader can
        # actually see the file. Read-only — no risk of cloud writes.
        #
        # We DO want shell parsing of the && so use bash -c with a fixed
        # argument string (no user input passes into the shell).
        exec bash -c "mv \"$DB_TMP\" \"$DB\" && mv \"$SENT_TMP\" \"$SENT\" && chmod 644 \"$DB\" \"$SENT\""
        ;;
    *)
        refuse "command not in allowlist"
        ;;
esac
