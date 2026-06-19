<?php
// Turn ad-hoc racing mode on or off by re-pointing the whole rig at a separate
// SQLite file (see inc/adhoc.inc / inc/db-marker.inc / docs/ADHOC.md).
//
//   mode=on  : (re)build adhoc.sqlite3 FRESH from the schema (no roster, no
//              schedule — just the event's age groups), then flip the active-DB
//              marker to it. The very next request opens the ad-hoc DB.
//   mode=off : stop any ad-hoc racing, then clear the marker → back to official.
//
// We do NOT append a coordinator poll here: the marker flip takes effect on the
// NEXT request, so a poll in this request would still reflect the pre-switch DB.

require_once('inc/racing-state.inc');
require_once('inc/adhoc.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else {
  $mode = isset($_POST['mode']) ? $_POST['mode'] : '';

  if ($mode === 'on') {
    try {
      $info = adhoc_build();
      if (!dn_set_active_db($info['path'])) {
        json_failure('marker-write', 'Built ad-hoc DB but could not write the active-DB marker ('
                     . dn_db_marker_path() . '). Check filesystem permissions.');
      } else {
        derby_log_info("Ad-hoc mode ON: built {$info['path']} with {$info['agegroups']} age group(s), "
                       . "round {$info['roundid']}");
        json_out('adhoc', array('mode' => 'on',
                                'agegroups' => $info['agegroups'],
                                'roundid' => $info['roundid'],
                                'path' => $info['path']));
        json_success();
      }
    } catch (Exception $e) {
      json_failure('adhoc-build', 'Could not build ad-hoc database: ' . $e->getMessage());
    }

  } else if ($mode === 'off') {
    // Only touch racing state if we are actually on the ad-hoc DB, so hitting
    // "off" while already on official can never stop an official heat.
    if (adhoc_mode_active()) {
      set_racing_state(0);
    }
    if (!dn_set_active_db('')) {
      json_failure('marker-write', 'Could not clear the active-DB marker ('
                   . dn_db_marker_path() . ').');
    } else {
      derby_log_info('Ad-hoc mode OFF: marker cleared, back to official DB.');
      json_out('adhoc', array('mode' => 'off'));
      json_success();
    }

  } else {
    json_failure('bad-mode', "mode must be 'on' or 'off'.");
  }
}
?>
