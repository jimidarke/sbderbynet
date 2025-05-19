# DerbyNet HLS Video Replay Documentation

This document explains how the HLS video feed is integrated into DerbyNet's replay functionality, specifically how the replay is triggered, how the interaction with the HLS feed works, what gets saved to the videos folder, and how the kiosks display the replay video.

## Overview

DerbyNet's replay functionality allows capturing video of races and playing them back immediately after a race completes. The system has been updated to support HLS (HTTP Live Streaming) as a video source. The HLS feed (configured at `http://derbynetpi:8037/hls/stream.m3u8`) provides a live video stream that can be buffered, replayed, and saved.

## How Replay is Triggered

There are three primary ways replays can be triggered:

1. **Automatically on Race Start**: When a race starts, the system can automatically trigger a replay after the race completes.
2. **Manually via Coordinator Interface**: Officials can manually trigger a replay by clicking the "Replay" button in the coordinator interface.
3. **Test Replay**: A test replay can be triggered for setup and testing purposes.

The key components for triggering the replay are:

- In `inc/replay.inc`, several functions handle different types of replay messages:
  - `send_replay_REPLAY()`: Sends a message to trigger an immediate replay
  - `send_replay_RACE_STARTS()`: Sets up a delayed replay to start automatically after a race
  - `send_replay_TEST()`: Triggers a test replay
  - `send_replay_START()`: Registers the beginning of a new heat for recording
  - `send_replay_CANCEL()`: Cancels a pending replay

- In `js/coordinator-controls.js`, the `trigger_replay()` function makes an AJAX call to `action.php` with the `action: "replay.trigger"` parameter, which invokes the handler in `ajax/action.replay.trigger.inc` to send the replay message.

## HLS Stream Integration

The HLS stream is integrated through the following mechanism:

1. **Stream Configuration**: The HLS stream URL is stored in the database as `hls-stream-url` and is retrieved in `replay.php` as:
   ```php
   $hlsStreamUrl = read_raceinfo('hls-stream-url', '');
   ```

2. **HLS.js Library**: The system uses the HLS.js JavaScript library to handle the HLS stream:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
   ```

3. **Stream Selection**: In the replay interface, users can select the HLS stream as a video source. When selected:
   - The HLS.js library loads the stream URL
   - It attaches the stream to a video element
   - A circular frame buffer begins recording from the stream

4. **Circular Frame Buffer**: The `CircularFrameBuffer` class in `js/circular-frame-buffer.js` maintains a buffer of recent video frames, configured by:
   - `length_ms`: The duration of the buffer in milliseconds (default: 4000)
   - `g_replay_options.count`: Number of replay repetitions (default: 2)
   - `g_replay_options.rate`: Playback speed as a percentage (default: 50%)

## Message Processing Flow

When a replay is triggered, the following sequence occurs:

1. A message is sent via either WebSocket (preferred) or the database queue
2. The replay page polls for messages using `poll_once_for_replay()` or listens via WebSockets
3. The `handle_replay_message()` function processes different command types:
   - `START`: Sets up recording for a new heat
   - `REPLAY`: Immediately triggers playback of recorded content
   - `RACE_STARTS`: Sets a timer to trigger replay after the race completes
   - `CANCEL`: Cancels any pending replay

## Video Recording and Storage

When the system is configured to save videos (`g_upload_videos = true`), the following happens:

1. During playback, the `on_replay()` function captures the replay and creates a video file
2. The `VideoCapture` class in `js/video-capture.js` records the video stream to a Blob
3. When playback completes, the `upload_video()` function sends the video file to the server
4. The server-side handler in `ajax/action.video.upload.inc` processes the uploaded file:
   - Files are saved to the directory specified by the `video-directory` setting in the database
   - If a file with the same name exists, a numbered suffix is added
   - Files are named based on the race information (class, round, heat)

Example of a saved video filename:
```
ClassA_Round1_Heat01.mkv
```

## Kiosk Display of Replay Video

Kiosks display the replay through a multi-layered approach:

1. **Playback Canvas**: When a replay is triggered, a canvas element (`#playback`) is used to display the frames
2. **Fullscreen Integration**: The replay can be displayed in fullscreen mode if enabled
3. **Iframe Integration**: The replay system can show the race data in an iframe, with the replay overlaid
4. **Notification System**: The replay system notifies any embedded content when replays start and end using the `postMessage` API:
   ```javascript
   announce_to_interior('replay-started');
   // ...and after playback completes:
   announce_to_interior('replay-ended');
   ```

