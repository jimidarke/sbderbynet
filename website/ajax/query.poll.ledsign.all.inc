<?php
// LED Sign Admin Dashboard Polling Endpoint
// Returns all discovered signs and zone assignments
//
// Query: poll.ledsign.all

require_once('inc/ledsigns.inc');

// Get all active LED signs
$signs = all_ledsigns();

// Get zone assignment summary
$zones = ledsign_zone_assignments();

// Return data for dashboard
json_out('ledsigns', array(
  'signs' => $signs,
  'zones' => $zones,
  'timestamp' => time()
));
?>
