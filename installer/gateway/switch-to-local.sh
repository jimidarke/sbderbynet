#!/bin/bash
# switch-to-local.sh
# Emergency failover: stop cloud bridge, start full local stack
#
# Devices reconnect automatically — same IP (192.168.100.10), same ports.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== DerbyNet: Switching to LOCAL mode ==="
echo ""

# Stop the gateway bridge
echo "[1/2] Stopping cloud bridge..."
docker compose -f docker-compose.yml down 2>/dev/null || true

# Start the full local stack
echo "[2/2] Starting local fallback stack..."
docker compose -f docker-compose.fallback.yml up -d

echo ""
echo "=== LOCAL mode active ==="
echo "Web UI: http://192.168.100.10/derbynet/"
echo "MQTT:   192.168.100.10:1883 (no auth)"
echo ""
echo "To resume cloud operation: ./switch-to-cloud.sh"
