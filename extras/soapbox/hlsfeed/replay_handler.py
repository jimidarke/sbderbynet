#!/usr/bin/env python3
"""
DerbyNet HLS Replay Handler

This module provides a bridge between DerbyNet replay commands and the HLS feed system.
It processes replay commands (START, REPLAY, RACE_STARTS, CANCEL) from DerbyNet via MQTT
and manages the HLS stream for replay functionality.

Replay commands are documented in the DerbyNet HLS replay documentation.

Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery for MQTT broker
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and live status reporting
- 0.1.0 - April 4, 2025 - Added MQTT integration for configuration
- 0.0.1 - March 31, 2025 - Initial implementation
"""

# Version information
VERSION = "0.5.0"  # Standardized version

import os
import sys
import json
import time
import logging
import argparse
import threading
import subprocess
import paho.mqtt.client as mqtt
from datetime import datetime
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hlsfeed_replay.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Starting DerbyNet HLS Replay Handler v{VERSION}")

# Default configuration
CONFIG = {
    'mqtt_broker': '192.168.100.10',
    'mqtt_port': 1883,
    'replay_topic': 'derbynet/replay/command',
    'status_topic': 'derbynet/replay/status',
    'replay_buffer_time': 4000,  # ms
    'replay_playback_rate': 50,  # percent
    'replay_num_showings': 2,
    'replay_video_dir': '/opt/hlsfeed/videos',
    'hls_stream_url': 'http://derbynetpi:8037/hls/stream.m3u8',
    'client_id': f'replay_handler_{int(time.time())}'
}

# Load configuration from environment variables
def load_config_from_env():
    """Load configuration from environment variables"""
    config_file = os.environ.get('CONFIG_FILE', '/opt/hlsfeed/config.env')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Map config file keys to our config keys
                        if key == 'MQTT_BROKER':
                            CONFIG['mqtt_broker'] = value
                        elif key == 'REPLAY_BUFFER_TIME':
                            CONFIG['replay_buffer_time'] = int(value)
                        elif key == 'REPLAY_PLAYBACK_RATE':
                            CONFIG['replay_playback_rate'] = int(value)
                        elif key == 'REPLAY_NUM_SHOWINGS':
                            CONFIG['replay_num_showings'] = int(value)
                        elif key == 'REPLAY_VIDEO_DIR':
                            CONFIG['replay_video_dir'] = value
                        elif key == 'DERBYNET_HOSTNAME':
                            # If hostname is defined, update the HLS stream URL
                            port = CONFIG['hls_stream_url'].split(':')[2].split('/')[0]
                            CONFIG['hls_stream_url'] = f'http://{value}:{port}/hls/stream.m3u8'
                        elif key == 'DERBYNET_PORT':
                            # If port is defined, update the HLS stream URL
                            parts = CONFIG['hls_stream_url'].split(':')
                            hostname = parts[1].lstrip('//')
                            CONFIG['hls_stream_url'] = f'http://{hostname}:{value}/hls/stream.m3u8'
                    except Exception as e:
                        logger.warning(f"Failed to parse config line: {line}, error: {e}")
    
    # Ensure video directory exists
    os.makedirs(CONFIG['replay_video_dir'], exist_ok=True)
    
    logger.info(f"Configuration loaded: {CONFIG}")