## Configuration Options

The replay system has several configurable options:

1. **Replay Length**: How much video to buffer and replay (default: 4000ms)
2. **Replay Count**: How many times to repeat the replay (default: 2)
3. **Replay Speed**: Playback speed as a percentage (default: 50% - slow motion)
4. **Delay**: Optional delay before starting playback after race completion
5. **Upload Videos**: Whether to save videos to the server (configured in settings)
6. **HLS Stream URL**: The URL to the HLS stream

These settings can be configured in the settings page where the `hls-stream-url` parameter must be set to `http://derbynetpi:8037/hls/stream.m3u8`.

## Implementation Details

- The circular buffer records at 30fps, capturing frames from the video element
- When using HLS, the system uses `video.captureStream()` to record from the HLS player
- Videos are saved in MKV format (WebM with Matroska container)
- The system handles various error conditions like network errors and media errors
- Low-latency mode is enabled to minimize delay between the live event and the stream

## Recent Changes and Updates

### 2025-05-19 Fix
- Added null-checks for `g_hlsStreamUrl` in video-device-picker.js to prevent "Uncaught ReferenceError: g_hlsStreamUrl is not defined" errors when accessing photo capture functionality from pages that don't define this variable
- Made HLS stream URL handling more robust by checking if the variable exists before attempting to use it

## Comprehensive Troubleshooting

If the HLS replay functionality is not working as expected, follow these troubleshooting steps:

### 1. Check Configuration Values

1. **Verify HLS Stream URL**:
   - Navigate to `Settings` in the DerbyNet interface
   - Confirm that `hls-stream-url` is set to `http://derbynetpi:8037/hls/stream.m3u8`
   - To verify this in the database directly, run this SQL:
     ```sql
     SELECT itemvalue FROM RaceInfo WHERE itemkey = 'hls-stream-url';
     ```

2. **Verify Video Directory Setting**:
   - Check that `video-directory` is set and points to a valid, writable directory
   - SQL to verify: 
     ```sql
     SELECT itemvalue FROM RaceInfo WHERE itemkey = 'video-directory';
     ```
   - Ensure the directory exists and has proper permissions for the web server user

3. **Check Replay Configuration Parameters**:
   - Verify settings for `replay-skipback`, `replay-num-showings`, and `replay-rate`
   - SQL to verify: 
     ```sql
     SELECT itemkey, itemvalue FROM RaceInfo WHERE itemkey LIKE 'replay-%';
     ```

### 2. Check System Status

1. **Verify Replay Connection Status**:
   - In the coordinator interface, look at the replay status icon
   - Status "CONNECTED" indicates normal operation
   - Status "NOT CONNECTED" indicates the replay page isn't active or has issues

2. **Check HLS Stream Accessibility**:
   - Open the HLS URL directly in a compatible browser (like Chrome) or media player (like VLC)
   - Command to check from terminal: `curl -I http://derbynetpi:8037/hls/stream.m3u8`
   - Ensure the host `derbynetpi` resolves correctly on your network

3. **Test Network Connectivity**:
   - Ping the HLS source: `ping derbynetpi`
   - Check for any network or firewall restrictions

### 3. Examine Log Files

1. **PHP Error Logs**:
   - Check the main PHP error log at `/root/code/sbderbynet/website/error/error-logs/error.log`
   - Look for any HLS.js, MediaSource, or video-related errors

