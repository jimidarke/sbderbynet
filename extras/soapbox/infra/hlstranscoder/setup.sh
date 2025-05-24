#!/bin/bash
# HLS Transcoder Setup Script
# Version: 0.5.0
# This script sets up the HLS Transcoder component for the Soapbox Derby System
# 
# It performs the following tasks:
# - Installs required dependencies
# - Sets up configuration files
# - Configures nginx
# - Installs the service file
# - Sets up kiosk mode for displaying web content
# - Supports remote updates via rsync

set -e

# Default configuration values
CONFIG_DIR="/etc/derbynet/hlstranscoder"
INSTALL_DIR="/opt/derbynet/hlstranscoder"
SERVICE_USER="derby"
DEFAULT_RTSP_SOURCE="rtsp://admin:all4theKids@192.168.100.20:554/21" # rtsp://admin:all4theKids@192.168.100.20:554/21
DEFAULT_HLS_OUTPUT_DIR="/var/www/html/hls"
DEFAULT_SEGMENT_DURATION="4"
DEFAULT_SEGMENT_LIST_SIZE="5"
DEFAULT_FFMPEG_PRESET="ultrafast"
DEFAULT_RESOLUTION="1280x720"
DEFAULT_BITRATE="2M"
DEFAULT_MQTT_BROKER="192.168.100.10"
DEFAULT_LOG_LEVEL="INFO"
DEFAULT_KIOSK_URL="http://derbynetpc/status.html"
SERVER_ADDRESS="192.168.100.10" # same as mqtt
RSYNC_MODULE="derbynet"
UPDATE_FLAG="/boot/updated"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --config-dir)
      CONFIG_DIR="$2"
      shift
      shift
      ;;
    --install-dir)
      INSTALL_DIR="$2"
      shift
      shift
      ;;
    --service-user)
      SERVICE_USER="$2"
      shift
      shift
      ;;
    --server)
      SERVER_ADDRESS="$2"
      shift
      shift
      ;;
    --rsync-module)
      RSYNC_MODULE="$2"
      shift
      shift
      ;;
    --update)
      UPDATE_MODE=1
      shift
      ;;
    *)
      echo "Unknown option: $key"
      exit 1
      ;;
  esac
done

echo "Setting up HLS Transcoder..."
echo "Installation directory: $INSTALL_DIR"
echo "Configuration directory: $CONFIG_DIR"
echo "Service user: $SERVICE_USER"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Check for derbyid.txt
DERBY_ID_FILE="/boot/derbyid.txt"
if [ ! -f "$DERBY_ID_FILE" ]; then
  # Try alternate location
  DERBY_ID_FILE="/boot/firmware/derbyid.txt"
  if [ ! -f "$DERBY_ID_FILE" ]; then
    echo "ERROR: Missing derbyid.txt. Please create this file in /boot/ with a unique identifier."
    exit 1
  fi
fi

# Get derby ID
DERBY_ID=$(cat "$DERBY_ID_FILE")
echo "Derby ID: $DERBY_ID"

# Set hostname based on derby ID if needed
current_hostname=$(hostname)
if [ "$current_hostname" != "hlst-$DERBY_ID" ]; then
  echo "Setting hostname to hlst-$DERBY_ID..."
  hostnamectl set-hostname "hlst-$DERBY_ID"
  # Update hosts file
  sed -i "s/127.0.1.1.*/127.0.1.1\thlst-$DERBY_ID/" /etc/hosts
fi

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y \
  python3 \
  python3-pip \
  ffmpeg \
  nginx \
  chromium-browser \
  unclutter \
  x11-xserver-utils \
  mosquitto-clients \
  python3-paho-mqtt \
  python3-psutil \
  python3-zeroconf \
  python3-netifaces \
  nginx-extras

# Install Python requirements
pip3 install ffmpeg-python

# Create directories
echo "Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$DEFAULT_HLS_OUTPUT_DIR"
mkdir -p "/var/log/hlstranscoder"

# Copy files
echo "Copying files..."
#cp hlstranscoder.py "$INSTALL_DIR/"
cp hlstranscoder.service /etc/systemd/system/
cp nginx/hls.conf /etc/nginx/conf.d/
#cp kiosk.sh "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/hlstranscoder.py"
chmod +x "$INSTALL_DIR/kiosk.sh"

# Link to common libraries
echo "Linking common libraries..."
ln -sf /opt/soapbox/common/derbylogger.py "$INSTALL_DIR/derbylogger.py"
ln -sf /opt/soapbox/common/derbynet.py "$INSTALL_DIR/derbynet.py"
ln -sf /opt/soapbox/common/network_metrics.py "$INSTALL_DIR/network_metrics.py"

# Create configuration
echo "Creating configuration..."
if [ ! -f "$CONFIG_DIR/config.env" ]; then
  cat > "$CONFIG_DIR/config.env" << EOF
