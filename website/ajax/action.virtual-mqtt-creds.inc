<?php
//
// Returns MQTT credentials for the browser virtual-hardware pages under
// website/virtual/*.
//
// Cloud-only: refuses when DERBYNET_CLOUD_MODE is empty so a misbuilt local
// image never hands out broker credentials.
//
// Permission gate: the same coordinator role that can already start/stop
// races. The ACL in installer/docker-cloud/mosquitto/acl restricts this
// user to derbynet/device/B_* publishes regardless, so the worst-case
// damage from a leak is impersonating browser virtual hardware that should
// never coexist with real hardware on the same broker.

if (!is_cloud_mode()) {
  json_failure('not_cloud_mode',
               'Virtual hardware is only available in the cloud twin.');
  return;
}

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
  return;
}

$user = isset($_SERVER['VIRTUAL_MQTT_USER']) ? $_SERVER['VIRTUAL_MQTT_USER'] : '';
$pass = isset($_SERVER['VIRTUAL_MQTT_PASS']) ? $_SERVER['VIRTUAL_MQTT_PASS'] : '';

if ($user === '' || $pass === '') {
  json_failure('not_configured',
               'VIRTUAL_MQTT_USER / VIRTUAL_MQTT_PASS not set on the cloud stack. '
               . 'Run installer/docker-cloud/scripts/setup-mqtt-auth.sh and update .env.');
  return;
}

json_success();
json_out('credentials', array(
  'user' => $user,
  'pass' => $pass,
  // Caddy reverse-proxies /mqtt to the Mosquitto WebSocket listener at 9001.
  // Browser pages should connect via wss://<host>/mqtt (or ws:// in dev).
  'broker_path' => '/mqtt',
));
?>