2. **Timer Logs**:
   - Timer logs are stored in the directory specified by the `logs-directory` setting
   - Default location: system temporary directory (`sys_get_temp_dir()`)
   - Files are named: `timer-YYYYMMDD-HHii-ss.log`
   - Recent log can be found by: 
     ```sql
     SELECT itemvalue FROM RaceInfo WHERE itemkey = 'timer-log';
     ```

3. **Browser Console**:
   - Open the browser developer tools (F12) on the replay page
   - Check the console for HLS.js errors, network failures, or JavaScript exceptions
   - Common errors include CORS issues, network failures, or media decoding problems

### 4. Validate and Debug Components

1. **Check Replay Page Setup**:
   - Open `/replay.php` in a browser
   - Select the "HLS Stream" option from the dropdown
   - Verify that the preview shows the video stream
   - Check browser console for any errors during initialization

2. **Debug WebSocket Communication**:
   - Check if a WebSocket URL is configured:
     ```sql
     SELECT itemvalue FROM RaceInfo WHERE itemkey = '_websocket_url';
     ```
   - If not using WebSockets, ensure polling is working by checking network activity
   - Review `js/message-poller.js` operation in browser developer tools

3. **Test HLS.js Library Compatibility**:
   - Verify browser supports HLS.js: `console.log(Hls.isSupported())`
   - Check HLS.js version compatibility: `console.log(Hls.version)`
   - Try a different browser if issues persist

4. **Test Video Capture and Playback**:
   - Use the Test Replay button to verify recording and playback
   - Check if frames are being captured by looking for "Recording at..." message
   - Monitor the circular buffer operation in console logs

5. **Debugging Uploaded Videos**:
   - If videos aren't being saved, ensure `g_upload_videos` is set to true
   - Check AJAX requests during upload (look for "video.upload" action in Network tab)
   - Verify temporary file handling in PHP (check `upload_max_filesize` in php.ini)

### 5. Advanced Troubleshooting

1. **Add Debug Logging**:
   - Add `console.log` statements to key functions in replay.php:
     - `on_device_selection`
     - `on_replay`
     - `start_playback`
     - `handle_replay_message`

2. **Verify HLS Stream Format**:
   - Check if the HLS stream is compatible with HLS.js
   - Ensure it has appropriate codec information and segment duration
   - Test with known working HLS streams

3. **Test Video Capturing**:
   - Add a test page with minimal HLS.js integration to isolate issues
   - Test if `captureStream()` is supported on your browser
   - Verify MediaRecorder API compatibility

4. **Check Resource Usage**:
   - Monitor CPU and memory usage during replay operation
   - High resource usage might indicate performance bottlenecks
   - Browser memory leaks can occur with long-running video operations

5. **Last Resort: Reset Configuration**:
   - Reset all replay settings to defaults:
     ```sql
     UPDATE RaceInfo SET itemvalue = '4000' WHERE itemkey = 'replay-skipback';
     UPDATE RaceInfo SET itemvalue = '2' WHERE itemkey = 'replay-num-showings';
     UPDATE RaceInfo SET itemvalue = '50' WHERE itemkey = 'replay-rate';
     ```

### 6. Repair Steps

If you've identified specific issues, here are common solutions:

1. **Fix HLS Stream Access**:
   - Update hosts file to ensure `derbynetpi` resolves correctly
   - Check if an IP address works better than hostname
   - Ensure CORS headers are enabled on the HLS server

2. **Fix Permission Issues**:
   - Ensure video directory has correct permissions:
     ```bash
     chmod 777 /path/to/video/directory
     ```
   - Check PHP's ability to write to the directory

3. **Fix JavaScript Errors**:
   - Update HLS.js to the latest version
   - Add error recovery callbacks to HLS.js initialization
   - Check for browser compatibility issues

4. **Fix WebSocket Issues**:
   - Ensure WebSocket server is running if configured
   - Check WebSocket URL formatting
   - Fall back to polling if WebSockets aren't reliable

5. **Fix Browser Compatibility**:
   - Use Chrome or Edge for best HLS.js compatibility
   - Ensure browser is updated to latest version
   - Check for browser extensions that might interfere with video playback