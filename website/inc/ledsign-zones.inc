<?php
// LED Sign Zone Definitions
// Fixed set of zones that LED signs can be assigned to

// Zone configuration array
// Each zone has an id (used in database/MQTT), display name, and description
function ledsign_zones() {
  return array(
    array('id' => 'starter',
          'name' => 'Start Line',
          'description' => 'Race status display (READY/GO/STOP)'),

    array('id' => 'usher-lane1',
          'name' => 'Usher Lane 1',
          'description' => 'Next racer assignment for lane 1'),

    array('id' => 'usher-lane2',
          'name' => 'Usher Lane 2',
          'description' => 'Next racer assignment for lane 2'),

    array('id' => 'usher-lane3',
          'name' => 'Usher Lane 3',
          'description' => 'Next racer assignment for lane 3'),

    array('id' => 'finish-lane1',
          'name' => 'Finish Lane 1',
          'description' => 'Race time display for lane 1'),

    array('id' => 'finish-lane2',
          'name' => 'Finish Lane 2',
          'description' => 'Race time display for lane 2'),

    array('id' => 'finish-lane3',
          'name' => 'Finish Lane 3',
          'description' => 'Race time display for lane 3'),

    array('id' => 'registration',
          'name' => 'Registration',
          'description' => 'Sponsor rotation and check-in instructions'),

    array('id' => 'audience',
          'name' => 'Audience',
          'description' => 'General announcements and standings'),

    array('id' => 'sign',
          'name' => 'Generic Sign',
          'description' => 'Advertisements and general notifications'),
  );
}

// Get zone by ID
function ledsign_zone_by_id($zone_id) {
  foreach (ledsign_zones() as $zone) {
    if ($zone['id'] === $zone_id) {
      return $zone;
    }
  }
  return null;
}

// Get zone name by ID (for display)
function ledsign_zone_name($zone_id) {
  $zone = ledsign_zone_by_id($zone_id);
  return $zone ? $zone['name'] : $zone_id;
}

// Get all zone IDs as simple array
function ledsign_zone_ids() {
  return array_map(function($z) { return $z['id']; }, ledsign_zones());
}

// Check if zone ID is valid
function ledsign_zone_valid($zone_id) {
  return in_array($zone_id, ledsign_zone_ids());
}

// Get MQTT topics for a zone
function ledsign_mqtt_topics($zone_id) {
  if (!$zone_id) {
    return null;
  }
  return array(
    'content' => 'derbynet/ledsign/' . $zone_id . '/message',
    'broadcast' => 'derbynet/ledsign/broadcast',
  );
}
?>
