<?php
require_once('inc/data.inc');
require_once('inc/kiosks.inc');
require_once('inc/scenes.inc');

maybe_apply_playlist_scene();

if (isset($_GET['address'])) {
  $kiosk_page = kiosk_page($_GET['address']);
}

// Check for active emergency broadcast first (takes priority)
$emergency_broadcast = null;
$emergency_json = read_raceinfo('emergency-broadcast', '');
if (!empty($emergency_json)) {
    $emergency_data = json_decode($emergency_json, true);
    if ($emergency_data && isset($emergency_data['active']) && $emergency_data['active']) {
        $emergency_broadcast = $emergency_data;
    }
}

// Check for active regular broadcast message (only if no emergency)
$broadcast_message = null;
if (!$emergency_broadcast) {
    $broadcast_json = read_raceinfo('broadcast-message', '');
    if (!empty($broadcast_json)) {
        $broadcast_data = json_decode($broadcast_json, true);
        if ($broadcast_data && isset($broadcast_data['expires'])) {
            // Check if message has expired
            if (time() < $broadcast_data['expires']) {
                $broadcast_message = $broadcast_data;
            } else {
                // Message expired, clear it
                write_raceinfo('broadcast-message', '');
            }
        }
    }
}

// Add emergency broadcast to kiosk page data (takes priority)
if ($emergency_broadcast) {
    $kiosk_page['emergency-broadcast'] = $emergency_broadcast;
}

// Add regular broadcast message to kiosk page data
if ($broadcast_message) {
    $kiosk_page['broadcast-message'] = $broadcast_message;
}

json_out('kiosk-setting', $kiosk_page);

?>
