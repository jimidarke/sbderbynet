<?php
/*
 * Clear Emergency Broadcast Action
 *
 * Clears any active emergency broadcast, removing the message from all kiosks and LED signs.
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

// Clear the emergency broadcast
write_raceinfo('emergency-broadcast', '');

// Also clear the regular broadcast (which was set for backward compatibility)
write_raceinfo('broadcast-message', '');

// Log the emergency clear
error_log("EMERGENCY BROADCAST CLEARED");

json_out('emergency_cleared', true);
json_success();
?>
