<?php
// Form an ad-hoc heat on the fly from the pinnies a start-line marshal enters,
// then arm racing. Each call mints a NEW heat number, so a racer can run as many
// times as they like over the session (their best single time is the score).
//
// POST: pinny1, pinny2, pinny3 (any may be blank; raw digits or a "PWD..." scan).
//
// Guards (race-day safety):
//   * Refuses unless the LIVE DB is the ad-hoc DB (adhoc-mode=1) — so this can
//     never inject heats into the official database.
//   * Refuses while a heat is already armed/racing.
//   * All-or-nothing on pinny resolution: any unknown/duplicate pinny aborts the
//     whole arm so a kid is never silently dropped.

require_once('inc/racing-state.inc');
require_once('inc/adhoc.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else if (!adhoc_mode_active()) {
  json_failure('not-adhoc', 'Ad-hoc mode is not active. Turn it on first.');
} else {
  $roundid = adhoc_roundid();
  if ($roundid === false) {
    json_failure('no-adhoc-round', 'Ad-hoc round is missing — rebuild ad-hoc mode.');
  } else if (get_racing_state()) {
    json_failure('heat-in-progress',
                 'A heat is already armed. Finish or stop it before arming the next group.');
  } else {
    // Resolve the entered pinnies (preserving lane order) to racerids.
    $racerids = array();
    $errors = array();
    $seen = array();
    foreach (array('pinny1', 'pinny2', 'pinny3') as $field) {
      $raw = isset($_POST[$field]) ? trim($_POST[$field]) : '';
      if ($raw === '') continue;
      $rid = adhoc_resolve_pinny($raw);
      if (!$rid) {
        $errors[] = $raw;
      } else if (isset($seen[$rid])) {
        $errors[] = $raw . ' (duplicate)';
      } else {
        $seen[$rid] = true;
        $racerids[] = $rid;
      }
    }

    if (count($errors) > 0) {
      json_failure('unknown-pinny',
                   'Unrecognized / duplicate pinny: ' . implode(', ', $errors)
                   . '. Check the number and that the racer is checked in.');
    } else if (count($racerids) == 0) {
      json_failure('no-racers', 'Enter at least one pinny.');
    } else {
      // Next heat number for the ad-hoc round (monotonic; never reused).
      $heat = 1 + read_single_value('SELECT MAX(heat) FROM RaceChart WHERE roundid = :r',
                                    array(':r' => $roundid), 0);
      $classid = read_single_value('SELECT classid FROM Rounds WHERE roundid = :r',
                                   array(':r' => $roundid));

      $stmt = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)'
                           . ' VALUES(:roundid, :heat, :lane, :racerid, :classid)');
      $lane = 0;
      foreach ($racerids as $rid) {
        $lane++;
        $stmt->execute(array(':roundid' => $roundid, ':heat' => $heat,
                             ':lane' => $lane, ':racerid' => $rid,
                             ':classid' => $classid));
      }

      set_current_heat($roundid, $heat);

      if (set_racing_state(1)) {
        derby_log_info("Ad-hoc heat armed: round $roundid heat $heat, "
                       . count($racerids) . ' lane(s)');
        json_out('adhoc_heat', array('roundid' => $roundid, 'heat' => $heat,
                                     'lanes' => count($racerids)));
        json_success();
      } else {
        json_failure('cant_race', 'Could not arm the ad-hoc heat.');
      }
    }
  }
}

require('ajax/query.poll.coordinator.inc');
?>
