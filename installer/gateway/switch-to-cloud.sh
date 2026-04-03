#!/bin/bash
# switch-to-cloud.sh
# Resume cloud operation: stop local stack, start cloud bridge gateway
#
# Devices reconnect automatically to the local broker which bridges to cloud.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== DerbyNet: Switching to CLOUD mode ==="
echo ""

# Stop the local fallback stack
echo "[1/2] Stopping local stack..."
docker compose -f docker-compose.fallback.yml down 2>/dev/null || true

# Start the gateway bridge
echo "[2/2] Starting cloud bridge gateway..."
docker compose -f docker-compose.yml up -d

echo ""
echo "=== CLOUD mode active ==="
echo "Local MQTT bridge: 192.168.100.10:1883 → cloud broker"
echo "Devices connect locally, messages relay to cloud"
echo ""
echo "To switch to local-only: ./switch-to-local.sh"
