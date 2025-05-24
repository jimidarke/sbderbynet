#!/usr/bin/env python3
"""
HLS Transcoder for DerbyNet Soapbox Derby System

This component transcodes video streams from RTSP to HLS format, providing
adaptive streaming capabilities for race viewing and replay. It also monitors
stream health and provides telemetry via MQTT. Includes replay handling for
DerbyNet integration and zeroconf service discovery.

Version History:
- 0.7.0: Added zeroconf service discovery and improved network resilience
- 0.6.0: Added DerbyNet replay handler integration from hlsfeed
- 0.5.0: Initial version with RTSP to HLS transcoding, MQTT telemetry, and web status API
"""

VERSION = "0.7.0"

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
import threading
import socket
import http.server
import socketserver
from datetime import datetime
import shutil
import psutil
import netifaces as ni
from pathlib import Path
import urllib.parse

# Import DerbyNet common libraries
try:
    from derbylogger import DerbyLogger
    from derbynet import MQTTClient
    from network_metrics import NetworkMetrics
except ImportError:
    # For development, try relative import
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from derbylogger import DerbyLogger
        from derbynet import MQTTClient
        from network_metrics import NetworkMetrics
    except ImportError:
        print("ERROR: Could not import DerbyNet common libraries")
        print("Please ensure derbylogger.py, derbynet.py, and network_metrics.py are available")
        sys.exit(1)

# Import zeroconf if available
try:
    from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
    from zeroconf.const import TYPE_ANY
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("WARNING: zeroconf module not available; service discovery will be disabled")
    print("To enable service discovery, install zeroconf: pip install zeroconf")

# Global variables
running = True
current_process = None
config = {}
stream_status = {
    "status": "INITIALIZING",
    "last_update": datetime.now().isoformat(),
    "stream_info": {},
    "errors": []
}
status_lock = threading.Lock()
mqtt_client = None
logger = None
network_metrics = None
zeroconf = None
zeroconf_service = None
discovered_services = {}
discovered_services_lock = threading.Lock()

# Replay handler state
replay_state = {
    'class': None,
    'round': None,
    'heat': None,
    'timestamp': None,
    'recording': False,
    'replay_pending': False,
    'recording_process': None,
    'replay_process': None
}
replay_lock = threading.Lock()

def load_config(config_file):
    """
    Load configuration from environment file
    """
    global config
    
    # Default configuration
    config = {
        "RTSP_SOURCE": "rtsp://192.168.100.10:8554/stream",
        "HLS_OUTPUT_DIR": "/var/www/html/hls",
        "SEGMENT_DURATION": "4",
        "SEGMENT_LIST_SIZE": "5",
        "FFMPEG_PRESET": "ultrafast",
        "RESOLUTION": "1280x720",
        "BITRATE": "2M",
        "CODEC": "libx264",
        "MQTT_BROKER": "localhost",
        "MQTT_PORT": "1883",
        "MQTT_USERNAME": "",
        "MQTT_PASSWORD": "",
        "LOG_LEVEL": "INFO",
        "DERBY_ID": "",
        "DEVICE_NAME": "hlstranscoder",
        "KIOSK_URL": "http://localhost/status.html",
        "API_PORT": "8038",
        "ENABLE_API": "true",
        "HLS_PLAYLIST_TYPE": "event",
        "HLS_LIST_SIZE": "5",
        "CLEANUP_OLD_SEGMENTS": "true",
        "MAX_SEGMENT_AGE": "300",
        "ENABLE_ARCHIVE": "false",
        "ARCHIVE_DIR": "/var/www/html/archive",
        "ARCHIVE_FORMAT": "mkv",
        "ARCHIVE_RETENTION_DAYS": "7",
        # Added for replay functionality
        "REPLAY_BUFFER_TIME": "4000",
        "REPLAY_PLAYBACK_RATE": "50",
        "REPLAY_NUM_SHOWINGS": "2",
        "REPLAY_VIDEO_DIR": "/var/www/html/replay",
        "REPLAY_TOPIC": "derbynet/replay/command",
        "STATUS_TOPIC": "derbynet/replay/status",
        "DERBYNET_HOSTNAME": "derbynetpi",
        # Added for zeroconf functionality
        "ENABLE_ZEROCONF": "true",
        "SERVICE_TYPE": "_derbynet._tcp.local.",
        "RTSP_FINDER_SERVICE": "_rtsp._tcp.local.",
        "FINISHTIMER_SERVICE": "_derbynet-finishtimer._tcp.local.",
        "AUTO_DISCOVER_RTSP": "true",
        "ENABLE_NETWORK_METRICS": "true"
    }
    
    # Try to load config from file
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        config[key] = value
                    except ValueError:
                        pass
    else:
        print(f"WARNING: Config file {config_file} not found, using defaults")
    
    # Try to load DERBY_ID from /boot/derbyid.txt if not set
    if not config["DERBY_ID"]:
        try:
            with open("/boot/derbyid.txt", "r") as f:
                config["DERBY_ID"] = f.read().strip()
        except:
            try:
                # Try alternate location for some OS installations
                with open("/boot/firmware/derbyid.txt", "r") as f:
                    config["DERBY_ID"] = f.read().strip()
            except:
                hostname = socket.gethostname()
                config["DERBY_ID"] = hostname
                print(f"WARNING: DERBY_ID not set, using hostname: {hostname}")
    
    # Ensure replay video directory exists
    os.makedirs(config["REPLAY_VIDEO_DIR"], exist_ok=True)
    
    return config

def setup_logger(log_level="INFO"):
    """
    Set up the logger using DerbyLogger
    """
    global logger
    
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    logger = DerbyLogger(
        name="hlstranscoder",
        log_file="/var/log/hlstranscoder/hlstranscoder.log",
        console=True,
        level=log_level
    )
    logger.info(f"HLS Transcoder {VERSION} starting up")
    logger.info(f"DERBY_ID: {config['DERBY_ID']}")
    logger.info(f"Device name: {config['DEVICE_NAME']}")
    return logger

