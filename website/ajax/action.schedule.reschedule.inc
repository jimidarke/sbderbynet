<?php

require_once('inc/schedule-adjuster.inc');

$roundid = $_POST['roundid'];
$racerid = $_POST['racerid'];
$dry_run = $_POST['dry-run'];
$trace = $_POST['trace'];

// =========================================================
if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else {
  $conflicting = read_raceinfo('reschedule_underway');
  // The time limit check is to handle the case where an attempt timed out (by
  // PHP or web server) and wasn't able to clear the marker.
  if ($conflicting !== false && time() - $conflicting < 2 * OVERALL_TIME_LIMIT) {
    json_failure('busy', 'Another schedule adjustment is already underway');
    return;  // Quits the include()
  }
  write_raceinfo('reschedule_underway', time());
  try {
    $t0 = time();

    $adj = new ScheduleAdjuster($roundid, $trace);

    $adj->remove_departed();

    $t1 = time();

    if ($racerid) {
      $adj->inject_new_racer($racerid);
    } else {
      // Insert all the racers for this round not already in the schedule.
      $racer_stmt = $db->prepare('SELECT racerid FROM Roster'
                                 .' WHERE roundid = :roundid'
                                 .' AND (SELECT passedinspection FROM RegistrationInfo'
                                 .'      WHERE racerid = Roster.racerid) = 1'
                                 .' AND NOT EXISTS(SELECT 1 FROM RaceChart'
                                 .'                WHERE racerid = Roster.racerid'
                                 .'                AND roundid = :roundid2)');
      $racer_stmt->execute(array(':roundid' => $roundid,
                                 ':roundid2' => $roundid));
      foreach ($racer_stmt as $racer_row) {
        if (time() - $t1 < OVERALL_TIME_LIMIT) {
          record_action(array('action' => 'schedule.*reschedule',
                              'racerid' => $racer_row['racerid']));
          $adj->inject_new_racer($racer_row['racerid']);
        }
      }
    }

    $t2 = time();

    $adj->squeeze_out_byes();

    if ($trace) {
      json_out('adjuster', $adj->to_json());
    }

    // May be false if there are no changes, or a rescheduling somehow failed.
    $new_chart = $adj->updated_race_chart();

    if ($new_chart !== null) {
      $renumbering_map = $adj->renumbering_map();
      $ok = true;
      json_out('chart', $adj->chart_debug());

      $t3 = $t2;
      if (!$dry_run) {
        update_race_chart($roundid, $new_chart, $renumbering_map);
        $t3 = time();
        assign_master_heats();
      }
      $t4 = time();
      json_out("timing", array('load' => $t1 - $t0,
                               'inject' => $t2 - $t1,
                               'update' => $t3 - $t2,
                               'master-heat' => $t4 - $t3,
                               'internal' => $adj->times));
      if ($ok) {
        json_success();
        mark_all_kiosks_for_reload();
        require('ajax/query.poll.coordinator.inc');
      }
    } else {
      json_failure('nochart', 'Unable to build new schedule');
    }
  } finally {
    delete_from_raceinfo('reschedule_underway');
  }
}
