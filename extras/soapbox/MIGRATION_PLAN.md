# Migration Plan: HLS Feed to Consolidated HLS Transcoder

This document outlines the plan for consolidating the hlsfeed and hlstranscoder components into a single enhanced hlstranscoder component.

## Background

Currently, the system has two components that handle HLS streaming functionality:

1. **HLS Feed** (`/extras/soapbox/hlsfeed/`): 
   - Basic RTSP to HLS conversion
   - Simple web player
   - Replay handling for DerbyNet
   - Segment cleanup and monitoring

2. **HLS Transcoder** (`/extras/soapbox/hlstranscoder/`): 
   - More advanced RTSP to HLS conversion
   - Status dashboard and API
   - MQTT telemetry
   - Kiosk mode display
   - System monitoring
   - Remote update support

The consolidated component takes the best features from both and creates a unified HLS handler that provides all functionality in a single package.

## Migration Steps

### 1. Preparation

1. **Backup existing configurations**:
   ```bash
   cp -r /opt/hlsfeed /opt/hlsfeed_backup
   cp -r /opt/hlstranscoder /opt/hlstranscoder_backup
   ```

2. **Stop existing services**:
   ```bash
   sudo systemctl stop hlsfeed
   sudo systemctl stop hlsfeed-replay
   sudo systemctl stop hlstranscoder
   ```

### 2. Installation

1. **Update hlstranscoder files with consolidated versions**:
   ```bash
   # Copy new Python script
   sudo cp /path/to/hlstranscoder_with_replay.py /opt/hlstranscoder/hlstranscoder.py
   
   # Copy new configuration template
   sudo cp /path/to/config.template.consolidated /opt/hlstranscoder/config.template
   
   # Copy new kiosk script
   sudo cp /path/to/kiosk.sh.consolidated /opt/hlstranscoder/kiosk.sh
   sudo chmod +x /opt/hlstranscoder/kiosk.sh
   
   # Copy new nginx configuration
   sudo cp /path/to/hls.conf.consolidated /opt/hlstranscoder/nginx/hls.conf
   sudo cp /opt/hlstranscoder/nginx/hls.conf /etc/nginx/conf.d/
   ```

2. **Create replay directory**:
   ```bash
   sudo mkdir -p /var/www/html/replay
   sudo chown www-data:www-data /var/www/html/replay
   ```