# HLS Transcoder Configuration
RTSP_SOURCE="$DEFAULT_RTSP_SOURCE"
HLS_OUTPUT_DIR="$DEFAULT_HLS_OUTPUT_DIR"
SEGMENT_DURATION="$DEFAULT_SEGMENT_DURATION"
SEGMENT_LIST_SIZE="$DEFAULT_SEGMENT_LIST_SIZE"
FFMPEG_PRESET="$DEFAULT_FFMPEG_PRESET"
RESOLUTION="$DEFAULT_RESOLUTION"
BITRATE="$DEFAULT_BITRATE"
MQTT_BROKER="$DEFAULT_MQTT_BROKER"
LOG_LEVEL="$DEFAULT_LOG_LEVEL"
DERBY_ID="$DERBY_ID"
KIOSK_URL="$DEFAULT_KIOSK_URL"
EOF
  echo "Created default configuration at $CONFIG_DIR/config.env"
  echo "Please review and update this file if needed."
else
  echo "Configuration exists at $CONFIG_DIR/config.env"
  echo "Kept existing configuration file."
fi

# Configure permissions
echo "Configuring permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR"
chown -R www-data:www-data "$DEFAULT_HLS_OUTPUT_DIR"
chmod 755 "$DEFAULT_HLS_OUTPUT_DIR"

# Configure nginx
echo "Configuring nginx..."
systemctl enable nginx
systemctl restart nginx

# Configure autostart
echo "Configuring service..."
systemctl daemon-reload
systemctl enable hlstranscoder.service

# Configure kiosk mode autostart
echo "Configuring kiosk mode..."
mkdir -p /home/$SERVICE_USER/.config/autostart
cat > /home/$SERVICE_USER/.config/autostart/kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=HLSTranscoder Kiosk
Exec=$INSTALL_DIR/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF
chown -R $SERVICE_USER:$SERVICE_USER /home/$SERVICE_USER/.config/autostart

# Configure system for kiosk operation
if ! grep -q "xset s off" /home/$SERVICE_USER/.xsessionrc 2>/dev/null; then
  cat > /home/$SERVICE_USER/.xsessionrc << EOF
xset s off
xset -dpms
xset s noblank
EOF
  chown $SERVICE_USER:$SERVICE_USER /home/$SERVICE_USER/.xsessionrc
  echo "Added display power management settings"
fi

# Disable screen blanking
sed -i 's/^#xserver-command=X/xserver-command=X -s 0 -dpms/' /etc/lightdm/lightdm.conf

# Check for system updates if requested
if [ -n "$UPDATE_MODE" ] || [ ! -f "$UPDATE_FLAG" ]; then
  echo "Checking for system updates..."
  
  # Try to ping a reliable internet host to verify connectivity
  if ping -c 1 google.com &> /dev/null || ping -c 1 8.8.8.8 &> /dev/null; then
    echo "Internet connectivity confirmed, proceeding with updates..."
    
    # Update the system packages
    apt-get update
    apt-get upgrade -y
    apt-get autoremove -y
    apt-get clean
    
    # Update pip packages
    pip3 install --upgrade pip
    pip3 install --upgrade ffmpeg-python paho-mqtt psutil zeroconf netifaces
    
    # Create update flag to indicate the system has been updated
    touch "$UPDATE_FLAG"
    echo "System updates completed."
  else
    echo "No internet connectivity detected, skipping system updates."
  fi
fi

# Perform rsync update if in update mode or installing
echo "Checking for application updates..."
if rsync -azh --stats "rsync://${SERVER_ADDRESS}/${RSYNC_MODULE}/hlstranscoder/" "$INSTALL_DIR/" --timeout=30; then
  echo "Successfully synced files from server."
  
  # Make sure all scripts are executable
  chmod +x "$INSTALL_DIR"/*.py "$INSTALL_DIR"/*.sh
  
  # Update the service file if it exists
  if [ -f "$INSTALL_DIR/hlstranscoder.service" ]; then
    cp "$INSTALL_DIR/hlstranscoder.service" /etc/systemd/system/
    systemctl daemon-reload
  fi
  
  # Update nginx config if it exists
  if [ -f "$INSTALL_DIR/nginx/hls.conf" ]; then
    cp "$INSTALL_DIR/nginx/hls.conf" /etc/nginx/conf.d/
    systemctl restart nginx
  fi
else
  echo "Failed to sync files from server or no server available."
  
  # If in update-only mode and rsync failed, exit with error
  if [ -n "$UPDATE_MODE" ]; then
    echo "Update failed. Exiting."
    exit 1
  fi
fi

# Start or restart the service
if systemctl is-active --quiet hlstranscoder.service; then
  echo "Restarting HLS Transcoder service..."
  systemctl restart hlstranscoder.service
else
  echo "Starting HLS Transcoder service..."
  systemctl start hlstranscoder.service
fi

echo "Setup complete!"
echo "HLS Transcoder should now be running."
echo "To view logs, run: journalctl -u hlstranscoder"
echo "To restart the service, run: systemctl restart hlstranscoder"
echo "To view status, run: systemctl status hlstranscoder"
echo "To update from server, run: $INSTALL_DIR/sync.sh"