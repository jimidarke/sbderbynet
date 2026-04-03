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

echo "Password file created at: ${PASSWD_FILE}"
echo ""
echo "To add additional users (without -c flag to avoid overwriting):"
echo "  docker run --rm -v '${MQTT_DIR}:/mosquitto/config' eclipse-mosquitto:2 \\"
echo "    mosquitto_passwd -b /mosquitto/config/passwd <username> <password>"
