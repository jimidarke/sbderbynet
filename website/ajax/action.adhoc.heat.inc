<?php
// Form an ad-hoc heat from the (pinny + age group) the coordinator entered per
// lane, then arm racing. Roster-less: each filled lane becomes a self-describing
// RaceChart row (racerid NULL, display_pinny, agegroup_classid) via
// adhoc_arm_heat(). Each call mints a NEW heat, so a pinny can run as many times
// as it likes over the session (best single time is the score).
//
// POST: pinny1..N and agegroup1..N, where the index is the physical lane
//       (1..lane_count). A blank pinny is a bye on that lane.
//
// Guards (race-day safety):
//   * Requires CONTROL_RACE_PERMISSION.
//   * Refuses unless the LIVE DB is the ad-hoc DB (adhoc-mode=1) — so this can
//     never inject heats into the official database.
//   * Refuses while a heat is already armed/racing.
//   * adhoc_arm_heat() is all-or-nothing: any unknown/duplicate/missing-age-group
//     entry aborts the whole arm so a kid is never silently dropped.

require_once('inc/racing-state.inc');
require_once('inc/adhoc.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else if (!adhoc_mode_active()) {
  json_failure('not-adhoc', 'Ad-hoc mode is not active. Turn it on first.');
} else if (get_racing_state()) {
  json_failure('heat-in-progress',
               'A heat is already armed. Finish or stop it before arming the next group.');
} else {
  // Collect lanes in physical order; position in the array IS the physical lane.
  $nlanes = get_lane_count();
  $lanes = array();
  for ($i = 1; $i <= $nlanes; $i++) {
    $lanes[] = array(
      'pinny' => isset($_POST["pinny$i"]) ? $_POST["pinny$i"] : '',
      'agegroup_classid' => isset($_POST["agegroup$i"]) ? $_POST["agegroup$i"] : 0,
    );
  }

  try {
    $armed = adhoc_arm_heat($lanes);
    set_current_heat($armed['roundid'], $armed['heat']);
    if (set_racing_state(1)) {
      derby_log_info("Ad-hoc heat armed: round {$armed['roundid']} heat {$armed['heat']}, "
                     . "{$armed['lanes']} lane(s)");
      json_out('adhoc_heat', array('roundid' => $armed['roundid'],
                                   'heat' => $armed['heat'],
                                   'lanes' => $armed['lanes']));
      json_success();
    } else {
      json_failure('cant_race', 'Could not arm the ad-hoc heat.');
    }
  } catch (Exception $e) {
    json_failure('arm-failed', $e->getMessage());
  }
}

require('ajax/query.poll.coordinator.inc');
?>
