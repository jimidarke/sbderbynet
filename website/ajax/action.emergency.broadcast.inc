<?php
/*
 * Emergency Broadcast Action
 *
 * Sets an emergency broadcast message that persists until explicitly cleared.
 * All kiosks and LED signs will display this message until the emergency is cleared.
 *
 * $_POST['message'] - The emergency message text (max 255 characters)
 *
 * Copyright (C) 2025 Jimi Ford <jimiford@gmail.com>
 * MIT License
 */

require_once('inc/data.inc');
require_once('inc/permissions.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
    json_not_authorized();
    return;
}

$message = isset($_POST['message']) ? trim($_POST['message']) : '';

// Validate message
if (empty($message)) {
    json_failure('message', 'Emergency message cannot be empty');
    return;
}

if (strlen($message) > 255) {
    json_failure('message', 'Emergency message cannot exceed 255 characters');
    return;
}

// Create emergency broadcast data (no expiry - persists until cleared)
$emergency_data = array(
    'message' => $message,
    'timestamp' => time(),
    'active' => true
);

// Store emergency broadcast in database
// This uses a different key than regular broadcasts to prevent accidental clearing
write_raceinfo('emergency-broadcast', json_encode($emergency_data));

// Also store as the regular broadcast for backward compatibility with existing kiosks
// that may not yet be updated to check emergency-broadcast
write_raceinfo('broadcast-message', json_encode(array(
    'message' => '⚠️ EMERGENCY: ' . $message,
    'duration' => 86400,  // 24 hours - effectively "forever" until cleared
    'timestamp' => time(),
    'expires' => time() + 86400,
    'is_emergency' => true
)));

// Log the emergency broadcast
error_log("EMERGENCY BROADCAST ACTIVATED: " . $message);

json_out('emergency', $emergency_data);
json_success();
?>
