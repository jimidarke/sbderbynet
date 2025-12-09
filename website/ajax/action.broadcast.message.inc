<?php
/*
 * Copyright (C) 2025 Jimi Ford <jimiford@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
 * associated documentation files (the "Software"), to deal in the Software without restriction, 
 * including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
 * and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
 * subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial 
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
 * LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

// $_POST['message'] - The message text to broadcast (255 char limit)
// $_POST['duration'] - Optional duration in seconds (default 20)

if (!have_permission(CONTROL_RACE_PERMISSION)) {
    json_not_authorized();
    return;
}

$message = isset($_POST['message']) ? trim($_POST['message']) : '';
$duration = isset($_POST['duration']) ? intval($_POST['duration']) : 20;

// Validate message
if (empty($message)) {
    json_failure('message', 'Message cannot be empty');
    return;
}

if (strlen($message) > 255) {
    json_failure('message', 'Message cannot exceed 255 characters');
    return;
}

// Validate duration (1-300 seconds)
if ($duration < 1 || $duration > 300) {
    $duration = 20; // Default to 20 seconds
}

// Create broadcast message data
$broadcast_data = array(
    'message' => $message,
    'duration' => $duration,
    'timestamp' => time(),
    'expires' => time() + $duration
);

// Store broadcast message in database using RaceInfo table
// This allows it to persist across sessions and be accessible by all kiosks
write_raceinfo('broadcast-message', json_encode($broadcast_data));

// Add debug information to response
json_out('broadcast-data', $broadcast_data);
json_out('message-stored', true);

json_success();
?>