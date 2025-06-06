#!/usr/bin/env python3
"""
Raspberry Pi Zero W Bluetooth Audio Player
5-Button Audio Trigger System

Hardware Setup:
- Connect 5 buttons to GPIO pins with internal pull-up resistors
- Each button connects between GPIO pin and GND
- Audio files stored on SD card in /home/pi/audio/ directory
- Streams audio to paired Bluetooth speaker via A2DP

Requirements:
- sudo apt-get install bluez bluez-tools pulseaudio-module-bluetooth
- sudo apt-get install mpg123 alsa-utils
- pip3 install RPi.GPIO

Usage:
- Pair Bluetooth speaker first using bluetoothctl
- Update BLUETOOTH_SPEAKER_MAC with your speaker's MAC address
- Place audio files in /home/pi/audio/ directory
- Run: python3 bluetooth_audio_player.py
"""

import RPi.GPIO as GPIO
import subprocess
import time
import threading
import signal
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/audio_player.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BluetoothAudioPlayer:
    def __init__(self):
        # GPIO pin assignments for buttons (BCM numbering)
        self.BUTTON_PINS = {
            1: 2,   # Button 1 -> GPIO 2
            2: 3,   # Button 2 -> GPIO 3  
            3: 4,   # Button 3 -> GPIO 4
            4: 5,   # Button 4 -> GPIO 5
            5: 6    # Button 5 -> GPIO 6
        }
        
        # Audio file assignments
        self.AUDIO_FILES = {
            1: "/home/pi/audio/sound1.mp3",
            2: "/home/pi/audio/sound2.mp3", 
            3: "/home/pi/audio/sound3.mp3",
            4: "/home/pi/audio/sound4.mp3",
            5: "/home/pi/audio/sound5.mp3"
        }
        
        # Bluetooth speaker configuration (multiple speakers supported)
        # List speakers in priority order - will connect to first available
        self.BLUETOOTH_SPEAKERS = [
            {
                "mac": "AA:BB:CC:DD:EE:FF",
                "name": "Primary_Speaker", 
                "priority": 1
            },
            {
                "mac": "11:22:33:44:55:66",
                "name": "Secondary_Speaker",
                "priority": 2  
            },
            {
                "mac": "77:88:99:AA:BB:CC",
                "name": "Backup_Speaker",
                "priority": 3
            }
        ]
        
        # Audio enhancement settings
        self.ENABLE_VOLUME_BOOST = True
        self.GAIN_LEVEL = 32  # Maximum gain boost (0-32)
        self.PLAY_TO_ALL_SPEAKERS = False  # Set to True for multi-speaker output
        self.AUTO_RECONNECT_INTERVAL = 30  # Seconds between reconnection attempts
        
        # Connected speakers tracking
        self.connected_speakers = []
        self.primary_speaker = None
        
        # Audio playback state
        self.current_process = None
        self.playback_lock = threading.Lock()
        
        # Setup GPIO
        self.setup_gpio()
        
        # Verify audio files exist
        self.verify_audio_files()
        
        # Start speaker monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_speaker_connections, daemon=True)
        self.monitoring_active = True
        
        logger.info("Enhanced Bluetooth Audio Player initialized")
        logger.info(f"Volume boost: {'Enabled' if self.ENABLE_VOLUME_BOOST else 'Disabled'}")
        logger.info(f"Multi-speaker mode: {'Enabled' if self.PLAY_TO_ALL_SPEAKERS else 'Disabled'}")

    def setup_gpio(self):
        """Initialize GPIO pins for button inputs"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for button_num, pin in self.BUTTON_PINS.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                pin, 
                GPIO.FALLING, 
                callback=lambda channel, btn=button_num: self.button_pressed(btn),
                bouncetime=300  # 300ms debounce
            )
            logger.info(f"Button {button_num} configured on GPIO {pin}")

    def verify_audio_files(self):
        """Check if audio files exist and create directory if needed"""
        audio_dir = Path("/home/pi/audio")
        audio_dir.mkdir(exist_ok=True)
        
        missing_files = []
        for button_num, file_path in self.AUDIO_FILES.items():
            if not Path(file_path).exists():
                missing_files.append(f"Button {button_num}: {file_path}")
        
        if missing_files:
            logger.warning("Missing audio files:")
            for missing in missing_files:
                logger.warning(f"  {missing}")
            logger.warning("Place MP3 files in /home/pi/audio/ directory")

    def connect_all_bluetooth_speakers(self):
        """Connect to all available Bluetooth speakers"""
        self.connected_speakers = []
        
        # Make device discoverable and pairable
        try:
            subprocess.run(["bluetoothctl", "discoverable", "on"], check=False)
            subprocess.run(["bluetoothctl", "pairable", "on"], check=False)
        except Exception as e:
            logger.warning(f"Failed to set discoverable/pairable: {e}")
        
        # Try to connect to speakers in priority order
        for speaker in self.BLUETOOTH_SPEAKERS:
            if self.connect_bluetooth_speaker(speaker):
                self.connected_speakers.append(speaker)
                if not self.primary_speaker:  # First connected becomes primary
                    self.primary_speaker = speaker
                    self.set_default_speaker(speaker)
                
                if not self.PLAY_TO_ALL_SPEAKERS:
                    break  # Only connect to one speaker if not in multi-speaker mode
                
        if self.connected_speakers:
            logger.info(f"Connected to {len(self.connected_speakers)} speaker(s)")
            return True
        else:
            logger.error("Failed to connect to any Bluetooth speakers")
            return False
    
    def connect_bluetooth_speaker(self, speaker_config):
        """Connect to a specific Bluetooth speaker"""
        try:
            logger.info(f"Connecting to {speaker_config['name']} ({speaker_config['mac']})")
            
            result = subprocess.run(
                ["bluetoothctl", "connect", speaker_config['mac']],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to {speaker_config['name']}")
                return True
            else:
                logger.warning(f"Failed to connect to {speaker_config['name']}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Connection to {speaker_config['name']} timed out")
            return False
        except Exception as e:
            logger.error(f"Error connecting to {speaker_config['name']}: {e}")
            return False
    
    def set_default_speaker(self, speaker_config):
        """Set the default audio output to specified speaker"""
        try:
            sink_name = f"bluez_sink.{speaker_config['mac'].replace(':', '_')}.a2dp_sink"
            subprocess.run(["pactl", "set-default-sink", sink_name], check=True)
            logger.info(f"Set {speaker_config['name']} as default audio output")
        except Exception as e:
            logger.error(f"Failed to set default speaker: {e}")
    
    def is_speaker_connected(self, speaker_config):
        """Check if a speaker is currently connected"""
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", speaker_config['mac']], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return "Connected: yes" in result.stdout
        except:
            return False
    
    def monitor_speaker_connections(self):
        """Monitor and reconnect to speakers if needed"""
        while self.monitoring_active:
            time.sleep(self.AUTO_RECONNECT_INTERVAL)
            
            if not self.monitoring_active:
                break
                
            # Check each connected speaker
            disconnected_speakers = []
            for speaker in self.connected_speakers[:]:
                if not self.is_speaker_connected(speaker):
                    logger.warning(f"Speaker {speaker['name']} disconnected")
                    disconnected_speakers.append(speaker)
                    self.connected_speakers.remove(speaker)
            
            # Try to reconnect disconnected speakers
            for speaker in disconnected_speakers:
                if self.connect_bluetooth_speaker(speaker):
                    self.connected_speakers.append(speaker)
                    logger.info(f"Reconnected to {speaker['name']}")
            
            # If primary speaker disconnected, select new primary
            if self.primary_speaker and self.primary_speaker not in self.connected_speakers:
                if self.connected_speakers:
                    self.primary_speaker = min(self.connected_speakers, key=lambda x: x['priority'])
                    self.set_default_speaker(self.primary_speaker)
                    logger.info(f"New primary speaker: {self.primary_speaker['name']}")
                else:
                    self.primary_speaker = None
                    logger.warning("No speakers connected")
    
    def maximize_volume(self):
        """Set audio volume to maximum levels"""
        if not self.ENABLE_VOLUME_BOOST:
            return True
            
        try:
            # Set master volume to 100%
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"], check=False)
            
            # Set specific Bluetooth sink volumes
            for speaker in self.connected_speakers:
                bt_sink = f"bluez_sink.{speaker['mac'].replace(':', '_')}.a2dp_sink"
                # Try 150% volume (may not be supported on all systems)
                subprocess.run(["pactl", "set-sink-volume", bt_sink, "150%"], check=False)
            
            # Boost audio using alsamixer if available
            subprocess.run(["amixer", "set", "Master", "100%"], check=False)
            subprocess.run(["amixer", "set", "PCM", "100%"], check=False)
            
            logger.debug("Audio volume maximized")
            return True
        except Exception as e:
            logger.warning(f"Failed to maximize volume: {e}")
            return False

    def button_pressed(self, button_num):
        """Handle button press events"""
        logger.info(f"Button {button_num} pressed")
        
        audio_file = self.AUDIO_FILES.get(button_num)
        if not audio_file:
            logger.error(f"No audio file assigned to button {button_num}")
            return
            
        if not Path(audio_file).exists():
            logger.error(f"Audio file not found: {audio_file}")
            return
        
        # Play audio in separate thread to avoid blocking
        threading.Thread(
            target=self.play_audio,
            args=(audio_file, button_num),
            daemon=True
        ).start()

    def play_audio(self, audio_file, button_num):
        """Play audio file via Bluetooth with volume enhancement"""
        with self.playback_lock:
            try:
                # Stop any currently playing audio
                self.stop_current_playback()
                
                # Maximize volume before playback
                self.maximize_volume()
                
                logger.info(f"Playing audio: {audio_file}")
                
                if self.PLAY_TO_ALL_SPEAKERS and len(self.connected_speakers) > 1:
                    self.play_to_all_speakers(audio_file, button_num)
                else:
                    self.play_to_single_speaker(audio_file, button_num)
                    
            except Exception as e:
                logger.error(f"Error playing audio file {audio_file}: {e}")
            finally:
                self.current_process = None
    
    def play_to_single_speaker(self, audio_file, button_num):
        """Play audio to primary speaker with volume boost"""
        try:
            # Build mpg123 command with gain boost
            cmd = [
                "mpg123", 
                "--quiet",
                "-o", "pulse"
            ]
            
            # Add gain boost if enabled
            if self.ENABLE_VOLUME_BOOST:
                cmd.extend(["--gain", str(self.GAIN_LEVEL)])
            
            cmd.append(audio_file)
            
            # Play audio using enhanced mpg123 command
            self.current_process = subprocess.Popen(cmd)
            
            # Wait for playback to complete
            self.current_process.wait()
            
            if self.current_process.returncode == 0:
                logger.info(f"Finished playing button {button_num} audio")
            else:
                logger.warning(f"Audio playback interrupted for button {button_num}")
                
        except Exception as e:
            logger.error(f"Error in single speaker playback: {e}")
    
    def play_to_all_speakers(self, audio_file, button_num):
        """Play audio to all connected speakers simultaneously"""
        try:
            logger.info(f"Playing to {len(self.connected_speakers)} speakers simultaneously")
            
            # Create multiple mpg123 processes for each connected speaker
            processes = []
            
            for speaker in self.connected_speakers:
                try:
                    sink_name = f"bluez_sink.{speaker['mac'].replace(':', '_')}.a2dp_sink"
                    
                    # Build command for this speaker
                    cmd = [
                        "mpg123",
                        "--quiet", 
                        "-o", "pulse"
                    ]
                    
                    # Add gain boost if enabled
                    if self.ENABLE_VOLUME_BOOST:
                        cmd.extend(["--gain", str(self.GAIN_LEVEL)])
                    
                    cmd.append(audio_file)
                    
                    # Set specific audio device for this process
                    env = os.environ.copy()
                    env['PULSE_SINK'] = sink_name
                    
                    process = subprocess.Popen(cmd, env=env)
                    processes.append((process, speaker['name']))
                    logger.debug(f"Started playback to {speaker['name']}")
                    
                except Exception as e:
                    logger.warning(f"Failed to start playback to {speaker['name']}: {e}")
            
            # Wait for all processes to complete
            for process, name in processes:
                try:
                    process.wait()
                    logger.debug(f"Finished playback to {name}")
                except Exception as e:
                    logger.warning(f"Error waiting for {name} playback: {e}")
                    
            logger.info(f"Finished playing to all speakers")
            
        except Exception as e:
            logger.error(f"Error in multi-speaker playback: {e}")

    def stop_current_playback(self):
        """Stop currently playing audio"""
        if self.current_process and self.current_process.poll() is None:
            logger.info("Stopping current audio playback")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.current_process.kill()

    def test_audio_system(self):
        """Test audio system and Bluetooth connections"""
        logger.info("Testing enhanced audio system...")
        
        # Test Bluetooth connections
        if not self.connect_all_bluetooth_speakers():
            logger.error("Bluetooth connection failed - check speaker pairing")
            return False
        
        # Start monitoring thread
        if not self.monitoring_thread.is_alive():
            self.monitoring_thread.start()
        
        # Test volume maximization
        self.maximize_volume()
        
        # Test audio playback with a short beep if no test file exists
        test_file = "/home/pi/audio/test.mp3"
        if Path(test_file).exists():
            logger.info("Playing test audio file")
            self.play_audio(test_file, "test")
        else:
            logger.info("No test audio file found, skipping audio test")
            
        return True

    def run(self):
        """Main run loop"""
        logger.info("Starting Bluetooth Audio Player")
        logger.info("Button assignments:")
        for button_num, audio_file in self.AUDIO_FILES.items():
            logger.info(f"  Button {button_num} (GPIO {self.BUTTON_PINS[button_num]}): {audio_file}")
        
        # Test system
        if not self.test_audio_system():
            logger.error("System test failed")
            return
        
        logger.info("System ready - press buttons to play audio")
        logger.info("Press Ctrl+C to exit")
        
        try:
            # Keep the program running
            signal.pause()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        # Stop monitoring thread
        self.monitoring_active = False
        
        # Stop any playing audio
        self.stop_current_playback()
        
        # Clean up GPIO
        GPIO.cleanup()
        
        logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run audio player
    player = BluetoothAudioPlayer()
    player.run()

if __name__ == "__main__":
    main()