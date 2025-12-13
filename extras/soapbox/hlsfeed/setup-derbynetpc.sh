#!/bin/bash
# DerbyNet PC Setup Script for Beelink Mini S12
# Version: 0.8.0
# Purpose: Configure the Beelink Mini PC for optimal DerbyNet multicam operation

# Exit on any error
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="/opt/derbynet/derbynetpc-dual-display.conf"
LOG_FILE="/var/log/derbynetpc-setup.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log "ERROR: This script must be run as root"
   exit 1
fi

log "Starting DerbyNet PC setup for Beelink Mini S12..."

# Update system packages
log "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
log "Installing required packages..."
apt install -y \
    chromium-browser \
    x11-xserver-utils \
    xorg \
    lightdm \
    openbox \
    feh \
    unclutter-xfixes \
    ffmpeg \
    nginx \
    mosquitto \
    mosquitto-clients \
    python3 \
    python3-pip \
    psutil \
    git \
    curl \
    wget \
    htop \
    iftop \
    intel-media-va-driver \
    vainfo

# Install Python packages
log "Installing Python packages..."
pip3 install paho-mqtt psutil

# Create derbynet user and directories
log "Creating derbynet user and directories..."
if ! id "derbynet" &>/dev/null; then
    useradd -m -G video,audio,input,render,dialout derbynet
fi

mkdir -p /opt/derbynet/{config,logs,scripts}
mkdir -p /opt/hlsfeed/{hls,videos,config}
mkdir -p /var/log/hlsfeed

# Copy configuration file
log "Installing configuration file..."
cp "$SCRIPT_DIR/derbynetpc-dual-display.conf" "$CONFIG_FILE"
chown derbynet:derbynet "$CONFIG_FILE"

# Configure dual display setup
log "Configuring dual display setup..."
cat > /etc/X11/xorg.conf.d/20-dual-display.conf << 'EOF'
Section "Monitor"
    Identifier "HDMI-1"
    Option "Primary" "true"
    Option "Position" "0 0"
    Option "PreferredMode" "1920x1080"
EndSection

Section "Monitor" 
    Identifier "HDMI-2"
    Option "Position" "1920 0"
    Option "PreferredMode" "1920x1080"
EndSection

Section "Screen"
    Identifier "Screen0"
    Monitor "HDMI-1"
    DefaultDepth 24
EndSection

Section "Screen"
    Identifier "Screen1" 
    Monitor "HDMI-2"
    DefaultDepth 24
EndSection

Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF

# Configure autologin for derbynet user
log "Configuring autologin..."
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/50-derbynet-autologin.conf << 'EOF'
[Seat:*]
autologin-user=derbynet
autologin-user-timeout=0
user-session=openbox
EOF

# Create primary display startup script (HDMI-1 - Main Kiosk)
log "Creating primary display startup script..."
cat > /home/derbynet/.config/openbox/autostart << 'EOF'
#!/bin/bash
# Primary Display Autostart (HDMI-1)

# Set display
export DISPLAY=:0.0

# Wait for network
sleep 10

# Get MAC address for kiosk identification
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || echo "NOMAC")

# Hide cursor
unclutter-xfixes --timeout 0 --hide-on-touch &

# Start primary kiosk display
URL="http://192.168.100.10/derbynet/kiosk.php?address=${MAC}"
chromium-browser \
    --kiosk \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu-sandbox \
    --noerrdialogs \
    --disable-translate \
    --disable-features=TranslateUI \
    --window-position=0,0 \
    --window-size=1920,1080 \
    "$URL" &

# Wait a moment then start secondary display
sleep 5

# Start secondary status dashboard on HDMI-2
DISPLAY=:0.1 chromium-browser \
    --new-window \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu-sandbox \
    --window-position=1920,0 \
    --window-size=1920,1080 \
    --app="file:///opt/derbynet/status_dashboard.html" &
EOF

# Ensure the autostart directory and file exist with proper ownership
mkdir -p /home/derbynet/.config/openbox
chown -R derbynet:derbynet /home/derbynet/.config
chmod +x /home/derbynet/.config/openbox/autostart

# Copy status dashboard
log "Installing status dashboard..."
cp "$SCRIPT_DIR/../derbydisplay/status_dashboard.html" /opt/derbynet/
chown derbynet:derbynet /opt/derbynet/status_dashboard.html

# Configure CPU governor for performance
log "Configuring CPU governor..."
echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils

