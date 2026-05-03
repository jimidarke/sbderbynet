#!/bin/bash
# setup-mqtt-auth.sh
# Generate Mosquitto password file for authenticated MQTT access
#
# Usage: ./setup-mqtt-auth.sh [username] [password]
#   Or set MQTT_USER and MQTT_PASS environment variables
#
# The password file is mounted into the Mosquitto container at
# /mosquitto/config/passwd

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MQTT_DIR="${SCRIPT_DIR}/../mosquitto"
PASSWD_FILE="${MQTT_DIR}/passwd"

# Get credentials from args or env
USERNAME="${1:-${MQTT_USER:-derbynet}}"
PASSWORD="${2:-${MQTT_PASS}}"

if [ -z "$PASSWORD" ]; then
    echo "Usage: $0 [username] [password]"
    echo "   Or: MQTT_USER=user MQTT_PASS=pass $0"
    echo ""
    echo "This creates a password file for Mosquitto MQTT broker authentication."
    echo "The bridge gateway and internal services use these credentials."
    exit 1
fi

# Generate password file using mosquitto_passwd in a temporary container
echo "Generating MQTT password file for user: ${USERNAME}"
docker run --rm -v "${MQTT_DIR}:/mosquitto/config" eclipse-mosquitto:2 \
    mosquitto_passwd -b -c /mosquitto/config/passwd "${USERNAME}" "${PASSWORD}"

# Always provision the virtual-device user used by browser virtual hardware
# (cloud-only). The ACL in mosquitto/acl restricts it to derbynet/device/B_*
# so a leaked browser cred cannot impersonate real hardware.
VIRTUAL_USER="${VIRTUAL_MQTT_USER:-virtual-device}"
VIRTUAL_PASSWORD="${VIRTUAL_MQTT_PASS:-}"
if [ -z "$VIRTUAL_PASSWORD" ]; then
    # Auto-generate one if not supplied; surface it so the operator can
    # set VIRTUAL_MQTT_PASS in .env to make it stable across re-runs.
    VIRTUAL_PASSWORD="$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '=+/' | head -c 24)"
    echo "Generated virtual-device password: ${VIRTUAL_PASSWORD}"
    echo "Add to .env to keep it stable: VIRTUAL_MQTT_PASS=${VIRTUAL_PASSWORD}"
fi
echo "Adding virtual-device user: ${VIRTUAL_USER}"
docker run --rm -v "${MQTT_DIR}:/mosquitto/config" eclipse-mosquitto:2 \
    mosquitto_passwd -b /mosquitto/config/passwd "${VIRTUAL_USER}" "${VIRTUAL_PASSWORD}"

echo "Password file created at: ${PASSWD_FILE}"
echo ""
echo "To add additional users (without -c flag to avoid overwriting):"
echo "  docker run --rm -v '${MQTT_DIR}:/mosquitto/config' eclipse-mosquitto:2 \\"
echo "    mosquitto_passwd -b /mosquitto/config/passwd <username> <password>"