3. **Migrate configurations**:

   Create a migration script that combines settings from both configurations:
   ```bash
   #!/bin/bash
   
   # Source paths
   HLSFEED_CONFIG="/opt/hlsfeed/config.env"
   HLSTRANSCODER_CONFIG="/etc/hlstranscoder/config.env"
   
   # Destination
   NEW_CONFIG="/etc/hlstranscoder/config.env.new"
   
   # Start with consolidated template
   cp /opt/hlstranscoder/config.template "$NEW_CONFIG"
   
   # Function to update config
   update_config() {
     local key="$1"
     local value="$2"
     local config_file="$3"
     
     if grep -q "^$key=" "$config_file"; then
       sed -i "s|^$key=.*|$key=\"$value\"|" "$config_file"
     fi
   }
   
   # Get values from hlsfeed config if it exists
   if [ -f "$HLSFEED_CONFIG" ]; then
     echo "Migrating settings from hlsfeed..."
     
     # Extract key settings from hlsfeed
     RTSP_URL=$(grep "^RTSP_URL=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     HLS_SEGMENT_TIME=$(grep "^HLS_SEGMENT_TIME=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     HLS_LIST_SIZE=$(grep "^HLS_LIST_SIZE=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     VIDEO_PRESET=$(grep "^VIDEO_PRESET=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     VIDEO_BITRATE=$(grep "^VIDEO_BITRATE=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     MAX_SEGMENT_AGE_MINUTES=$(grep "^MAX_SEGMENT_AGE_MINUTES=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     DERBYNET_HOSTNAME=$(grep "^DERBYNET_HOSTNAME=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     DERBYNET_PORT=$(grep "^DERBYNET_PORT=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     REPLAY_BUFFER_TIME=$(grep "^REPLAY_BUFFER_TIME=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     REPLAY_PLAYBACK_RATE=$(grep "^REPLAY_PLAYBACK_RATE=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     REPLAY_NUM_SHOWINGS=$(grep "^REPLAY_NUM_SHOWINGS=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     REPLAY_VIDEO_DIR=$(grep "^REPLAY_VIDEO_DIR=" "$HLSFEED_CONFIG" | cut -d= -f2- | tr -d '"')
     
     # Update new config with hlsfeed values
     [ ! -z "$RTSP_URL" ] && update_config "RTSP_SOURCE" "$RTSP_URL" "$NEW_CONFIG"
     [ ! -z "$HLS_SEGMENT_TIME" ] && update_config "SEGMENT_DURATION" "$HLS_SEGMENT_TIME" "$NEW_CONFIG"
     [ ! -z "$HLS_LIST_SIZE" ] && update_config "SEGMENT_LIST_SIZE" "$HLS_LIST_SIZE" "$NEW_CONFIG"
     [ ! -z "$VIDEO_PRESET" ] && update_config "FFMPEG_PRESET" "$VIDEO_PRESET" "$NEW_CONFIG"
     [ ! -z "$VIDEO_BITRATE" ] && update_config "BITRATE" "$VIDEO_BITRATE" "$NEW_CONFIG"
     [ ! -z "$MAX_SEGMENT_AGE_MINUTES" ] && update_config "MAX_SEGMENT_AGE" "$(($MAX_SEGMENT_AGE_MINUTES * 60))" "$NEW_CONFIG"
     [ ! -z "$DERBYNET_HOSTNAME" ] && update_config "DERBYNET_HOSTNAME" "$DERBYNET_HOSTNAME" "$NEW_CONFIG"
     [ ! -z "$DERBYNET_PORT" ] && update_config "DERBYNET_PORT" "$DERBYNET_PORT" "$NEW_CONFIG"
     [ ! -z "$REPLAY_BUFFER_TIME" ] && update_config "REPLAY_BUFFER_TIME" "$REPLAY_BUFFER_TIME" "$NEW_CONFIG"
     [ ! -z "$REPLAY_PLAYBACK_RATE" ] && update_config "REPLAY_PLAYBACK_RATE" "$REPLAY_PLAYBACK_RATE" "$NEW_CONFIG"
     [ ! -z "$REPLAY_NUM_SHOWINGS" ] && update_config "REPLAY_NUM_SHOWINGS" "$REPLAY_NUM_SHOWINGS" "$NEW_CONFIG"
     [ ! -z "$REPLAY_VIDEO_DIR" ] && update_config "REPLAY_VIDEO_DIR" "$REPLAY_VIDEO_DIR" "$NEW_CONFIG"
   fi
   
   # Get values from hlstranscoder config if it exists
   if [ -f "$HLSTRANSCODER_CONFIG" ]; then
     echo "Migrating settings from hlstranscoder..."
     
     # Extract key settings from hlstranscoder
     RTSP_SOURCE=$(grep "^RTSP_SOURCE=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     HLS_OUTPUT_DIR=$(grep "^HLS_OUTPUT_DIR=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     MQTT_BROKER=$(grep "^MQTT_BROKER=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     MQTT_PORT=$(grep "^MQTT_PORT=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     MQTT_USERNAME=$(grep "^MQTT_USERNAME=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     MQTT_PASSWORD=$(grep "^MQTT_PASSWORD=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     DERBY_ID=$(grep "^DERBY_ID=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     KIOSK_URL=$(grep "^KIOSK_URL=" "$HLSTRANSCODER_CONFIG" | cut -d= -f2- | tr -d '"')
     
     # Update new config with hlstranscoder values
     [ ! -z "$RTSP_SOURCE" ] && update_config "RTSP_SOURCE" "$RTSP_SOURCE" "$NEW_CONFIG"
     [ ! -z "$HLS_OUTPUT_DIR" ] && update_config "HLS_OUTPUT_DIR" "$HLS_OUTPUT_DIR" "$NEW_CONFIG"
     [ ! -z "$MQTT_BROKER" ] && update_config "MQTT_BROKER" "$MQTT_BROKER" "$NEW_CONFIG"
     [ ! -z "$MQTT_PORT" ] && update_config "MQTT_PORT" "$MQTT_PORT" "$NEW_CONFIG"
     [ ! -z "$MQTT_USERNAME" ] && update_config "MQTT_USERNAME" "$MQTT_USERNAME" "$NEW_CONFIG"
     [ ! -z "$MQTT_PASSWORD" ] && update_config "MQTT_PASSWORD" "$MQTT_PASSWORD" "$NEW_CONFIG"
     [ ! -z "$DERBY_ID" ] && update_config "DERBY_ID" "$DERBY_ID" "$NEW_CONFIG"
     [ ! -z "$KIOSK_URL" ] && update_config "KIOSK_URL" "$KIOSK_URL" "$NEW_CONFIG"
   fi
   
   # Apply the new configuration
   echo "New configuration created at $NEW_CONFIG"
   echo "Review the new configuration and then run:"
   echo "sudo mv $NEW_CONFIG $HLSTRANSCODER_CONFIG"
   ```