# Disable unnecessary services for performance
log "Disabling unnecessary services..."
systemctl disable bluetooth.service || true
systemctl disable cups.service || true
systemctl disable cups-browsed.service || true

# Configure network interface
log "Configuring network interface..."
cat > /etc/netplan/01-derbynet-config.yaml << 'EOF'
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      dhcp6: false
      optional: true
  wifis: {}
EOF

# Apply network configuration
netplan apply

# Create systemd service for DerbyNet PC monitoring
log "Creating monitoring service..."
cat > /etc/systemd/system/derbynetpc-monitor.service << 'EOF'
[Unit]
Description=DerbyNet PC System Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=derbynet
Group=derbynet
ExecStart=/opt/derbynet/scripts/monitor.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/derbynet/scripts

[Install]
WantedBy=multi-user.target
EOF

# Create monitoring script
log "Creating monitoring script..."
cat > /opt/derbynet/scripts/monitor.py << 'EOF'
#!/usr/bin/env python3
"""
DerbyNet PC System Monitor
Monitors system health and reports status via MQTT using standardized telemetry format
Version: 0.8.0
"""

import json
import time
import psutil
import paho.mqtt.client as mqtt
import subprocess
import logging
import uuid
import socket
import os
from datetime import datetime

# Version information - standardized across all DerbyNet components
VERSION = "0.8.0"
DEVICE_CLASS = "PC"

# Setup logging compatible with DerbyNet infrastructure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/derbynet/derbynetpc-monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DerbyNetPC')

