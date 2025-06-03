#!/bin/bash
# Sync soapbox files to Raspberry Pi with proper line ending conversion
# Usage: ./sync-to-pi.sh <pi-hostname-or-ip> [target-directory]

if [ $# -lt 1 ]; then
    echo "Usage: $0 <pi-hostname-or-ip> [target-directory]"
    echo "Example: $0 192.168.100.15 /opt/derbynet"
    exit 1
fi

PI_HOST="$1"
TARGET_DIR="${2:-/opt/derbynet}"
SOURCE_DIR="$(dirname "$0")"

echo "Syncing soapbox files to $PI_HOST:$TARGET_DIR"
echo "Source directory: $SOURCE_DIR"

# Sync files with line ending conversion
rsync -av --progress \
    --iconv=utf-8,utf-8 \
    --chmod=D755,F644 \
    --exclude=".git*" \
    --exclude="*.tar.gz" \
    --exclude="*.log" \
    --exclude="__pycache__" \
    "$SOURCE_DIR/" "pi@$PI_HOST:$TARGET_DIR/"

# Fix permissions and line endings on the target
echo "Fixing permissions and line endings on target..."
ssh "pi@$PI_HOST" "
    cd '$TARGET_DIR' &&
    find . -name '*.sh' -type f -exec chmod +x {} \; &&
    find . -name '*.py' -type f -exec chmod +x {} \; &&
    if command -v dos2unix >/dev/null 2>&1; then
        find . -name '*.sh' -type f -exec dos2unix {} \; 2>/dev/null
        find . -name '*.py' -type f -exec dos2unix {} \; 2>/dev/null
    else
        echo 'Installing dos2unix...'
        sudo apt update && sudo apt install -y dos2unix
        find . -name '*.sh' -type f -exec dos2unix {} \; 2>/dev/null
        find . -name '*.py' -type f -exec dos2unix {} \; 2>/dev/null
    fi
"

echo "Sync completed to $PI_HOST:$TARGET_DIR"