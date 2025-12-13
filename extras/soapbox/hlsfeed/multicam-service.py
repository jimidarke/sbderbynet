#!/usr/bin/env python3
"""
DerbyNet Multi-Camera HLS Feed Service

This service provides multi-camera HLS streaming support for the DerbyNet system.
It extends the existing single-camera architecture to support multiple camera sources
including RTSP (POE cameras) and USB webcams, with optimized FFmpeg transcoding
profiles for 1080p with automatic fallback capabilities.

Features:
- Multiple camera source support (RTSP, USB)
- Quality profiles (1080p, 720p, 480p) with automatic fallback
- Hardware acceleration support
- Real-time stream health monitoring
- MQTT integration for status reporting
- Automatic stream recovery and restart
- Resource usage monitoring and optimization

Version History:
- 0.8.0 - Dec 12, 2025 - Standardized version across all soapbox components
- 0.5.0 - May 30, 2025 - Initial multi-camera implementation
"""

# Version information
VERSION = "0.8.0"

import os
import sys
import json
import time
import logging
import argparse
import threading
import subprocess
import signal
import psutil
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil

# Configure logging
def setup_logging(log_dir: str = "/var/log/hlsfeed") -> logging.Logger:
    """Set up structured logging for the service"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatter for structured logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(f"{log_dir}/multicam-service.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger
    logger = logging.getLogger("MultiCamService")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()
logger.info(f"Starting DerbyNet Multi-Camera HLS Service v{VERSION}")

class CameraSource:
    """Represents a single camera source configuration"""
    
    def __init__(self, camera_id: str, config: Dict):
        self.id = camera_id
        self.enabled = config.get('enabled', False)
        self.type = config.get('type', 'RTSP')
        self.source = config.get('source', '')
        self.name = config.get('name', f'Camera {camera_id}')
        self.position = config.get('position', 'unknown')
        self.primary = config.get('primary', False)
        
        # Stream health tracking
        self.process: Optional[subprocess.Popen] = None
        self.last_restart = datetime.now()
        self.restart_count = 0
        self.health_status = "unknown"
        self.lock = threading.Lock()
        
    def get_output_path(self, base_dir: str) -> str:
        """Get the HLS output path for this camera"""
        return os.path.join(base_dir, f"camera_{self.id}")
        
    def get_stream_url(self, hostname: str, port: int) -> str:
        """Get the public stream URL for this camera"""
        return f"http://{hostname}:{port}/hls/camera_{self.id}/stream.m3u8"
        
    def is_healthy(self) -> bool:
        """Check if the camera stream is healthy"""
        with self.lock:
            if not self.process:
                return False
            return self.process.poll() is None
            
    def __repr__(self):
        return f"CameraSource(id={self.id}, name={self.name}, type={self.type}, enabled={self.enabled})"

class FFmpegProfiler:
    """Manages FFmpeg encoding profiles and optimization"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.current_profile = config.get('VIDEO_QUALITY_PROFILE', 'HIGH_QUALITY')
        
    def get_video_filters(self, camera: CameraSource) -> List[str]:
        """Generate video filters for the camera stream"""
        filters = []
        
        # Scale filter based on quality profile
        resolution = self.config.get(f"{self.current_profile}_RESOLUTION", "1920x1080")
        filters.append(f"scale={resolution}")
        
        # Add deinterlacing if needed
        if camera.type == "USB":
            filters.append("yadif=0:-1:0")
            
        return filters
        
    def get_encoding_params(self) -> Dict[str, str]:
        """Get encoding parameters for current quality profile"""
        profile = self.current_profile
        return {
            'codec': 'libx264',
            'preset': self.config.get(f"{profile}_PRESET", "medium"),
            'bitrate': self.config.get(f"{profile}_BITRATE", "4000k"),
            'crf': self.config.get(f"{profile}_CRF", "23"),
            'gop_size': self.config.get(f"{profile}_GOP_SIZE", "50"),
            'resolution': self.config.get(f"{profile}_RESOLUTION", "1920x1080")
        }
        
    def build_ffmpeg_command(self, camera: CameraSource, output_dir: str) -> List[str]:
        """Build complete FFmpeg command for a camera"""
        cmd = ['ffmpeg']
        
        # Input settings
        if camera.type == "RTSP":
            cmd.extend([
                '-rtsp_transport', self.config.get('RTSP_TRANSPORT', 'tcp'),
                '-timeout', self.config.get('RTSP_TIMEOUT', '30'),
                '-reconnect', '1',
                '-reconnect_delay_max', self.config.get('RTSP_RECONNECT_DELAY', '5')
            ])
        elif camera.type == "USB":
            cmd.extend([
                '-f', self.config.get('USB_CAMERA_FORMAT', 'v4l2'),
                '-framerate', self.config.get('USB_CAMERA_FRAMERATE', '30'),
                '-input_format', self.config.get('USB_CAMERA_INPUT_FORMAT', 'mjpeg')
            ])
            
        # Input source
        cmd.extend(['-i', camera.source])
        
        # Video encoding settings
        encoding = self.get_encoding_params()
        cmd.extend([
            '-c:v', encoding['codec'],
            '-preset', encoding['preset'],
            '-b:v', encoding['bitrate'],
            '-crf', encoding['crf'],
            '-g', encoding['gop_size'],
            '-sc_threshold', '0'
        ])
        
        # Video filters
        filters = self.get_video_filters(camera)
        if filters:
            cmd.extend(['-vf', ','.join(filters)])
            
        # Hardware acceleration (optimized for Intel N95 Quick Sync)
        if self.config.get('ENABLE_HARDWARE_ACCEL', False):
            accel_type = self.config.get('HARDWARE_ACCEL_TYPE', 'vaapi')
            if accel_type == 'qsv':
                # Intel Quick Sync Video for N95 processor
                cmd.extend(['-hwaccel', 'qsv', '-hwaccel_output_format', 'qsv'])
                cmd[cmd.index('libx264')] = 'h264_qsv'
                cmd.extend(['-global_quality', '25'])  # QSV quality setting
            elif accel_type == 'vaapi':
                cmd.extend(['-hwaccel', 'vaapi', '-hwaccel_output_format', 'vaapi'])
                cmd[cmd.index('libx264')] = 'h264_vaapi'
            elif accel_type == 'nvenc':
                cmd[cmd.index('libx264')] = 'h264_nvenc'
                
        # HLS output settings
        cmd.extend([
            '-f', 'hls',
            '-hls_time', str(self.config.get('HLS_SEGMENT_TIME', 2)),
            '-hls_list_size', str(self.config.get('HLS_LIST_SIZE', 5)),
            '-hls_flags', self.config.get('HLS_FLAGS', 'delete_segments'),
            '-hls_segment_filename', f"{output_dir}/segment_%03d.ts"
        ])
        
        # Output file
        cmd.append(f"{output_dir}/stream.m3u8")
        
        return cmd
        
    def can_fallback(self) -> bool:
        """Check if we can fall back to a lower quality profile"""
        profiles = ['HIGH_QUALITY', 'MEDIUM_QUALITY', 'LOW_QUALITY']
        current_index = profiles.index(self.current_profile) if self.current_profile in profiles else 0
        return current_index < len(profiles) - 1
        
    def fallback_quality(self) -> bool:
        """Fall back to next lower quality profile"""
        profiles = ['HIGH_QUALITY', 'MEDIUM_QUALITY', 'LOW_QUALITY']
        try:
            current_index = profiles.index(self.current_profile)
            if current_index < len(profiles) - 1:
                self.current_profile = profiles[current_index + 1]
                logger.warning(f"Falling back to quality profile: {self.current_profile}")
                return True
        except ValueError:
            pass
        return False