class DerbyNetPCMonitor:
    def __init__(self):
        self.hostname = "derbynetpc"
        self.device_type = "multicam-server"
        self.start_time = time.time()
        
        # Get hardware ID using same method as other components
        if os.path.exists("/etc/machine-id"):
            with open("/etc/machine-id", "r") as f:
                self.hwid = f.read().strip()
        else:
            self.hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
        
        # MQTT setup with auto-reconnect similar to other components
        self.mqtt_client = mqtt.Client(client_id=f"derbynetpc_{int(time.time())}")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.connected = False
        
        logger.info(f"DerbyNet PC Monitor v{VERSION} initialized with HWID: {self.hwid}")
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker with result code {rc}")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
        
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
            
    def get_system_metrics(self):
        """Collect standardized DerbyNet telemetry format"""
        try:
            # Standard telemetry fields used by finish timers and kiosks
            payload = {
                # Standard device identification
                "hostname": self.hostname,
                "hwid": self.hwid,
                "device_class": DEVICE_CLASS,
                "version": VERSION,
                "time": int(time.time()),
                "uptime": int(time.time() - self.start_time),
                
                # Network information
                "ip": self.get_ip(),
                "mac": self.get_mac(),
                "wifi_rssi": self.get_wifi_rssi(),
                
                # System resources (standardized format)
                "cpu_usage": psutil.cpu_percent(interval=1),
                "cpu_temp": self.get_cpu_temp(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent,
                
                # DerbyNet PC specific fields
                "displays": self.check_displays(),
                "camera_streams": self.check_camera_streams(),
                "services": self.check_services(),
                "gpu_temp": self.get_gpu_temp(),
                "load_average": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
                
                # Performance metrics
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "cpu_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                
                # Network traffic
                "network_bytes_sent": psutil.net_io_counters().bytes_sent,
                "network_bytes_recv": psutil.net_io_counters().bytes_recv,
            }
            
            return payload
            
        except Exception as e:
            logger.error(f"Error collecting telemetry: {e}")
            return {}
    
    def get_ip(self):
        """Get primary IP address"""
        try:
            return subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode("utf-8").strip()
        except:
            return None
    
    def get_mac(self):
        """Get MAC address in standardized format"""
        return ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])
    
    def get_cpu_temp(self):
        """Get CPU temperature (Intel-specific for N95)"""
        try:
            # Try Intel thermal sensors
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    return float(f.read()) / 1000.0
            # Try sensors command for Intel
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Core 0' in line or 'Package id 0' in line:
                        for part in line.split():
                            if '°C' in part:
                                return float(part.replace('°C', '').replace('+', ''))
        except:
            pass
        return None
    
    def get_gpu_temp(self):
        """Get GPU temperature (Intel integrated graphics)"""
        try:
            # Try Intel GPU thermal zone
            if os.path.exists('/sys/class/thermal/thermal_zone1/temp'):
                with open('/sys/class/thermal/thermal_zone1/temp', 'r') as f:
                    return float(f.read()) / 1000.0
        except:
            pass
        return None
    
    def get_wifi_rssi(self):
        """Get WiFi signal strength (if applicable)"""
        try:
            # Check if WiFi is disabled (as configured)
            if not os.path.exists('/sys/class/net/wlan0'):
                return None
            result = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Signal level' in line:
                        for part in line.split():
                            if 'level=' in part:
                                return int(part.split('=')[1])
        except:
            pass
        return None
    
    def check_displays(self):
        """Check status of dual HDMI displays"""
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"error": "xrandr failed"}
                
            displays = {}
            for line in result.stdout.split('\n'):
                if ' connected' in line:
                    parts = line.split()
                    display_name = parts[0]
                    connected = 'connected' in line
                    primary = 'primary' in line
                    
                    # Extract resolution if available
                    resolution = None
                    for part in parts:
                        if 'x' in part and '+' in part:
                            resolution = part.split('+')[0]
                            break
                            
                    displays[display_name] = {
                        'connected': connected,
                        'primary': primary,
                        'resolution': resolution,
                        'active': resolution is not None
                    }
                    
            return displays
        except Exception as e:
            logger.error(f"Error checking displays: {e}")
            return {"error": str(e)}
    
    def check_camera_streams(self):
        """Check status of camera streaming processes"""
        try:
            # Check for FFmpeg processes (multicam service)
            ffmpeg_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'ffmpeg':
                        ffmpeg_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': ' '.join(proc.info['cmdline'][:3])  # First 3 args for brevity
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                'active_streams': len(ffmpeg_processes),
                'processes': ffmpeg_processes
            }
        except Exception as e:
            logger.error(f"Error checking camera streams: {e}")
            return {"error": str(e)}
    
    def check_services(self):
        """Check status of key DerbyNet services"""
        services = ['multicam-service', 'derbynetpc-monitor', 'nginx', 'mosquitto']
        status = {}
        
        for service in services:
            try:
                result = subprocess.run(['systemctl', 'is-active', service], 
                                      capture_output=True, text=True, timeout=2)
                status[service] = result.stdout.strip()
            except Exception as e:
                status[service] = "error"
                
        return status
    
    def publish_telemetry(self, payload):
        """Publish telemetry using standardized DerbyNet topics"""
        try:
            # Use same topic structure as finish timers and kiosks
            telemetry_topic = f"derbynet/device/{self.hwid}/telemetry"
            status_topic = f"derbynet/device/{self.hwid}/status"
            
            # Publish telemetry with QoS 1 and retain flag (standard for DerbyNet)
            if self.connected:
                self.mqtt_client.publish(telemetry_topic, json.dumps(payload), qos=1, retain=True)
                self.mqtt_client.publish(status_topic, "online", qos=1, retain=True)
                logger.debug(f"Published telemetry: CPU {payload.get('cpu_usage', 0):.1f}%, Memory {payload.get('memory_usage', 0):.1f}%")
            else:
                logger.warning("Not connected to MQTT broker, telemetry not sent")
                
        except Exception as e:
            logger.error(f"Error publishing telemetry: {e}")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting DerbyNet PC Monitor")
        
        # Connect to MQTT broker with retry logic
        broker_ip = "192.168.100.10"
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.mqtt_client.connect(broker_ip, 1883, 60)
                self.mqtt_client.loop_start()
                logger.info(f"Connected to MQTT broker at {broker_ip}")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Failed to connect to MQTT broker (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)  # Exponential backoff
                else:
                    logger.error("Max connection attempts reached, continuing without MQTT")
        
        # Main monitoring loop
        telemetry_interval = 5  # seconds (same as finish timers)
        last_telemetry_time = 0
        
        try:
            while True:
                current_time = time.time()
                
                # Send telemetry at regular intervals
                if current_time - last_telemetry_time >= telemetry_interval:
                    telemetry = self.get_system_metrics()
                    if telemetry:
                        self.publish_telemetry(telemetry)
                        last_telemetry_time = current_time
                
                time.sleep(1)  # Check every second for responsiveness
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        finally:
            # Clean shutdown
            try:
                if self.connected:
                    self.mqtt_client.publish(f"derbynet/device/{self.hwid}/status", "offline", qos=1, retain=True)
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass
            logger.info("DerbyNet PC Monitor stopped")

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('/var/log/derbynet', exist_ok=True)
    
    monitor = DerbyNetPCMonitor()
    monitor.run()
EOF

