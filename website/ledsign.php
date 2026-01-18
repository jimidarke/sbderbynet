<?php
// LED Sign Registration Entry Point
// ESP32 LED sign controllers call this endpoint to register and get configuration
//
// Usage: GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF&ip=192.168.1.100&version=1.0.0
//
// Returns JSON with zone assignment and MQTT configuration

@session_start();

require_once('inc/data.inc');
require_once('inc/ledsigns.inc');

header('Content-Type: application/json');

// Get parameters from request
$mac = isset($_GET['mac']) ? $_GET['mac'] : null;
$ip = isset($_GET['ip']) ? $_GET['ip'] : $_SERVER['REMOTE_ADDR'];
$version = isset($_GET['version']) ? $_GET['version'] : 'unknown';

// MAC address is required
if (!$mac) {
  http_response_code(400);
  echo json_encode(array(
    'error' => 'Missing required parameter: mac',
    'status' => 'error'
  ));
  exit;
}

// Validate MAC format (should be 12 hex characters, with or without separators)
$clean_mac = preg_replace('/[^A-Fa-f0-9]/', '', $mac);
if (strlen($clean_mac) != 12) {
  http_response_code(400);
  echo json_encode(array(
    'error' => 'Invalid MAC address format',
    'status' => 'error'
  ));
  exit;
}

// Register the sign and get current zone assignment
$zone = ledsign_register($mac, $ip, $version);

// Get MQTT configuration
$mqtt = ledsign_mqtt_config();

// Build response
$response = array(
  'mac' => normalize_mac($mac),
  'zone' => $zone,
  'status' => $zone ? 'configured' : 'identify',
  'poll_interval' => 5,  // ESP32 should poll every 5 seconds
  'mqtt_broker' => $mqtt['broker'],
  'mqtt_port' => $mqtt['port'],
);

// Include MQTT topics if zone is assigned
if ($zone) {
  $response['mqtt_topics'] = ledsign_mqtt_topics($zone);
}

echo json_encode($response);
?>