4. **Apply the new configuration**:
   ```bash
   sudo chmod +x migrate_config.sh
   sudo ./migrate_config.sh
   sudo mv /etc/hlstranscoder/config.env.new /etc/hlstranscoder/config.env
   ```

### 3. Restart Services

1. **Restart Nginx**:
   ```bash
   sudo systemctl restart nginx
   ```

2. **Start the consolidated HLS Transcoder**:
   ```bash
   sudo systemctl start hlstranscoder
   ```

3. **Check the service status**:
   ```bash
   sudo systemctl status hlstranscoder
   ```

4. **Verify the logs**:
   ```bash
   sudo journalctl -u hlstranscoder -f
   ```

### 4. Testing

1. **Verify HLS Stream Access**:
   - Check that the HLS stream is accessible at: `http://<server>:8037/hls/stream.m3u8`
   - Use VLC or a web browser to view the stream

2. **Test Replay Functionality**:
   - Send a test replay command via MQTT:
     ```bash
     mosquitto_pub -h <broker> -t "derbynet/replay/command" -m '{"command":"START","class":"Test","round":1,"heat":1}'
     ```
   - After a few seconds, trigger a replay:
     ```bash
     mosquitto_pub -h <broker> -t "derbynet/replay/command" -m '{"command":"REPLAY"}'
     ```
   - Verify that the replay window appears

3. **Check Status Dashboard**:
   - Access the status dashboard at: `http://<server>/status.html`
   - Verify that it shows system information, stream status, and replay information

4. **Test DerbyNet Integration**:
   - Configure DerbyNet to use the consolidated HLS Transcoder
   - Run a test race with replay

### 5. Clean Up

After successful migration and testing:

1. **Disable old services**:
   ```bash
   sudo systemctl disable hlsfeed
   sudo systemctl disable hlsfeed-replay
   ```

2. **Update documentation**:
   - Update the component documentation to reflect the consolidation
   - Update any references to hlsfeed in other documents

3. **Archive old components** (optional):
   ```bash
   # Move old components to an archive directory
   sudo mkdir -p /opt/archive
   sudo mv /opt/hlsfeed /opt/archive/
   ```

## Fallback Plan

If issues arise during migration:

1. **Stop the consolidated service**:
   ```bash
   sudo systemctl stop hlstranscoder
   ```

2. **Restore original configurations**:
   ```bash
   sudo cp -r /opt/hlsfeed_backup/* /opt/hlsfeed/
   sudo cp -r /opt/hlstranscoder_backup/* /opt/hlstranscoder/
   ```

3. **Restart original services**:
   ```bash
   sudo systemctl start hlsfeed
   sudo systemctl start hlsfeed-replay
   sudo systemctl start hlstranscoder
   ```

## Post-Migration Tasks

1. **Update deployment scripts** to include only the consolidated component
2. **Remove references to hlsfeed** from automated tests
3. **Document the new component architecture** in relevant documentation
4. **Train system administrators** on the consolidated system

## Component Comparison Table

| Feature                    | Old hlsfeed    | Old hlstranscoder | Consolidated |
|----------------------------|----------------|-------------------|--------------|
| RTSP to HLS conversion     | ✓              | ✓                 | ✓            |
| Web player interface       | ✓              | ✓                 | ✓            |
| Status dashboard           | ✗              | ✓                 | ✓            |
| DerbyNet replay handling   | ✓              | ✗                 | ✓            |
| MQTT telemetry             | Limited        | ✓                 | ✓            |
| Segment cleanup            | ✓              | ✓                 | ✓            |
| Stream health monitoring   | ✓              | ✓                 | ✓            |
| Kiosk mode                 | ✗              | ✓                 | ✓            |
| DerbyDisplay kiosk support | ✗              | ✗                 | ✓            |
| Remote update capability   | ✗              | ✓                 | ✓            |
| API for status/control     | ✗              | ✓                 | ✓            |
| Secure credential handling | ✓              | Limited           | ✓            |
| Video archiving            | ✗              | ✓                 | ✓            |