def get_system_info():
    """
    Get system information for telemetry
    """
    info = {
        "hostname": socket.gethostname(),
        "hwid": config["DERBY_ID"],
        "version": VERSION,
        "uptime": int(time.time() - psutil.boot_time()),
        "cpu_temp": get_cpu_temperature(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "stream_status": stream_status["status"]
    }
    
    # Get IP and MAC address
    try:
        interfaces = ni.interfaces()
        for interface in interfaces:
            if interface != 'lo':
                addresses = ni.ifaddresses(interface)
                if ni.AF_INET in addresses:
                    info["ip"] = addresses[ni.AF_INET][0]['addr']
                if ni.AF_LINK in addresses:
                    info["mac"] = addresses[ni.AF_LINK][0]['addr']
                # Get wireless signal strength if it's a wireless interface
                if "wlan" in interface or "wifi" in interface:
                    try:
                        signal_strength = get_wifi_signal_strength(interface)
                        if signal_strength is not None:
                            info["wifi_rssi"] = signal_strength
                    except:
                        pass
                break
    except:
        info["ip"] = "unknown"
        info["mac"] = "unknown"
    
    # Add network metrics if available
    if network_metrics:
        try:
            net_stats = network_metrics.get_network_stats()
            info.update(net_stats)
        except Exception as e:
            logger.error(f"Error getting network metrics: {e}")
    
    # Add discovered services info
    with discovered_services_lock:
        services_info = {
            "discovered_services": {key: {
                "address": value.get("address", ""),
                "port": value.get("port", 0),
                "properties": value.get("properties", {})
            } for key, value in discovered_services.items()}
        }
    
    info.update(services_info)
    
    return info

def get_cpu_temperature():
    """
    Get CPU temperature on Raspberry Pi
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        return temp
    except:
        return 0

def get_wifi_signal_strength(interface):
    """
    Get WiFi signal strength for a wireless interface
    """
    try:
        # Use iwconfig to get signal strength info
        cmd = ["iwconfig", interface]
        process = subprocess.run(cmd, capture_output=True, text=True)
        output = process.stdout
        
        # Extract signal level from output
        for line in output.split("\n"):
            if "Signal level" in line:
                # Format is typically "Signal level=-XX dBm"
                parts = line.split("Signal level=")
                if len(parts) > 1:
                    signal_part = parts[1].split(" ")[0]
                    try:
                        return int(signal_part)
                    except:
                        pass
    except:
        pass
    
    return None

def send_telemetry():
    """
    Send system telemetry via MQTT
    """
    global mqtt_client, config
    
    if not mqtt_client or not mqtt_client.is_connected():
        return
    
    info = get_system_info()
    topic = f"derbynet/device/{config['DEVICE_NAME']}/telemetry"
    
    try:
        mqtt_client.publish(topic, json.dumps(info), retain=True)
        logger.debug(f"Sent telemetry: {info}")
    except Exception as e:
        logger.error(f"Failed to send telemetry: {e}")

def update_stream_status(status, info=None, error=None):
    """
    Update stream status information
    """
    global stream_status
    
    with status_lock:
        stream_status["status"] = status
        stream_status["last_update"] = datetime.now().isoformat()
        
        if info:
            stream_status["stream_info"] = info
        
        if error:
            stream_status["errors"].append({
                "time": datetime.now().isoformat(),
                "error": str(error)
            })
            # Keep only last 10 errors
            stream_status["errors"] = stream_status["errors"][-10:]
    
    # Send status via MQTT
    if mqtt_client and mqtt_client.is_connected():
        topic = f"derbynet/device/{config['DEVICE_NAME']}/state"
        try:
            mqtt_client.publish(topic, status, retain=True)
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

def clean_old_segments():
    """
    Clean up old HLS segments
    """
    if config["CLEANUP_OLD_SEGMENTS"].lower() != "true":
        return
    
    try:
        now = time.time()
        hls_dir = Path(config["HLS_OUTPUT_DIR"])
        max_age = int(config["MAX_SEGMENT_AGE"])
        
        for file in hls_dir.glob("*.ts"):
            if now - file.stat().st_mtime > max_age:
                logger.debug(f"Removing old segment: {file}")
                file.unlink()
    except Exception as e:
        logger.error(f"Error cleaning old segments: {e}")

def prepare_output_directory():
    """
    Prepare the output directory for HLS files
    """
    os.makedirs(config["HLS_OUTPUT_DIR"], exist_ok=True)
    
    # Create index.html if it doesn't exist
    index_path = os.path.join(config["HLS_OUTPUT_DIR"], "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>HLS Stream</title>
    <style>
        body { margin: 0; background-color: #000; color: #fff; font-family: Arial, sans-serif; }
        .video-container { width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; }
        video { max-width: 100%; max-height: 100%; }
    </style>
</head>
<body>
    <div class="video-container">
        <video id="video" controls autoplay></video>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        const video = document.getElementById('video');
        const videoSrc = 'stream.m3u8';
        
        if (Hls.isSupported()) {
            const hls = new Hls();
            hls.loadSource(videoSrc);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, function() {
                video.play();
            });
        }
        else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = videoSrc;
            video.addEventListener('loadedmetadata', function() {
                video.play();
            });
        }
    </script>
</body>
</html>
""")
    
    # Create status.html for the kiosk display
    status_path = os.path.join(config["HLS_OUTPUT_DIR"], "status.html")
    if not os.path.exists(status_path):
        with open(status_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>HLS Transcoder Status</title>
    <style>
        body { margin: 0; background-color: #222; color: #eee; font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #4CAF50; }
        .container { max-width: 1200px; margin: 0 auto; }
        .status-indicator { display: inline-block; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px; }
        .status-indicator.RUNNING { background-color: #4CAF50; }
        .status-indicator.INITIALIZING { background-color: #2196F3; }
        .status-indicator.ERROR { background-color: #f44336; }
        .status-indicator.STOPPED { background-color: #9E9E9E; }
        .card { background-color: #333; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .status-value { font-weight: bold; color: #4CAF50; }
        .error-list { background-color: #400; padding: 10px; border-radius: 5px; }
        .time { color: #999; font-size: 0.8em; }
        .stream-preview { width: 100%; max-height: 300px; object-fit: cover; background-color: #000; border-radius: 5px; }
        .tab { overflow: hidden; border: 1px solid #444; background-color: #333; border-radius: 5px 5px 0 0; }
        .tab button { background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; color: #ccc; }
        .tab button:hover { background-color: #444; }
        .tab button.active { background-color: #4CAF50; color: white; }
        .tabcontent { display: none; padding: 20px; border: 1px solid #444; border-top: none; border-radius: 0 0 5px 5px; }
        #Status { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>HLS Transcoder Status</h1>
        
        <div class="tab">
            <button class="tablinks active" onclick="openTab(event, 'Status')">Status</button>
            <button class="tablinks" onclick="openTab(event, 'Stream')">Stream</button>
            <button class="tablinks" onclick="openTab(event, 'Replay')">Replay</button>
            <button class="tablinks" onclick="openTab(event, 'Network')">Network</button>
            <button class="tablinks" onclick="openTab(event, 'System')">System</button>
            <button class="tablinks" onclick="openTab(event, 'Logs')">Logs</button>
        </div>
        
        <div id="Status" class="tabcontent">
            <div class="card">
                <h2>Transcoder Status</h2>
                <p>
                    <span class="status-indicator" id="statusDot"></span>
                    <span id="statusText">Loading...</span>
                </p>
                <p>Last Update: <span id="lastUpdate">-</span></p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>Stream Source</h3>
                    <p id="sourceUrl">-</p>
                </div>
                <div class="card">
                    <h3>Output</h3>
                    <p>HLS URL: <span id="hlsUrl">-</span></p>
                    <p>Format: <span id="outputFormat">-</span></p>
                </div>
                <div class="card">
                    <h3>System Info</h3>
                    <p>CPU: <span id="cpuUsage">-</span>%</p>
                    <p>Memory: <span id="memoryUsage">-</span>%</p>
                    <p>Temp: <span id="cpuTemp">-</span>°C</p>
                </div>
                <div class="card">
                    <h3>Device Info</h3>
                    <p>Device ID: <span id="deviceId">-</span></p>
                    <p>Version: <span id="version">-</span></p>
                    <p>Uptime: <span id="uptime">-</span></p>
                </div>
            </div>
            
            <div class="card" id="errorCard" style="display: none;">
                <h3>Recent Errors</h3>
                <div class="error-list" id="errorList"></div>
            </div>
        </div>
        
        <div id="Stream" class="tabcontent">
            <div class="card">
                <h2>Stream Preview</h2>
                <video id="video" controls class="stream-preview"></video>
            </div>
            
            <div class="card">
                <h3>Stream Information</h3>
                <div id="streamInfo">Loading...</div>
            </div>
        </div>
        
        <div id="Replay" class="tabcontent">
            <div class="card">
                <h3>Replay Status</h3>
                <div id="replayStatus">
                    <p>Status: <span id="replayStatusText">-</span></p>
                    <p>Current Race: <span id="currentRace">-</span></p>
                    <p>Recording: <span id="recordingStatus">-</span></p>
                </div>
            </div>
            <div class="card">
                <h3>Replay Configuration</h3>
                <p>Buffer Time: <span id="replayBuffer">-</span> ms</p>
                <p>Playback Rate: <span id="replayRate">-</span>%</p>
                <p>Number of Showings: <span id="replayShowings">-</span></p>
                <p>Video Directory: <span id="replayDir">-</span></p>
            </div>
            <div class="card">
                <h3>Replay Controls</h3>
                <button onclick="triggerReplay()" class="button">Trigger Manual Replay</button>
                <button onclick="cancelReplay()" class="button">Cancel Replay</button>
            </div>
        </div>

        <div id="Network" class="tabcontent">
            <div class="card">
                <h3>Network Status</h3>
                <p>IP Address: <span id="ipAddress">-</span></p>
                <p>MAC Address: <span id="macAddress">-</span></p>
                <p>WiFi Signal: <span id="wifiSignal">-</span> dBm</p>
            </div>

            <div class="card">
                <h3>Discovered Services</h3>
                <div id="discoveredServices">Loading...</div>
            </div>

            <div class="card">
                <h3>Network Metrics</h3>
                <p>Packet Loss: <span id="packetLoss">-</span>%</p>
                <p>Latency: <span id="latency">-</span> ms</p>
                <p>Jitter: <span id="jitter">-</span> ms</p>
            </div>
        </div>
        
        <div id="System" class="tabcontent">
            <div class="grid">
                <div class="card">
                    <h3>Hardware</h3>
                    <p>Hostname: <span id="hostname">-</span></p>
                    <p>CPU Temperature: <span id="cpuTemp2">-</span>°C</p>
                    <p>Memory Usage: <span id="memoryUsage2">-</span>%</p>
                </div>
                <div class="card">
                    <h3>Storage</h3>
                    <p>Disk Usage: <span id="diskUsage">-</span>%</p>
                    <p>Output Directory: <span id="outputDir">-</span></p>
                </div>
                <div class="card">
                    <h3>Configuration</h3>
                    <p>Bitrate: <span id="bitrate">-</span></p>
                    <p>Resolution: <span id="resolution">-</span></p>
                    <p>Preset: <span id="preset">-</span></p>
                </div>
            </div>
        </div>
        
        <div id="Logs" class="tabcontent">
            <div class="card">
                <h3>Recent Log Messages</h3>
                <pre id="logMessages" style="height: 400px; overflow-y: auto; background-color: #222; padding: 10px; border-radius: 5px;">Loading logs...</pre>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        // Tab functionality
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }
        
        // Format time difference
        function formatTimeDiff(isoString) {
            const date = new Date(isoString);
            const now = new Date();
            const diffSeconds = Math.floor((now - date) / 1000);
            
            if (diffSeconds < 60) return `${diffSeconds} seconds ago`;
            if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} minutes ago`;
            if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} hours ago`;
            return `${Math.floor(diffSeconds / 86400)} days ago`;
        }
        
        // Format uptime
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            
            if (days > 0) return `${days}d ${hours}h ${minutes}m`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            return `${minutes}m ${seconds % 60}s`;
        }
        
        // Update the status page with data
        function updateStatus(data) {
            // Status tab
            document.getElementById('statusText').textContent = data.status;
            document.getElementById('statusDot').className = `status-indicator ${data.status}`;
            document.getElementById('lastUpdate').textContent = formatTimeDiff(data.last_update);
            document.getElementById('sourceUrl').textContent = data.config.RTSP_SOURCE;
            document.getElementById('hlsUrl').textContent = `http://${window.location.hostname}:8037/hls/stream.m3u8`;
            document.getElementById('outputFormat').textContent = `HLS (${data.config.RESOLUTION} @ ${data.config.BITRATE})`;
            document.getElementById('cpuUsage').textContent = data.system_info.cpu_usage;
            document.getElementById('memoryUsage').textContent = data.system_info.memory_usage;
            document.getElementById('cpuTemp').textContent = data.system_info.cpu_temp.toFixed(1);
            document.getElementById('deviceId').textContent = data.system_info.hwid;
            document.getElementById('version').textContent = data.system_info.version;
            document.getElementById('uptime').textContent = formatUptime(data.system_info.uptime);
            
            // System tab
            document.getElementById('hostname').textContent = data.system_info.hostname;
            document.getElementById('ipAddress').textContent = data.system_info.ip;
            document.getElementById('macAddress').textContent = data.system_info.mac;
            document.getElementById('diskUsage').textContent = data.system_info.disk;
            document.getElementById('outputDir').textContent = data.config.HLS_OUTPUT_DIR;
            document.getElementById('bitrate').textContent = data.config.BITRATE;
            document.getElementById('resolution').textContent = data.config.RESOLUTION;
            document.getElementById('preset').textContent = data.config.FFMPEG_PRESET;
            document.getElementById('cpuTemp2').textContent = data.system_info.cpu_temp.toFixed(1);
            document.getElementById('memoryUsage2').textContent = data.system_info.memory_usage;
            
            // Network tab
            if (data.system_info.wifi_rssi) {
                document.getElementById('wifiSignal').textContent = data.system_info.wifi_rssi;
            }
            
            if (data.system_info.packet_loss) {
                document.getElementById('packetLoss').textContent = data.system_info.packet_loss.toFixed(2);
            }
            
            if (data.system_info.latency) {
                document.getElementById('latency').textContent = data.system_info.latency.toFixed(2);
            }
            
            if (data.system_info.jitter) {
                document.getElementById('jitter').textContent = data.system_info.jitter.toFixed(2);
            }
            
            // Discovered services
            if (data.system_info.discovered_services) {
                const servicesDiv = document.getElementById('discoveredServices');
                let servicesHtml = '<ul>';
                
                for (const [name, service] of Object.entries(data.system_info.discovered_services)) {
                    servicesHtml += `<li><strong>${name}</strong>: ${service.address}:${service.port}</li>`;
                }
                
                servicesHtml += '</ul>';
                
                if (Object.keys(data.system_info.discovered_services).length === 0) {
                    servicesHtml = '<p>No services discovered</p>';
                }
                
                servicesDiv.innerHTML = servicesHtml;
            }
            
            // Replay tab
            if (data.replay_state) {
                document.getElementById('replayStatusText').textContent = data.replay_state.status || "Idle";
                
                const raceInfo = data.replay_state.class ? 
                    `Class ${data.replay_state.class}, Round ${data.replay_state.round}, Heat ${data.replay_state.heat}` : 
                    "No active race";
                document.getElementById('currentRace').textContent = raceInfo;
                
                document.getElementById('recordingStatus').textContent = data.replay_state.recording ? "Recording" : "Not recording";
                document.getElementById('replayBuffer').textContent = data.config.REPLAY_BUFFER_TIME;
                document.getElementById('replayRate').textContent = data.config.REPLAY_PLAYBACK_RATE;
                document.getElementById('replayShowings').textContent = data.config.REPLAY_NUM_SHOWINGS;
                document.getElementById('replayDir').textContent = data.config.REPLAY_VIDEO_DIR;
            }
            
            // Stream info
            const streamInfoEl = document.getElementById('streamInfo');
            if (Object.keys(data.stream_info).length > 0) {
                let infoHtml = '<table style="width:100%">';
                for (const [key, value] of Object.entries(data.stream_info)) {
                    infoHtml += `<tr><td style="font-weight:bold;padding:5px">${key}</td><td>${value}</td></tr>`;
                }
                infoHtml += '</table>';
                streamInfoEl.innerHTML = infoHtml;
            } else {
                streamInfoEl.textContent = 'No stream information available';
            }
            
            // Errors
            const errorCard = document.getElementById('errorCard');
            const errorList = document.getElementById('errorList');
            if (data.errors && data.errors.length > 0) {
                errorCard.style.display = 'block';
                errorList.innerHTML = '';
                data.errors.forEach(error => {
                    const errorTime = new Date(error.time).toLocaleTimeString();
                    errorList.innerHTML += `<p><span class="time">[${errorTime}]</span> ${error.error}</p>`;
                });
            } else {
                errorCard.style.display = 'none';
            }
            
            // Update HLS player if status is RUNNING
            if (data.status === 'RUNNING') {
                const video = document.getElementById('video');
                const videoSrc = `http://${window.location.hostname}:8037/hls/stream.m3u8`;
                
                if (Hls.isSupported()) {
                    if (!window.hls) {
                        window.hls = new Hls();
                        window.hls.loadSource(videoSrc);
                        window.hls.attachMedia(video);
                    }
                }
                else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                    video.src = videoSrc;
                }
            }
        }
        
        // Replay control functions
        function triggerReplay() {
            fetch('/api/replay/trigger', { method: 'POST' })
                .then(response => {
                    if (response.ok) {
                        alert('Manual replay triggered');
                    } else {
                        alert('Failed to trigger replay');
                    }
                })
                .catch(error => {
                    console.error('Error triggering replay:', error);
                    alert('Error triggering replay');
                });
        }
        
        function cancelReplay() {
            fetch('/api/replay/cancel', { method: 'POST' })
                .then(response => {
                    if (response.ok) {
                        alert('Replay canceled');
                    } else {
                        alert('Failed to cancel replay');
                    }
                })
                .catch(error => {
                    console.error('Error canceling replay:', error);
                    alert('Error canceling replay');
                });
        }
        
        // Fetch logs
        function fetchLogs() {
            fetch('/api/logs')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('logMessages').textContent = data;
                })
                .catch(error => {
                    document.getElementById('logMessages').textContent = 'Error loading logs: ' + error;
                });
        }
        
        // Fetch status periodically
        function fetchStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateStatus(data);
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                })
                .finally(() => {
                    setTimeout(fetchStatus, 2000);
                });
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            fetchStatus();
            fetchLogs();
            // Refresh logs every 10 seconds
            setInterval(fetchLogs, 10000);
        });
    </script>
</body>
</html>
""")
    
    logger.info(f"Output directory prepared: {config['HLS_OUTPUT_DIR']}")

def ffmpeg_transcode():
    """
    Run FFmpeg to transcode RTSP to HLS
    """
    global current_process, config
    
    # Prepare output directory
    prepare_output_directory()
    
    # Build FFmpeg command
    output_path = os.path.join(config["HLS_OUTPUT_DIR"], "stream.m3u8")
    segment_path = os.path.join(config["HLS_OUTPUT_DIR"], "stream_%03d.ts")
    
    # Check if we should use a discovered RTSP source instead of configured one
    rtsp_source = config["RTSP_SOURCE"]
    if config["AUTO_DISCOVER_RTSP"].lower() == "true":
        with discovered_services_lock:
            # Look for services with RTSP in name or properties
            for service_name, service_info in discovered_services.items():
                if "rtsp" in service_name.lower() or service_info.get("properties", {}).get("type", "").lower() == "rtsp":
                    new_source = f"rtsp://{service_info['address']}:{service_info['port']}/stream"
                    logger.info(f"Auto-discovered RTSP source: {new_source}")
                    rtsp_source = new_source
                    break
    
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output files
        "-rtsp_transport", "tcp",  # Use TCP for RTSP
        "-i", rtsp_source,  # Input stream
        "-c:v", config["CODEC"],  # Video codec
        "-b:v", config["BITRATE"],  # Video bitrate
        "-maxrate", config["BITRATE"],  # Maximum bitrate
        "-bufsize", "5M",  # Buffer size
        "-s", config["RESOLUTION"],  # Resolution
        "-preset", config["FFMPEG_PRESET"],  # Encoding preset
        "-g", "30",  # GOP size (keyframe interval)
        "-sc_threshold", "0",  # Scene change threshold
        "-hls_time", config["SEGMENT_DURATION"],  # Segment duration
        "-hls_list_size", config["HLS_LIST_SIZE"],  # Number of segments in playlist
        "-hls_flags", "delete_segments",  # Delete old segments
        "-hls_delete_threshold", "1",  # Delete threshold
        "-hls_segment_type", "mpegts",  # Segment type
        "-hls_segment_filename", segment_path,  # Segment filename pattern
        "-f", "hls",  # Format
        output_path  # Output file
    ]
    
    logger.info(f"Starting FFmpeg with command: {' '.join(cmd)}")
    
    try:
        # Start FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        current_process = process
        update_stream_status("RUNNING")
        
        # Monitor the process
        while process.poll() is None and running:
            # Read stderr for FFmpeg output
            line = process.stderr.readline()
            if line:
                line = line.strip()
                logger.debug(f"FFmpeg: {line}")
                
                # Parse stream information from FFmpeg output
                if "Stream #" in line and "Video:" in line:
                    try:
                        update_stream_status("RUNNING", {"video_info": line})
                    except:
                        pass
            
            # Clean old segments periodically
            clean_old_segments()
            
            # Check if process has terminated
            if process.poll() is not None:
                break
            
            time.sleep(0.1)
        
        # Process has terminated
        exit_code = process.poll()
        if exit_code is not None and exit_code != 0:
            stderr = process.stderr.read()
            logger.error(f"FFmpeg exited with code {exit_code}: {stderr}")
            update_stream_status("ERROR", error=f"FFmpeg exited with code {exit_code}")
        else:
            logger.info("FFmpeg process stopped")
            update_stream_status("STOPPED")
    
    except Exception as e:
        logger.error(f"Error running FFmpeg: {e}")
        update_stream_status("ERROR", error=str(e))
    
    current_process = None

def get_process_info():
    """
    Get information about the FFmpeg process
    """
    if current_process is None:
        return {}
    
    try:
        # Get process information
        proc = psutil.Process(current_process.pid)
        return {
            "pid": proc.pid,
            "status": proc.status(),
            "cpu_percent": proc.cpu_percent(),
            "memory_percent": proc.memory_percent(),
            "create_time": datetime.fromtimestamp(proc.create_time()).isoformat()
        }
    except:
        return {}

def start_transcoding():
    """
    Start the transcoding process
    """
    global running
    
    while running:
        try:
            ffmpeg_transcode()
            
            # If we got here, the process exited
            logger.warning("Transcoding process exited, restarting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in transcoding thread: {e}")
            time.sleep(5)

def setup_mqtt():
    """
    Set up MQTT client for telemetry and control
    """
    global mqtt_client, config
    
    client_id = f"{config['DEVICE_NAME']}_{config['DERBY_ID']}"
    mqtt_client = MQTTClient(
        client_id=client_id,
        broker_host=config["MQTT_BROKER"],
        broker_port=int(config["MQTT_PORT"]),
        username=config["MQTT_USERNAME"] if config["MQTT_USERNAME"] else None,
        password=config["MQTT_PASSWORD"] if config["MQTT_PASSWORD"] else None,
        logger=logger
    )
    
    # Set up message handler
    mqtt_client.set_message_callback(mqtt_message_handler)
    
    # Define topics to subscribe to
    topics = [
        f"derbynet/device/{config['DEVICE_NAME']}/command",
        f"derbynet/device/{config['DERBY_ID']}/command",  # Hardware ID specific commands
        f"derbynet/device/{config['DEVICE_NAME']}/update",  # Update channel
        f"derbynet/device/{config['DERBY_ID']}/update",  # Hardware ID specific update channel
        "derbynet/race/state",
        "derbynet/command/replay",
        config["REPLAY_TOPIC"]  # Added for replay functionality
    ]
    
    # Try to connect
    if mqtt_client.connect():
        logger.info(f"Connected to MQTT broker at {config['MQTT_BROKER']}:{config['MQTT_PORT']}")
        
        # Subscribe to topics
        for topic in topics:
            if mqtt_client.subscribe(topic):
                logger.info(f"Subscribed to topic: {topic}")
            else:
                logger.error(f"Failed to subscribe to topic: {topic}")
        
        # Publish online status
        mqtt_client.publish(
            f"derbynet/device/{config['DEVICE_NAME']}/status",
            "online",
            retain=True
        )
        
        # Publish device info with version
        device_info = {
            "type": "hlstranscoder",
            "version": VERSION,
            "hwid": config["DERBY_ID"],
            "name": config["DEVICE_NAME"]
        }
        mqtt_client.publish(
            f"derbynet/device/{config['DEVICE_NAME']}/info",
            json.dumps(device_info),
            retain=True
        )
        
        # Send initial telemetry
        send_telemetry()
        
        # Publish replay handler status
        mqtt_client.publish(
            config["STATUS_TOPIC"],
            json.dumps({
                "status": "online",
                "version": VERSION
            }),
            retain=True
        )
    else:
        logger.error(f"Failed to connect to MQTT broker at {config['MQTT_BROKER']}:{config['MQTT_PORT']}")

def mqtt_message_handler(client, userdata, message):
    """
    Handle MQTT messages
    """
    try:
        topic = message.topic
        payload = message.payload.decode()
        logger.debug(f"Received MQTT message on {topic}: {payload}")
        
        # Handle device commands
        if topic.endswith("/command"):
            handle_command(payload)
        
        # Handle update commands
        elif topic.endswith("/update"):
            handle_update_command(payload)
        
        # Handle race state
        elif topic == "derbynet/race/state":
            handle_race_state(payload)
        
        # Handle replay command
        elif topic == "derbynet/command/replay" or topic == config["REPLAY_TOPIC"]:
            handle_replay_command(payload)
    
    except Exception as e:
        logger.error(f"Error handling MQTT message: {e}")

def handle_command(command):
    """
    Handle device commands from MQTT
    """
    global current_process
    
    if command == "restart":
        logger.info("Received command to restart transcoding")
        if current_process:
            try:
                current_process.terminate()
            except:
                pass
    
    elif command == "stop":
        logger.info("Received command to stop transcoding")
        if current_process:
            try:
                current_process.terminate()
                update_stream_status("STOPPED")
            except:
                pass
    
    elif command == "update":
        # Shortcut to trigger update
        handle_update_command("update")
    
    elif command.startswith("set:"):
        # Handle setting configuration
        try:
            _, param, value = command.split(":", 2)
            if param in config:
                config[param] = value
                logger.info(f"Set config {param} to {value}")
                
                # Restart transcoding if certain parameters change
                if param in ["RTSP_SOURCE", "RESOLUTION", "BITRATE", "CODEC", "FFMPEG_PRESET"]:
                    logger.info(f"Parameter {param} changed, restarting transcoding")
                    if current_process:
                        try:
                            current_process.terminate()
                        except:
                            pass
            else:
                logger.warning(f"Unknown config parameter: {param}")
        except:
            logger.error(f"Invalid set command: {command}")

def handle_update_command(payload):
    """
    Handle update commands from MQTT
    """
    if payload.lower() == "update":
        logger.info("Received update command via MQTT")
        update_stream_status("UPDATING")
        
        # Publish updating status
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(
                f"derbynet/device/{config['DEVICE_NAME']}/status",
                "updating",
                retain=True
            )
        
        # Run the update process in a separate thread to avoid blocking
        threading.Thread(target=perform_update, daemon=True).start()
    else:
        logger.warning(f"Unknown update command: {payload}")

def perform_update():
    """
    Perform the update process
    """
    try:
        logger.info("Starting update process")
        
        # Build the command to execute the sync script
        cmd = ["/opt/hlstranscoder/sync.sh"]
        
        # Add server address if specified in config
        if "UPDATE_SERVER" in config and config["UPDATE_SERVER"]:
            cmd.append(config["UPDATE_SERVER"])
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Update successful: {result.stdout}")
            # The sync.sh script will restart the service, so this process will end
        else:
            logger.error(f"Update failed: {result.stderr}")
            
            # Update status back to previous state and notify
            update_stream_status(stream_status["status"], error=f"Update failed: {result.stderr}")
            
            # Publish back online status
            if mqtt_client and mqtt_client.is_connected():
                mqtt_client.publish(
                    f"derbynet/device/{config['DEVICE_NAME']}/status",
                    "online",
                    retain=True
                )
    except Exception as e:
        logger.error(f"Error during update: {e}")
        
        # Update status back to previous state and notify
        update_stream_status(stream_status["status"], error=f"Update error: {str(e)}")
        
        # Publish back online status
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(
                f"derbynet/device/{config['DEVICE_NAME']}/status",
                "online",
                retain=True
            )

def handle_race_state(state):
    """
    Handle race state changes from MQTT
    """
    logger.info(f"Race state changed to {state}")
    # Could be used to start/stop recording based on race state

# Zeroconf Functions
def setup_zeroconf():
    """
    Set up zeroconf for service discovery and advertisement
    """
    global zeroconf, zeroconf_service
    
    if not ZEROCONF_AVAILABLE or config["ENABLE_ZEROCONF"].lower() != "true":
        logger.info("Zeroconf disabled or not available")
        return
    
    try:
        # Create zeroconf instance
        zeroconf = Zeroconf()
        
        # Get host info
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Register this service
        service_port = int(config["API_PORT"])
        service_name = f"{config['DEVICE_NAME']}_{config['DERBY_ID']}.{config['SERVICE_TYPE']}"
        service_info = ServiceInfo(
            type_=config['SERVICE_TYPE'],
            name=service_name,
            addresses=[socket.inet_aton(ip_address)],
            port=service_port,
            properties={
                'version': VERSION,
                'device_type': 'hlstranscoder',
                'hwid': config['DERBY_ID']
            }
        )
        
        zeroconf.register_service(service_info)
        zeroconf_service = service_info
        logger.info(f"Registered zeroconf service: {service_name} at {ip_address}:{service_port}")
        
        # Start service discovery
        start_service_discovery()
    except Exception as e:
        logger.error(f"Error setting up zeroconf: {e}")

def start_service_discovery():
    """
    Start discovering other services on the network
    """
    if not zeroconf:
        return
    
    try:
        # Start service browsers for different service types
        ServiceBrowser(zeroconf, config['RTSP_FINDER_SERVICE'], ServiceListener())
        ServiceBrowser(zeroconf, config['FINISHTIMER_SERVICE'], ServiceListener())
        ServiceBrowser(zeroconf, config['SERVICE_TYPE'], ServiceListener())
        
        logger.info("Started zeroconf service discovery")
    except Exception as e:
        logger.error(f"Error starting service discovery: {e}")

class ServiceListener:
    """
    Listener for zeroconf service discovery
    """
    def add_service(self, zc, type_, name):
        """
        Called when a service is discovered
        """
        try:
            info = zc.get_service_info(type_, name)
            if info:
                # Extract service info
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                address = addresses[0] if addresses else "unknown"
                
                # Convert properties from bytes to strings
                properties = {}
                for k, v in info.properties.items():
                    try:
                        key = k.decode('utf-8')
                        value = v.decode('utf-8')
                        properties[key] = value
                    except:
                        continue
                
                # Store the service
                with discovered_services_lock:
                    discovered_services[name] = {
                        "address": address,
                        "port": info.port,
                        "properties": properties,
                        "discovered_at": datetime.now().isoformat()
                    }
                
                logger.info(f"Discovered service: {name} at {address}:{info.port}")
                
                # If this is an RTSP source and we should use auto-discovered sources,
                # possibly restart the transcoder
                if (
                    config["AUTO_DISCOVER_RTSP"].lower() == "true" and 
                    ("rtsp" in name.lower() or properties.get("type", "").lower() == "rtsp") and
                    current_process
                ):
                    logger.info(f"New RTSP source discovered, restarting transcoder")
                    try:
                        current_process.terminate()
                    except:
                        pass
                
        except Exception as e:
            logger.error(f"Error processing discovered service: {e}")

    def remove_service(self, zc, type_, name):
        """
        Called when a service disappears
        """
        with discovered_services_lock:
            if name in discovered_services:
                logger.info(f"Service removed: {name}")
                del discovered_services[name]

    def update_service(self, zc, type_, name):
        """
        Called when a service is updated
        """
        self.add_service(zc, type_, name)

def cleanup_zeroconf():
    """
    Clean up zeroconf resources
    """
    if zeroconf:
        try:
            if zeroconf_service:
                zeroconf.unregister_service(zeroconf_service)
            zeroconf.close()
        except:
            pass

# Replay handling functions

def handle_replay_command(payload):
    """
    Handle replay commands from MQTT
    """
    try:
        # If payload is a JSON string, parse it
        if payload.startswith('{'):
            data = json.loads(payload)
            command_type = data.get('command')
            
            if command_type == 'START':
                # Begin recording a new heat
                start_recording(data)
            elif command_type == 'REPLAY':
                # Trigger immediate replay
                trigger_replay()
            elif command_type == 'RACE_STARTS':
                # Set up delayed replay after race
                race_starts(data)
            elif command_type == 'CANCEL':
                # Cancel pending replay
                cancel_replay()
            else:
                logger.warning(f"Unknown replay command type: {command_type}")
        else:
            # Handle simple string commands (for compatibility)
            if payload.lower() == 'replay':
                trigger_replay()
            elif payload.lower() == 'cancel':
                cancel_replay()
            else:
                logger.warning(f"Unknown replay command: {payload}")
    except json.JSONDecodeError:
        logger.error(f"Failed to decode replay message: {payload}")
    except Exception as e:
        logger.error(f"Error processing replay message: {e}")

def start_recording(command):
    """
    Start recording a new heat
    """
    global replay_state
    
    with replay_lock:
        # Stop any existing recording
        stop_recording()
        
        # Update race information
        replay_state = {
            'class': command.get('class', 'Unknown'),
            'round': command.get('round', 0),
            'heat': command.get('heat', 0),
            'timestamp': int(time.time()),
            'recording': True,
            'replay_pending': False,
            'recording_process': None,
            'replay_process': None
        }
        
        logger.info(f"Starting recording for Class {replay_state['class']}, "
                    f"Round {replay_state['round']}, Heat {replay_state['heat']}")
        
        # Start ffmpeg process for recording
        try:
            output_file = get_output_filename()
            
            # Discover stream URL for derby host if available
            host = config["DERBYNET_HOSTNAME"]
            with discovered_services_lock:
                for service_name, service_info in discovered_services.items():
                    # Look for host in service name
                    if host.lower() in service_name.lower():
                        host = service_info["address"]
                        logger.info(f"Using discovered host for recording: {host}")
                        break
                        
            stream_url = f"http://{host}:8037/hls/stream.m3u8"
            
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-t', '30',  # Maximum recording length (30 seconds)
                '-y',        # Overwrite output file
                output_file
            ]
            
            replay_state['recording_process'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Recording started to {output_file}")
            
            # Send status update
            if mqtt_client and mqtt_client.is_connected():
                mqtt_client.publish(
                    config["STATUS_TOPIC"],
                    json.dumps({
                        "status": "recording",
                        "race": {
                            'class': replay_state['class'],
                            'round': replay_state['round'],
                            'heat': replay_state['heat']
                        }
                    }),
                    qos=1
                )
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            replay_state['recording'] = False

def stop_recording():
    """
    Stop the current recording process
    """
    global replay_state
    
    if replay_state.get('recording_process'):
        try:
            replay_state['recording_process'].terminate()
            replay_state['recording_process'].wait(timeout=5)
            logger.info("Recording stopped")
        except Exception as e:
            logger.error(f"Error stopping recording process: {e}")
            try:
                replay_state['recording_process'].kill()
            except:
                pass
        finally:
            replay_state['recording_process'] = None
            
    replay_state['recording'] = False

def trigger_replay():
    """
    Trigger immediate replay of the most recent recording
    """
    global replay_state
    
    with replay_lock:
        # Stop recording if it's still going
        if replay_state.get('recording'):
            stop_recording()
            
        # Check if we have a valid recording
        output_file = get_output_filename()
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            logger.warning(f"No valid recording found at {output_file}")
            return
            
        logger.info(f"Triggering replay of {output_file}")
        
        # Send status update
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(
                config["STATUS_TOPIC"],
                json.dumps({
                    "status": "replaying",
                    "race": {
                        'class': replay_state.get('class'),
                        'round': replay_state.get('round'),
                        'heat': replay_state.get('heat')
                    }
                }),
                qos=1
            )
        
        # Calculate replay parameters
        replay_speed = int(config["REPLAY_PLAYBACK_RATE"]) / 100.0
        
        # Start ffplay process for replay
        try:
            cmd = [
                'ffplay',
                '-i', output_file,
                '-vf', f'setpts={1/replay_speed}*PTS',
                '-af', f'atempo={replay_speed}',
                '-loop', config["REPLAY_NUM_SHOWINGS"],
                '-autoexit',
                '-x', '640',
                '-y', '480',
                '-window_title', f"Replay: {replay_state.get('class', 'Unknown')} Round {replay_state.get('round', '?')} Heat {replay_state.get('heat', '?')}"
            ]
            
            replay_state['replay_process'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Start a thread to monitor the replay process
            threading.Thread(target=monitor_replay, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start replay: {e}")

def monitor_replay():
    """
    Monitor the replay process until it completes
    """
    global replay_state
    
    if not replay_state.get('replay_process'):
        return
        
    try:
        replay_state['replay_process'].wait()
        logger.info("Replay complete")
        
        # Send status update
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish(
                config["STATUS_TOPIC"],
                json.dumps({
                    "status": "idle",
                    "race": {
                        'class': replay_state.get('class'),
                        'round': replay_state.get('round'),
                        'heat': replay_state.get('heat')
                    }
                }),
                qos=1
            )
        
        with replay_lock:
            replay_state['replay_process'] = None
            replay_state['replay_pending'] = False
        
    except Exception as e:
        logger.error(f"Error monitoring replay process: {e}")

def race_starts(command):
    """
    Set a pending replay for when the race finishes
    """
    global replay_state
    
    replay_state['replay_pending'] = True
    logger.info("Race started, replay pending")
    
    # Calculate the delay before starting the replay
    delay = command.get('delay', 1000)  # Default 1 second delay
    
    # Schedule the delayed replay
    threading.Timer(delay / 1000.0, trigger_replay).start()

def cancel_replay():
    """
    Cancel any pending replay
    """
    global replay_state
    
    replay_state['replay_pending'] = False
    
    # Kill any existing replay process
    if replay_state.get('replay_process'):
        try:
            replay_state['replay_process'].terminate()
            replay_state['replay_process'].wait(timeout=5)
        except:
            try:
                replay_state['replay_process'].kill()
            except:
                pass
                
        replay_state['replay_process'] = None
        
    logger.info("Replay canceled")
    
    # Send status update
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.publish(
            config["STATUS_TOPIC"],
            json.dumps({
                "status": "idle",
                "race": {
                    'class': replay_state.get('class'),
                    'round': replay_state.get('round'),
                    'heat': replay_state.get('heat')
                }
            }),
            qos=1
        )

def get_output_filename():
    """
    Generate output filename based on current race information
    """
    # Format: Class_Round_Heat.mkv (e.g., ClassA_Round1_Heat01.mkv)
    class_name = replay_state.get('class', 'Unknown').replace(' ', '')
    round_num = replay_state.get('round', 0)
    heat_num = replay_state.get('heat', 0)
    
    filename = f"{class_name}_Round{round_num}_Heat{heat_num:02d}.mkv"
    return os.path.join(config["REPLAY_VIDEO_DIR"], filename)

# Enhanced API handler with replay endpoints
class APIHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler for transcoder API
    """
    def do_GET(self):
        """
        Handle GET requests
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Status API
        if path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Prepare response data
            with status_lock:
                status_data = {
                    "status": stream_status["status"],
                    "last_update": stream_status["last_update"],
                    "stream_info": stream_status["stream_info"],
                    "errors": stream_status["errors"],
                    "process_info": get_process_info(),
                    "system_info": get_system_info(),
                    "config": config,
                    "replay_state": replay_state
                }
            
            self.wfile.write(json.dumps(status_data).encode())
        
        # Logs API
        elif path == "/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Get recent logs
            log_file = "/var/log/hlstranscoder/hlstranscoder.log"
            if os.path.exists(log_file):
                try:
                    # Get last 50 lines
                    process = subprocess.run(
                        ["tail", "-n", "50", log_file],
                        capture_output=True,
                        text=True
                    )
                    self.wfile.write(process.stdout.encode())
                except:
                    self.wfile.write(b"Error reading log file")
            else:
                self.wfile.write(b"Log file not found")
        
        # Service discovery API
        elif path == "/services":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            with discovered_services_lock:
                services_data = {
                    "services": discovered_services,
                    "count": len(discovered_services)
                }
            
            self.wfile.write(json.dumps(services_data).encode())
        
        # Health check
        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        
        # Not found
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def do_POST(self):
        """
        Handle POST requests for replay controls
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Trigger replay
        if path == "/replay/trigger":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            trigger_replay()
            self.wfile.write(json.dumps({"status": "Replay triggered"}).encode())
        
        # Cancel replay
        elif path == "/replay/cancel":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            cancel_replay()
            self.wfile.write(json.dumps({"status": "Replay canceled"}).encode())
        
        # Invalid endpoint
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
    
    def log_message(self, format, *args):
        """
        Override log message to use our logger
        """
        logger.debug(f"API: {format % args}")

def start_api_server():
    """
    Start the HTTP API server
    """
    if config["ENABLE_API"].lower() != "true":
        logger.info("API server disabled in configuration")
        return
    
    try:
        port = int(config["API_PORT"])
        server = socketserver.TCPServer(("", port), APIHandler)
        logger.info(f"Started API server on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Error starting API server: {e}")

def signal_handler(sig, frame):
    """
    Handle signals for graceful shutdown
    """
    global running, mqtt_client, current_process
    
    logger.info("Shutting down...")
    running = False
    
    # Stop FFmpeg process
    if current_process:
        logger.info("Terminating FFmpeg process...")
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except:
            logger.warning("Failed to terminate FFmpeg gracefully, killing...")
            try:
                current_process.kill()
            except:
                pass
    
    # Stop any recording/replay processes
    stop_recording()
    cancel_replay()
    
    # Clean up zeroconf
    cleanup_zeroconf()
    
    # Disconnect from MQTT
    if mqtt_client:
        logger.info("Disconnecting from MQTT...")
        try:
            # Publish offline status
            mqtt_client.publish(
                f"derbynet/device/{config['DEVICE_NAME']}/status",
                "offline",
                retain=True
            )
            
            # Publish replay handler offline status
            mqtt_client.publish(
                config["STATUS_TOPIC"],
                json.dumps({"status": "offline"}),
                retain=True
            )
            
            mqtt_client.disconnect()
        except:
            pass
    
    logger.info("Shutdown complete")
    sys.exit(0)

def main():
    """
    Main entry point
    """
    global config, network_metrics
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="HLS Transcoder for DerbyNet Soapbox Derby")
    parser.add_argument("--config", type=str, default="/etc/hlstranscoder/config.env",
                        help="Path to configuration file")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Set up logging
    log_level = "DEBUG" if args.debug else config["LOG_LEVEL"]
    logger = setup_logger(log_level)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize network metrics if enabled
    if config["ENABLE_NETWORK_METRICS"].lower() == "true":
        try:
            network_metrics = NetworkMetrics(logger=logger)
            logger.info("Network metrics monitoring initialized")
        except Exception as e:
            logger.error(f"Failed to initialize network metrics: {e}")
    
    # Set up zeroconf
    setup_zeroconf()
    
    # Start MQTT client
    setup_mqtt()
    
    # Start telemetry thread
    telemetry_thread = threading.Thread(target=telemetry_loop)
    telemetry_thread.daemon = True
    telemetry_thread.start()
    
    # Start API server thread
    api_thread = threading.Thread(target=start_api_server)
    api_thread.daemon = True
    api_thread.start()
    
    # Start transcoding in the main thread
    start_transcoding()

def telemetry_loop():
    """
    Loop to send telemetry periodically
    """
    while running:
        send_telemetry()
        time.sleep(10)  # Send telemetry every 10 seconds

if __name__ == "__main__":
    main()