<?php
// LED Sign Zone Assignment Endpoint
// Assigns a zone to a LED sign
//
// Action: ledsign.assign
// Parameters:
//   mac - LED sign MAC address (required)
//   zone - Zone ID to assign (empty to unassign)

require_once('inc/ledsigns.inc');

// Check permissions - require SET_UP_PERMISSION
if (have_permission(SET_UP_PERMISSION)) {

  $mac = isset($_POST['mac']) ? $_POST['mac'] : null;
  $zone = isset($_POST['zone']) ? $_POST['zone'] : null;

  if (!$mac) {
    json_failure('missing-mac', 'MAC address parameter required');
    return;
  }

  // Assign zone (empty string means unassign)
  $result = ledsign_assign_zone($mac, $zone ? $zone : null);

  if ($result['success']) {
    // Return updated sign list and zone assignments
    $signs = all_ledsigns();
    $zones = ledsign_zone_assignments();

    json_out('assignment', array(
      'success' => true,
      'mac' => $result['mac'],
      'zone' => $result['zone'],
      'signs' => $signs,
      'zones' => $zones
    ));
  } else {
    json_failure('assign-failed', $result['error']);
  }

} else {
  json_not_authorized();
}
?>
