<?php
// LED Sign Individual Polling Endpoint
// ESP32 calls this to check for zone assignment changes
//
// Query: poll.ledsign
// Parameters: mac - LED sign MAC address

require_once('inc/ledsigns.inc');

// Get MAC from request
$mac = isset($_GET['mac']) ? $_GET['mac'] : null;

if (!$mac) {
  json_failure('missing-mac', 'MAC address parameter required');
  return;
}

// Register contact and get config
$ip = isset($_GET['ip']) ? $_GET['ip'] : $_SERVER['REMOTE_ADDR'];
$version = isset($_GET['version']) ? $_GET['version'] : null;

// Update last contact
ledsign_register($mac, $ip, $version);

// Get current configuration
$config = ledsign_config($mac);

// Return configuration
json_out('ledsign', $config);
?>