chmod +x /opt/derbynet/scripts/monitor.py
chown -R derbynet:derbynet /opt/derbynet

# Enable and start services
log "Enabling services..."
systemctl enable lightdm
systemctl enable derbynetpc-monitor
systemctl daemon-reload

# Configure Intel Quick Sync Video
log "Configuring Intel Quick Sync Video..."
usermod -a -G video,render derbynet

# Create FFmpeg configuration for hardware acceleration
cat > /opt/hlsfeed/ffmpeg-qsv.conf << 'EOF'
# Intel Quick Sync Video configuration for Beelink Mini S12 N95
# Enable hardware-accelerated encoding

# Check for QSV availability
vainfo_output=$(vainfo 2>/dev/null | grep -i "VAEntrypointEncSlice" || echo "")

if [ -n "$vainfo_output" ]; then
    export FFMPEG_VAAPI_DEVICE=/dev/dri/renderD128
    export FFMPEG_QSV_DEVICE=/dev/dri/renderD128
else
    echo "Warning: Intel Quick Sync Video not detected"
fi
EOF

# Set up log rotation
log "Configuring log rotation..."
cat > /etc/logrotate.d/derbynetpc << 'EOF'
/var/log/derbynetpc-*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 derbynet derbynet
}

/var/log/hlsfeed/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 derbynet derbynet
}
EOF

# Create system optimization script
log "Creating system optimization script..."
cat > /opt/derbynet/scripts/optimize.sh << 'EOF'
#!/bin/bash
# System optimization for DerbyNet PC

# Set CPU governor to performance
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase network buffer sizes
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf

# Apply sysctl changes
sysctl -p

# Set process limits for derbynet user
echo 'derbynet soft nofile 65536' >> /etc/security/limits.conf
echo 'derbynet hard nofile 65536' >> /etc/security/limits.conf
echo 'derbynet soft nproc 32768' >> /etc/security/limits.conf
echo 'derbynet hard nproc 32768' >> /etc/security/limits.conf

echo "System optimization complete"
EOF

chmod +x /opt/derbynet/scripts/optimize.sh

# Run optimization
log "Running system optimization..."
/opt/derbynet/scripts/optimize.sh

# Create startup verification script
log "Creating startup verification script..."
cat > /opt/derbynet/scripts/verify-startup.sh << 'EOF'
#!/bin/bash
# Verify that both displays are working correctly

sleep 30  # Wait for displays to initialize

# Check if both displays are connected
DISPLAY_COUNT=$(xrandr | grep " connected" | wc -l)

if [ "$DISPLAY_COUNT" -ge 2 ]; then
    echo "SUCCESS: $DISPLAY_COUNT displays detected"
    logger "DerbyNet PC: $DISPLAY_COUNT displays detected"
else
    echo "WARNING: Only $DISPLAY_COUNT display(s) detected"
    logger "DerbyNet PC: Only $DISPLAY_COUNT display(s) detected"
fi

# Check if browser processes are running
BROWSER_COUNT=$(pgrep chromium-browser | wc -l)

if [ "$BROWSER_COUNT" -ge 2 ]; then
    echo "SUCCESS: $BROWSER_COUNT browser instances running"
    logger "DerbyNet PC: $BROWSER_COUNT browser instances running"
else
    echo "WARNING: Only $BROWSER_COUNT browser instance(s) running"
    logger "DerbyNet PC: Only $BROWSER_COUNT browser instance(s) running"
fi
EOF

chmod +x /opt/derbynet/scripts/verify-startup.sh

# Add verification to user session
echo "/opt/derbynet/scripts/verify-startup.sh &" >> /home/derbynet/.config/openbox/autostart

log "DerbyNet PC setup complete!"
log "System will be optimized for:"
log "  - Dual HDMI displays (1920x1080 each)"
log "  - Intel Quick Sync Video hardware acceleration"
log "  - Performance tuning for 4-core N95 processor"
log "  - Automatic kiosk display startup"
log "  - System monitoring and MQTT reporting"
log ""
log "Next steps:"
log "  1. Reboot the system"
log "  2. Verify both displays are working"
log "  3. Check that kiosk and status dashboard load correctly"
log "  4. Monitor system performance via MQTT or logs"

# Set up automatic reboot reminder
echo "echo 'REMINDER: Please reboot to complete DerbyNet PC setup'" > /etc/update-motd.d/99-derbynet-reminder
chmod +x /etc/update-motd.d/99-derbynet-reminder

log "Setup completed. Please reboot the system to activate all changes."