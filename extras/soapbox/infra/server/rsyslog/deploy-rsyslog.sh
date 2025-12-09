#!/bin/bash
# Deploy DerbyNet rsyslog configuration (run locally on Raspberry Pi)
#
# Usage: sudo ./deploy-rsyslog.sh
#
# This script:
# 1. Creates necessary directories 
# 2. Copies rsyslog configuration
# 3. Sets proper permissions
# 4. Restarts rsyslog service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./deploy-rsyslog.sh"
    exit 1
fi

echo "=== DerbyNet rsyslog Deployment ==="
echo ""

# Create log directories
echo "Creating log directories..."
mkdir -p /var/log/derbynet
chown 1000:1000 /var/log/derbynet
chmod 755 /var/log/derbynet

mkdir -p /var/lib/derbynet/logs/archive
chown -R 1000:1000 /var/lib/derbynet/logs/archive
chmod 755 /var/lib/derbynet/logs/archive

# Copy rsyslog configuration
echo "Installing rsyslog configuration..."
cp "${SCRIPT_DIR}/10-derbynet.conf" /etc/rsyslog.d/
chown root:root /etc/rsyslog.d/10-derbynet.conf
chmod 644 /etc/rsyslog.d/10-derbynet.conf

# Validate configuration
echo "Validating rsyslog configuration..."
if rsyslogd -N1; then
    echo "Configuration valid."
else
    echo "ERROR: Configuration validation failed!" 
    exit 1
fi

# Restart rsyslog
echo "Restarting rsyslog service..."
systemctl restart rsyslog

# Verify service status
echo ""
echo "Verifying service status..."
systemctl status rsyslog --no-pager | head -10

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Test with:"
echo "  logger -t finishtimer 'Test message from deployment'"
echo ""
echo "Monitor logs:"
echo "  tail -f /var/log/derbynet/derby.jsonl | jq ."