class MultiCameraService:
    """Main service class managing multiple camera streams"""
    
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.cameras: Dict[str, CameraSource] = {}
        self.profiler = FFmpegProfiler(self.config)
        
        # Service state
        self.running = False
        self.mqtt_client: Optional[mqtt.Client] = None
        
        # Performance monitoring
        self.system_monitor = SystemMonitor()
        
        # Initialize cameras from config
        self.setup_cameras()
        
        # Create output directories
        self.setup_directories()
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from file"""
        config = {}
        
        if not os.path.exists(config_file):
            logger.error(f"Configuration file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Convert boolean strings
                        if value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                        # Convert numeric strings
                        elif value.isdigit():
                            value = int(value)
                            
                        config[key] = value
                    except ValueError:
                        logger.warning(f"Failed to parse config line: {line}")
                        
        logger.info(f"Loaded configuration with {len(config)} settings")
        return config
        
    def setup_cameras(self):
        """Initialize camera sources from configuration"""
        camera_prefixes = set()
        
        # Find all camera definitions
        for key in self.config:
            if key.startswith('CAMERA_') and key.endswith('_ENABLED'):
                prefix = key.replace('_ENABLED', '')
                camera_id = prefix.replace('CAMERA_', '').lower()
                camera_prefixes.add((camera_id, prefix))
                
        # Create camera objects
        for camera_id, prefix in camera_prefixes:
            camera_config = {
                'enabled': self.config.get(f"{prefix}_ENABLED", False),
                'type': self.config.get(f"{prefix}_TYPE", 'RTSP'),
                'source': self.config.get(f"{prefix}_SOURCE", ''),
                'name': self.config.get(f"{prefix}_NAME", f'Camera {camera_id}'),
                'position': self.config.get(f"{prefix}_POSITION", 'unknown'),
                'primary': self.config.get(f"{prefix}_PRIMARY", False)
            }
            
            camera = CameraSource(camera_id, camera_config)
            self.cameras[camera_id] = camera
            
            logger.info(f"Configured camera: {camera}")
            
    def setup_directories(self):
        """Create necessary directories for HLS output"""
        base_dir = self.config.get('HLS_OUTPUT_DIR', '/opt/hlsfeed/hls')
        
        # Create base HLS directory
        os.makedirs(base_dir, exist_ok=True)
        
        # Create camera-specific directories
        for camera in self.cameras.values():
            if camera.enabled:
                output_dir = camera.get_output_path(base_dir)
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created output directory for {camera.name}: {output_dir}")
                
        # Create video recording directory
        video_dir = self.config.get('REPLAY_VIDEO_DIR', '/opt/hlsfeed/videos')
        os.makedirs(video_dir, exist_ok=True)
        
    def start_camera_stream(self, camera: CameraSource) -> bool:
        """Start FFmpeg process for a camera"""
        if not camera.enabled:
            return False
            
        with camera.lock:
            # Stop existing process if running
            self.stop_camera_stream(camera)
            
            # Build FFmpeg command
            output_dir = camera.get_output_path(self.config.get('HLS_OUTPUT_DIR', '/opt/hlsfeed/hls'))
            cmd = self.profiler.build_ffmpeg_command(camera, output_dir)
            
            logger.info(f"Starting stream for {camera.name}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            try:
                # Start FFmpeg process
                camera.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid  # Create new process group for clean termination
                )
                
                camera.last_restart = datetime.now()
                camera.health_status = "starting"
                
                logger.info(f"Started stream for {camera.name} (PID: {camera.process.pid})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start stream for {camera.name}: {e}")
                camera.health_status = "failed"
                return False
                
    def stop_camera_stream(self, camera: CameraSource):
        """Stop FFmpeg process for a camera"""
        with camera.lock:
            if camera.process:
                try:
                    # Terminate the process group to kill FFmpeg and children
                    os.killpg(os.getpgid(camera.process.pid), signal.SIGTERM)
                    
                    # Wait for process to terminate
                    camera.process.wait(timeout=10)
                    logger.info(f"Stopped stream for {camera.name}")
                    
                except subprocess.TimeoutExpired:
                    # Force kill if termination takes too long
                    logger.warning(f"Force killing stream for {camera.name}")
                    os.killpg(os.getpgid(camera.process.pid), signal.SIGKILL)
                    camera.process.wait()
                    
                except Exception as e:
                    logger.error(f"Error stopping stream for {camera.name}: {e}")
                    
                finally:
                    camera.process = None
                    camera.health_status = "stopped"
                    
    def monitor_streams(self):
        """Monitor stream health and restart failed streams"""
        while self.running:
            try:
                for camera in self.cameras.values():
                    if not camera.enabled:
                        continue
                        
                    # Check if stream is healthy
                    if not camera.is_healthy():
                        # Check restart throttling
                        time_since_restart = datetime.now() - camera.last_restart
                        min_restart_interval = timedelta(seconds=30)
                        
                        if time_since_restart > min_restart_interval:
                            logger.warning(f"Stream unhealthy for {camera.name}, restarting...")
                            camera.restart_count += 1
                            
                            # Check if we should fall back quality
                            if camera.restart_count > 3 and self.profiler.can_fallback():
                                logger.warning(f"Multiple restarts for {camera.name}, falling back quality")
                                self.profiler.fallback_quality()
                                camera.restart_count = 0  # Reset count after fallback
                                
                            self.start_camera_stream(camera)
                        else:
                            logger.debug(f"Restart throttled for {camera.name}")
                            
                    else:
                        camera.health_status = "healthy"
                        
                # System resource monitoring
                self.system_monitor.check_resources()
                
                # Publish status via MQTT
                self.publish_status()
                
            except Exception as e:
                logger.error(f"Error in stream monitoring: {e}")
                
            time.sleep(30)  # Check every 30 seconds
            
    def publish_status(self):
        """Publish service status to MQTT"""
        if not self.mqtt_client or not self.config.get('MONITORING_ENABLED', True):
            return
            
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'version': VERSION,
                'cameras': {}
            }
            
            for camera_id, camera in self.cameras.items():
                status['cameras'][camera_id] = {
                    'name': camera.name,
                    'enabled': camera.enabled,
                    'healthy': camera.is_healthy(),
                    'health_status': camera.health_status,
                    'restart_count': camera.restart_count,
                    'stream_url': camera.get_stream_url(
                        self.config.get('DERBYNET_HOSTNAME', 'derbynetpi'),
                        self.config.get('DERBYNET_PORT', 8037)
                    ) if camera.enabled else None
                }
                
            # Add system metrics
            status['system'] = self.system_monitor.get_metrics()
            status['quality_profile'] = self.profiler.current_profile
            
            topic = f"{self.config.get('MQTT_TOPIC_PREFIX', 'derbynet/camera')}/status"
            self.mqtt_client.publish(topic, json.dumps(status), qos=1, retain=True)
            
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")
            
    def setup_mqtt(self):
        """Set up MQTT client for monitoring"""
        if not self.config.get('MONITORING_ENABLED', True):
            return
            
        try:
            client_id = f"multicam_service_{int(time.time())}"
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
            
            # Set up will message
            will_topic = f"{self.config.get('MQTT_TOPIC_PREFIX', 'derbynet/camera')}/status"
            will_payload = json.dumps({"status": "offline", "timestamp": datetime.now().isoformat()})
            self.mqtt_client.will_set(will_topic, will_payload, qos=1, retain=True)
            
            # Connect to broker
            broker = self.config.get('MQTT_BROKER', '192.168.100.10')
            self.mqtt_client.connect(broker, 1883, 60)
            self.mqtt_client.loop_start()
            
            logger.info(f"Connected to MQTT broker at {broker}")
            
        except Exception as e:
            logger.error(f"Failed to setup MQTT: {e}")
            self.mqtt_client = None
            
    def cleanup_old_segments(self):
        """Clean up old HLS segments and recordings"""
        try:
            base_dir = self.config.get('HLS_OUTPUT_DIR', '/opt/hlsfeed/hls')
            max_age_minutes = self.config.get('MAX_SEGMENT_AGE_MINUTES', 30)
            
            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
            
            for camera in self.cameras.values():
                if camera.enabled:
                    output_dir = camera.get_output_path(base_dir)
                    if os.path.exists(output_dir):
                        for file_path in Path(output_dir).glob("*.ts"):
                            if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                                file_path.unlink()
                                
            # Clean up old recordings
            video_dir = self.config.get('REPLAY_VIDEO_DIR', '/opt/hlsfeed/videos')
            keep_days = self.config.get('RECORDING_KEEP_DAYS', 7)
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            
            if os.path.exists(video_dir):
                for file_path in Path(video_dir).glob("*.mkv"):
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        file_path.unlink()
                        logger.info(f"Cleaned up old recording: {file_path}")
                        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    def start(self):
        """Start the multi-camera service"""
        logger.info("Starting Multi-Camera HLS Service")
        self.running = True
        
        # Setup MQTT monitoring
        self.setup_mqtt()
        
        # Start all enabled camera streams
        for camera in self.cameras.values():
            if camera.enabled:
                self.start_camera_stream(camera)
                time.sleep(2)  # Stagger startup to reduce system load
                
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_streams, daemon=True)
        monitor_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        logger.info(f"Service started with {len([c for c in self.cameras.values() if c.enabled])} enabled cameras")
        
    def periodic_cleanup(self):
        """Periodic cleanup task"""
        while self.running:
            try:
                self.cleanup_old_segments()
                time.sleep(self.config.get('CLEANUP_INTERVAL_MINUTES', 5) * 60)
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                time.sleep(60)  # Wait a minute before retrying
                
    def stop(self):
        """Stop the multi-camera service"""
        logger.info("Stopping Multi-Camera HLS Service")
        self.running = False
        
        # Stop all camera streams
        for camera in self.cameras.values():
            self.stop_camera_stream(camera)
            
        # Disconnect MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
        logger.info("Service stopped")

class SystemMonitor:
    """Monitor system resources and performance"""
    
    def __init__(self):
        self.cpu_threshold = 80.0  # CPU usage threshold
        self.memory_threshold = 80.0  # Memory usage threshold
        self.disk_threshold = 90.0  # Disk usage threshold
        
    def get_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg(),
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
            
    def check_resources(self):
        """Check if system resources are under stress"""
        try:
            metrics = self.get_metrics()
            
            if metrics.get('cpu_percent', 0) > self.cpu_threshold:
                logger.warning(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
                
            if metrics.get('memory_percent', 0) > self.memory_threshold:
                logger.warning(f"High memory usage: {metrics['memory_percent']:.1f}%")
                
            if metrics.get('disk_percent', 0) > self.disk_threshold:
                logger.warning(f"High disk usage: {metrics['disk_percent']:.1f}%")
                
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DerbyNet Multi-Camera HLS Service')
    parser.add_argument('--config', 
                        default='/opt/hlsfeed/multicam-config.env',
                        help='Path to configuration file')
    parser.add_argument('--daemon', action='store_true',
                        help='Run as daemon')
    
    args = parser.parse_args()
    
    try:
        # Create service instance
        service = MultiCameraService(args.config)
        
        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            service.stop()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start service
        service.start()
        
        # Main loop
        try:
            while service.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            service.stop()
            
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()