class ReplayHandler:
    """Handles DerbyNet replay commands via MQTT"""
    
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CONFIG['client_id'])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Set up will message for clean disconnection
        self.client.will_set(
            CONFIG['status_topic'], 
            payload=json.dumps({"status": "offline"}),
            qos=1,
            retain=True
        )
        
        # State tracking
        self.connected = False
        self.current_race = {
            'class': None,
            'round': None,
            'heat': None,
            'timestamp': None,
            'recording': False,
            'replay_pending': False
        }
        
        # Replay process management
        self.recording_process = None
        self.replay_process = None
        self.recording_lock = threading.Lock()
        
    def connect(self):
        """Connect to the MQTT broker"""
        try:
            self.client.connect(CONFIG['mqtt_broker'], CONFIG['mqtt_port'], 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {CONFIG['mqtt_broker']}:{CONFIG['mqtt_port']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self.client.publish(
            CONFIG['status_topic'], 
            payload=json.dumps({"status": "offline"}),
            qos=1,
            retain=True
        )
        self.client.loop_stop()
        self.client.disconnect()
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            
            # Subscribe to replay commands
            client.subscribe(CONFIG['replay_topic'], qos=1)
            logger.info(f"Subscribed to {CONFIG['replay_topic']}")
            
            # Publish online status
            client.publish(
                CONFIG['status_topic'], 
                payload=json.dumps({
                    "status": "online",
                    "version": VERSION
                }),
                qos=1,
                retain=True
            )
        else:
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")
            
    def on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        logger.warning(f"Disconnected from MQTT broker with result code {rc}")
        self.connected = False
        
        if rc != 0:
            logger.info("Attempting to reconnect...")
            try:
                client.reconnect()
            except Exception as e:
                logger.error(f"Failed to reconnect: {e}")
                
    def on_message(self, client, userdata, msg):
        """Callback for MQTT messages"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.info(f"Received message on {msg.topic}: {payload}")
            
            if msg.topic == CONFIG['replay_topic']:
                self.handle_replay_command(payload)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    def handle_replay_command(self, command):
        """Process replay commands from DerbyNet"""
        command_type = command.get('command')
        
        if command_type == 'START':
            # Begin recording a new heat
            self.start_recording(command)
        elif command_type == 'REPLAY':
            # Trigger immediate replay
            self.trigger_replay()
        elif command_type == 'RACE_STARTS':
            # Set up delayed replay after race
            self.race_starts(command)
        elif command_type == 'CANCEL':
            # Cancel pending replay
            self.cancel_replay()
        else:
            logger.warning(f"Unknown command type: {command_type}")
            
    def start_recording(self, command):
        """Start recording a new heat"""
        with self.recording_lock:
            # Stop any existing recording
            self.stop_recording()
            
            # Update race information
            self.current_race = {
                'class': command.get('class', 'Unknown'),
                'round': command.get('round', 0),
                'heat': command.get('heat', 0),
                'timestamp': int(time.time()),
                'recording': True,
                'replay_pending': False
            }
            
            logger.info(f"Starting recording for Class {self.current_race['class']}, "
                        f"Round {self.current_race['round']}, Heat {self.current_race['heat']}")
            
            # Start ffmpeg process for recording
            try:
                output_file = self.get_output_filename()
                cmd = [
                    'ffmpeg',
                    '-i', CONFIG['hls_stream_url'],
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-t', '30',  # Maximum recording length (30 seconds)
                    '-y',        # Overwrite output file
                    output_file
                ]
                
                self.recording_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                logger.info(f"Recording started to {output_file}")
                
                # Send status update
                self.client.publish(
                    CONFIG['status_topic'],
                    payload=json.dumps({
                        "status": "recording",
                        "race": self.current_race
                    }),
                    qos=1
                )
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                self.current_race['recording'] = False
                
    def stop_recording(self):
        """Stop the current recording process"""
        if self.recording_process:
            try:
                self.recording_process.terminate()
                self.recording_process.wait(timeout=5)
                logger.info("Recording stopped")
            except Exception as e:
                logger.error(f"Error stopping recording process: {e}")
                try:
                    self.recording_process.kill()
                except:
                    pass
            finally:
                self.recording_process = None
                
        self.current_race['recording'] = False
        
    def trigger_replay(self):
        """Trigger immediate replay of the most recent recording"""
        with self.recording_lock:
            # Stop recording if it's still going
            if self.current_race['recording']:
                self.stop_recording()
                
            # Check if we have a valid recording
            output_file = self.get_output_filename()
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                logger.warning(f"No valid recording found at {output_file}")
                return
                
            logger.info(f"Triggering replay of {output_file}")
            
            # Send status update
            self.client.publish(
                CONFIG['status_topic'],
                payload=json.dumps({
                    "status": "replaying",
                    "race": self.current_race
                }),
                qos=1
            )
            
            # Calculate replay parameters
            replay_speed = CONFIG['replay_playback_rate'] / 100.0
            
            # Start ffplay process for replay
            try:
                cmd = [
                    'ffplay',
                    '-i', output_file,
                    '-vf', f'setpts={1/replay_speed}*PTS',
                    '-af', f'atempo={replay_speed}',
                    '-loop', str(CONFIG['replay_num_showings']),
                    '-autoexit',
                    '-x', '640',
                    '-y', '480',
                    '-window_title', f"Replay: {self.current_race['class']} Round {self.current_race['round']} Heat {self.current_race['heat']}"
                ]
                
                self.replay_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Start a thread to monitor the replay process
                threading.Thread(target=self.monitor_replay, daemon=True).start()
                
            except Exception as e:
                logger.error(f"Failed to start replay: {e}")
                
    def monitor_replay(self):
        """Monitor the replay process until it completes"""
        if not self.replay_process:
            return
            
        try:
            self.replay_process.wait()
            logger.info("Replay complete")
            
            # Send status update
            self.client.publish(
                CONFIG['status_topic'],
                payload=json.dumps({
                    "status": "idle",
                    "race": self.current_race
                }),
                qos=1
            )
            
            self.replay_process = None
            self.current_race['replay_pending'] = False
            
        except Exception as e:
            logger.error(f"Error monitoring replay process: {e}")
            
    def race_starts(self, command):
        """Set a pending replay for when the race finishes"""
        self.current_race['replay_pending'] = True
        logger.info("Race started, replay pending")
        
        # Calculate the delay before starting the replay
        delay = command.get('delay', 1000)  # Default 1 second delay
        
        # Schedule the delayed replay
        threading.Timer(delay / 1000.0, self.trigger_replay).start()
        
    def cancel_replay(self):
        """Cancel any pending replay"""
        self.current_race['replay_pending'] = False
        
        # Kill any existing replay process
        if self.replay_process:
            try:
                self.replay_process.terminate()
                self.replay_process.wait(timeout=5)
            except:
                try:
                    self.replay_process.kill()
                except:
                    pass
                    
            self.replay_process = None
            
        logger.info("Replay canceled")
        
        # Send status update
        self.client.publish(
            CONFIG['status_topic'],
            payload=json.dumps({
                "status": "idle",
                "race": self.current_race
            }),
            qos=1
        )
            
    def get_output_filename(self):
        """Generate output filename based on current race information"""
        # Format: Class_Round_Heat.mkv (e.g., ClassA_Round1_Heat01.mkv)
        class_name = self.current_race['class'].replace(' ', '')
        round_num = self.current_race['round']
        heat_num = self.current_race['heat']
        
        filename = f"{class_name}_Round{round_num}_Heat{heat_num:02d}.mkv"
        return os.path.join(CONFIG['replay_video_dir'], filename)
            
    def run(self):
        """Run the replay handler service"""
        if not self.connect():
            logger.error("Failed to connect to MQTT broker, exiting")
            return
            
        # Set up signal handlers for graceful shutdown
        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}, shutting down")
            self.disconnect()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        # Main loop
        try:
            logger.info("Replay handler running")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
        finally:
            self.disconnect()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DerbyNet HLS Replay Handler')
    parser.add_argument('--config', help='Path to config file')
    args = parser.parse_args()
    
    if args.config:
        os.environ['CONFIG_FILE'] = args.config
        
    load_config_from_env()
    
    handler = ReplayHandler()
    handler.run()

if __name__ == '__main__':
    main()