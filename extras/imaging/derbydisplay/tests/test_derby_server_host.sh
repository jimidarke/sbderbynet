#!/usr/bin/env bash
# Tests for derby-server-host: resolve the kiosk's server host from
# /boot/firmware/derby-server.txt, robust to comments/blank/CRLF, with a
# safe default. The helper honors $DERBY_SERVER_FILE so we can point it at
# temp fixtures instead of /boot/firmware.
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HELPER="$HERE/../rootfs/usr/local/sbin/derby-server-host"
DEFAULT="192.168.100.10"

pass=0; fail=0
check() { # description  expected  actual
  if [ "$2" = "$3" ]; then
    pass=$((pass+1)); printf 'ok   - %s\n' "$1"
  else
    fail=$((fail+1)); printf 'FAIL - %s\n       expected [%s] got [%s]\n' "$1" "$2" "$3"
  fi
}

# Run the helper with a given fixture file path (empty = no file / missing).
run_with() { DERBY_SERVER_FILE="$1" "$HELPER" 2>/dev/null; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# 1. plain valid IP
printf '192.168.100.10\n' > "$tmp/a"
check "valid default IP returned verbatim" "192.168.100.10" "$(run_with "$tmp/a")"

# 2. a different IP
printf '192.168.1.55\n' > "$tmp/b"
check "alternate IP returned" "192.168.1.55" "$(run_with "$tmp/b")"

# 3. missing file -> default
check "missing file falls back to default" "$DEFAULT" "$(run_with "$tmp/does-not-exist")"

# 4. blank file -> default
printf '\n\n' > "$tmp/blank"
check "blank file falls back to default" "$DEFAULT" "$(run_with "$tmp/blank")"

# 5. comment-only file -> default
printf '# just a comment\n#another\n' > "$tmp/comments"
check "comment-only file falls back to default" "$DEFAULT" "$(run_with "$tmp/comments")"

# 6. comment then value -> value
printf '# edit the IP below\n10.0.0.9\n' > "$tmp/comval"
check "skips comment, returns first value" "10.0.0.9" "$(run_with "$tmp/comval")"

# 7. CRLF (Windows Notepad) -> stripped
printf '10.0.0.5\r\n' > "$tmp/crlf"
check "CRLF line ending stripped" "10.0.0.5" "$(run_with "$tmp/crlf")"

# 8. leading/trailing whitespace -> trimmed
printf '   10.0.0.7   \n' > "$tmp/ws"
check "surrounding whitespace trimmed" "10.0.0.7" "$(run_with "$tmp/ws")"

# 9. hostname (not validated, read as-is)
printf 'derby.local\n' > "$tmp/host"
check "hostname returned as-is" "derby.local" "$(run_with "$tmp/host")"

# 10. value on a later line after blanks+comments
printf '\n# header\n\n192.168.50.2\n10.10.10.10\n' > "$tmp/multi"
check "first real value among blanks/comments" "192.168.50.2" "$(run_with "$tmp/multi")"

echo "-----"
printf '%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
