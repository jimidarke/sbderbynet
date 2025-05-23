#!/usr/bin/env python3
"""
HLS Transcoder for DerbyNet Soapbox Derby System

This component transcodes video streams from RTSP to HLS format, providing
adaptive streaming capabilities for race viewing and replay. It also monitors
stream health and provides telemetry via MQTT.

Version History:
- 0.5.0: Initial version with RTSP to HLS transcoding, MQTT telemetry, and web status API

"""

VERSION = "0.5.0"

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
except ImportError:
    # For development, try relative import
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from derbylogger import DerbyLogger
        from derbynet import MQTTClient
    except ImportError:
        print("ERROR: Could not import DerbyNet common libraries")
        print("Please ensure derbylogger.py and derbynet.py are available")
        sys.exit(1)

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
        "ARCHIVE_RETENTION_DAYS": "7"
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
            hostname = socket.gethostname()
            config["DERBY_ID"] = hostname
            print(f"WARNING: DERBY_ID not set, using hostname: {hostname}")
    
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
                break
    except:
        info["ip"] = "unknown"
        info["mac"] = "unknown"
    
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
        
        <div id="System" class="tabcontent">
            <div class="grid">
                <div class="card">
                    <h3>Network</h3>
                    <p>IP: <span id="ipAddress">-</span></p>
                    <p>MAC: <span id="macAddress">-</span></p>
                    <p>Hostname: <span id="hostname">-</span></p>
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
            document.getElementById('ipAddress').textContent = data.system_info.ip;
            document.getElementById('macAddress').textContent = data.system_info.mac;
            document.getElementById('hostname').textContent = data.system_info.hostname;
            document.getElementById('diskUsage').textContent = data.system_info.disk;
            document.getElementById('outputDir').textContent = data.config.HLS_OUTPUT_DIR;
            document.getElementById('bitrate').textContent = data.config.BITRATE;
            document.getElementById('resolution').textContent = data.config.RESOLUTION;
            document.getElementById('preset').textContent = data.config.FFMPEG_PRESET;
            
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
    
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output files
        "-rtsp_transport", "tcp",  # Use TCP for RTSP
        "-i", config["RTSP_SOURCE"],  # Input stream
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
        "derbynet/command/replay"
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
        elif topic == "derbynet/command/replay":
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

def handle_replay_command(payload):
    """
    Handle replay commands from MQTT
    """
    try:
        data = json.loads(payload)
        logger.info(f"Received replay command: {data}")
        # Could be used to create and save replay clips
    except:
        logger.error(f"Invalid replay command: {payload}")

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
                    "config": config
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
            mqtt_client.disconnect()
        except:
            pass
    
    logger.info("Shutdown complete")
    sys.exit(0)

def main():
    """
    Main entry point
    """
    global config
    
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