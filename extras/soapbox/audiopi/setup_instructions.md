# Raspberry Pi Zero W Bluetooth Audio Player Setup

## Hardware Wiring

Connect 5 push buttons to the Pi Zero W:

| Button | GPIO Pin | Physical Pin | Connection |
|--------|----------|--------------|------------|
| 1 | GPIO 2 | Pin 3 | Button to GND (Pin 6) |
| 2 | GPIO 3 | Pin 5 | Button to GND (Pin 9) |
| 3 | GPIO 4 | Pin 7 | Button to GND (Pin 14) |
| 4 | GPIO 5 | Pin 29 | Button to GND (Pin 20) |
| 5 | GPIO 6 | Pin 31 | Button to GND (Pin 25) |

**Note**: No external pull-up resistors needed - using internal pull-ups.

## Software Setup

### 1. Install Required Packages
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Bluetooth and audio packages
sudo apt install -y bluez bluez-tools pulseaudio-module-bluetooth
sudo apt install -y mpg123 alsa-utils
sudo apt install -y python3-pip

# Install Python GPIO library
pip3 install RPi.GPIO
```

### 2. Configure Audio System
```bash
# Add user to audio group
sudo usermod -a -G audio pi

# Enable PulseAudio for user session
systemctl --user enable pulseaudio
```

### 3. Pair Bluetooth Speaker
```bash
# Start bluetoothctl
bluetoothctl

# In bluetoothctl prompt:
power on
agent on
default-agent
scan on

# Wait for your speaker to appear, then:
pair AA:BB:CC:DD:EE:FF  # Replace with your speaker's MAC
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF

# Exit bluetoothctl
exit
```

### 4. Prepare Audio Files
```bash
# Create audio directory
mkdir -p /home/pi/audio

# Copy your MP3 files (name them appropriately):
# /home/pi/audio/sound1.mp3
# /home/pi/audio/sound2.mp3  
# /home/pi/audio/sound3.mp3
# /home/pi/audio/sound4.mp3
# /home/pi/audio/sound5.mp3
```

### 5. Configure the Script
Edit `bluetooth_audio_player.py` and update:
```python
# Replace with your speaker's actual MAC address
self.BLUETOOTH_SPEAKER_MAC = "AA:BB:CC:DD:EE:FF"

# Replace with your speaker's name
self.BLUETOOTH_SPEAKER_NAME = "Your_Speaker_Name"
```

### 6. Test the System
```bash
# Make script executable
chmod +x bluetooth_audio_player.py

# Run the script
python3 bluetooth_audio_player.py
```

### 7. Auto-Start on Boot (Optional)
Create a systemd service:
```bash
sudo nano /etc/systemd/system/audio-player.service
```

Add this content:
```ini
[Unit]
Description=Bluetooth Audio Player
After=bluetooth.service

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /home/pi/bluetooth_audio_player.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable the service:
```bash
sudo systemctl enable audio-player.service
sudo systemctl start audio-player.service
```

## Usage

1. Power on the Pi Zero W
2. Wait for boot (30-60 seconds)
3. Press any of the 5 buttons to play corresponding audio file
4. New button press will stop current audio and play new file

## Troubleshooting

### Check Bluetooth Connection
```bash
bluetoothctl info AA:BB:CC:DD:EE:FF
```

### Check Audio Devices
```bash
pactl list sinks short
```

### View Logs
```bash
tail -f /home/pi/audio_player.log
```

### Test Audio Manually
```bash
mpg123 -o pulse /home/pi/audio/sound1.mp3
```

## Customization

### Change Button Pins
Edit the `BUTTON_PINS` dictionary in the script:
```python
self.BUTTON_PINS = {
    1: 2,   # Button 1 -> GPIO 2
    2: 3,   # Button 2 -> GPIO 3  
    # ... etc
}
```

### Change Audio Files
Edit the `AUDIO_FILES` dictionary:
```python
self.AUDIO_FILES = {
    1: "/home/pi/audio/your_file1.mp3",
    2: "/home/pi/audio/your_file2.mp3",
    # ... etc
}
```

### Adjust Debounce Time
Change the `bouncetime` parameter (in milliseconds):
```python
bouncetime=300  # Increase if getting double-presses
```

### Configure Audio Enhancement
```python
# Volume and audio settings
self.ENABLE_VOLUME_BOOST = True       # Enable/disable volume maximization
self.GAIN_LEVEL = 32                  # Software gain boost (0-32)
self.PLAY_TO_ALL_SPEAKERS = False     # Single vs multi-speaker output
self.AUTO_RECONNECT_INTERVAL = 30     # Reconnection check frequency
```

### Add/Remove Speakers
Modify the `BLUETOOTH_SPEAKERS` list:
```python
self.BLUETOOTH_SPEAKERS = [
    # Add as many speakers as needed
    {"mac": "XX:XX:XX:XX:XX:XX", "name": "Speaker_Name", "priority": 1},
    # Lower priority numbers = higher preference
    # Remove entries for speakers you don't want to use
]
```

## Performance Tips

### Maximum Volume Output
1. **Enable volume boost**: Set `ENABLE_VOLUME_BOOST = True`
2. **Use multi-speaker mode**: Set `PLAY_TO_ALL_SPEAKERS = True`
3. **Choose high-output speakers**: Use speakers with high wattage ratings
4. **Optimize placement**: Position speakers for acoustic reinforcement

### Connection Reliability
1. **Use quality speakers**: Choose speakers with stable Bluetooth connections
2. **Minimize interference**: Keep WiFi and Bluetooth on different channels
3. **Monitor signal strength**: Check RSSI values in logs
4. **Reduce distance**: Keep speakers within 10 meters of Pi Zero W

## Hardware Considerations for Maximum Volume

### Speaker Selection
- **High-wattage speakers**: Choose speakers with 20W+ output for best results
- **Efficient drivers**: Look for speakers with high sensitivity ratings (>85dB)
- **Quality Bluetooth**: Ensure speakers support A2DP profile and apt-X codecs
- **Battery life**: Consider speakers with long battery life for cart racing

### Power Optimization
- **USB power bank**: Use high-capacity power bank for Pi Zero W
- **Speaker charging**: Ensure speakers are fully charged before events
- **Power management**: Monitor power consumption in logs

## Troubleshooting Volume Issues

### If Audio Isn't Loud Enough
1. Check `ENABLE_VOLUME_BOOST = True` in script
2. Verify `GAIN_LEVEL = 32` (maximum)
3. Test with `PLAY_TO_ALL_SPEAKERS = True` 
4. Check speaker volume buttons/settings
5. Verify PulseAudio configuration applied correctly

### If Audio Quality Is Poor
1. Reduce `GAIN_LEVEL` to avoid distortion (try 20-25)
2. Check Bluetooth connection quality
3. Verify audio file quality (use high bitrate MP3s)
4. Test with single speaker mode first