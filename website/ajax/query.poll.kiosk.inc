<?php
require_once('inc/data.inc');
require_once('inc/kiosks.inc');
require_once('inc/scenes.inc');

maybe_apply_playlist_scene();

if (isset($_GET['address'])) {
  $kiosk_page = kiosk_page($_GET['address']);
}

// Check for active broadcast message
$broadcast_message = null;
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

// Add broadcast message to kiosk page data
if ($broadcast_message) {
    $kiosk_page['broadcast-message'] = $broadcast_message;
}

json_out('kiosk-setting', $kiosk_page);

?>
