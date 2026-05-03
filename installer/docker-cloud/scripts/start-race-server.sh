#!/bin/bash
# start-race-server.sh
# Starts derbyRace.py and derbyTime.py services for DerbyNet
# Waits for dependencies (MQTT, DerbyNet web) before starting

set -e

echo "=== DerbyNet Race Server Starting ==="
echo "MQTT Broker: ${MQTT_BROKER}:${MQTT_PORT}"
echo "DerbyNet API: ${DERBYNET_API_HOST}"
echo "Lane Count: ${LANE_COUNT}"
echo "Debug Mode: ${DERBY_DEBUG}"
echo ""

# Wait for MQTT broker to be available
echo "[1/3] Waiting for MQTT broker..."
MAX_RETRIES=30
RETRY_COUNT=0
until nc -z ${MQTT_BROKER} ${MQTT_PORT} 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: MQTT broker not available after ${MAX_RETRIES} attempts"
        exit 1
    fi
    echo "  MQTT not ready (attempt ${RETRY_COUNT}/${MAX_RETRIES}), waiting..."
    sleep 2
done
echo "  MQTT broker is available"

# Wait for DerbyNet web application to be available
echo "[2/3] Waiting for DerbyNet web application..."
RETRY_COUNT=0
until curl -sf "http://${DERBYNET_API_HOST}/" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: DerbyNet web not available after ${MAX_RETRIES} attempts"
        exit 1
    fi
    echo "  DerbyNet web not ready (attempt ${RETRY_COUNT}/${MAX_RETRIES}), waiting..."
    sleep 2
done
echo "  DerbyNet web application is available"

# Start services
echo "[3/3] Starting race server services..."

# Start derbyTime.py in background
echo "  Starting derbyTime.py..."
python3 /var/lib/infra/app/derbyTime.py &
DERBYTIME_PID=$!
echo "  derbyTime.py started (PID: ${DERBYTIME_PID})"

# Brief delay to allow derbyTime to initialize
sleep 2

# Start derbyRace.py in foreground
echo "  Starting derbyRace.py..."
echo ""
echo "=== Race Server Ready ==="
echo ""
exec python3 /var/lib/infra/app/derbyRace.py
