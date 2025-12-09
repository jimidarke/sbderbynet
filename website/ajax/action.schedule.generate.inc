<?php
// // Action to schedule heats for a round, with each car running once in each lane.
// // (An exception is if max-runs-per-car is non-zero; see below.)
// //

// $roundid = $_POST['roundid'];
// $n_times_per_lane = isset($_POST['n_times_per_lane']) ? $_POST['n_times_per_lane'] : 1;

// $trace = !isset($_POST['trace']) ? false : array('trace');

// //
// // Normally we use max-runs-per-car = 0, so that each car runs once per lane.
// // For some unusual situations, we want to limit to just 1 run per car (no
// // matter which lane).  In that case, we first pad out the roster with BYEs so
// // each car can get one run before we would start running anyone's second run.
// // Then we form the rough schedule as a simple rotation chart (because the
// // normal chart generators may put a given car only in heats that include a
// // second run for some other car).  Finally, in make_ordered_schedule, we
// // abandon those heats from the rough schedule that would cause any car to have
// // second run.

// require_once('inc/data.inc');
// require_once('inc/masterheat.inc');
// require_once('inc/autoadvance.inc');
// require_once('inc/schedule_utils.inc');
// require_once('inc/schedule_one_round.inc');

// if (have_permission(CONTROL_RACE_PERMISSION)) {
//   // $nlanes reports the number of physical lanes, even if some won't be used.
//   $nlanes = read_raceinfo('lane_count', 0);
//   // For generating the schedule, we care about the number of lanes actually in use.
//   $nlanes -= count_one_bits(read_raceinfo('unused-lane-mask', 0));
//   if ($nlanes <= 0) {
//     json_failure('nlanes', 'Number of lanes hasn\'t been determined.');
// // TODO
// //  } else if (!isset($all_generators[$nlanes])) {
// //    json_failure('too-many-lanes', 'Lane scheduling is only available for up to '
// //    .max(array_keys($all_generators)).' lanes.');
//   } else if (results_exist($roundid)) {
//     json_failure('results-exist', 'Race results already exist for this round');
//   } else {
// 	if (schedule_one_round($roundid, $nlanes, $n_times_per_lane, $trace)) {
//       json_success();
//       if ($trace) {
//         json_out('trace', $trace);
//       }
//       require('ajax/query.poll.coordinator.inc');
//     } else {
//       json_failure('too-few-racers', 'There need to be at least two racers checked in'
//                    .' to generate a schedule.');
//     }
//   }

//   assign_master_heats();
//   if (use_master_sched()) {
//     $current = get_running_round();
//     advance_heat($current, 'next-up', /* report failure */ false);
//   }
// } else {
//   json_not_authorized();
// }



// UPDATE: As on 31-03-2025

// Action to schedule heats for a round, with each car running once in each lane.
require_once('inc/data.inc');
require_once('inc/masterheat.inc');
require_once('inc/autoadvance.inc');
require_once('inc/schedule_utils.inc');
require_once('inc/schedule_one_round.inc');
require_once('inc/error-logging.inc');

$roundid = $_POST['roundid'];
$n_times_per_lane = isset($_POST['n_times_per_lane']) ? $_POST['n_times_per_lane'] : 1;

$trace = !isset($_POST['trace']) ? false : array('trace');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  // Get number of lanes in use  
  $nlanes = read_raceinfo('lane_count', 0);
  $nlanes -= count_one_bits(read_raceinfo('unused-lane-mask', 0));

  if ($nlanes <= 0) {
    json_failure('nlanes', 'Number of lanes hasn\'t been determined.');
  } else if (results_exist($roundid)) {
    json_failure('results-exist', 'Race results already exist for this round');
  } else {

    // Fetch heat ordering settings
    $group_weighted_cars = intval(read_raceinfo('group-weighted-cars', 0));
    $avoid_consecutive = intval(read_raceinfo('avoid-consecutive', 0));
    $avoid_same_lane = intval(read_raceinfo('avoid-same-lane', 0));


    // Get round info without legacy columns (JSON hardcoded approach only)
    $round_info = read_single_row(
      'SELECT r.roundid, r.round, r.roundname, r.classid
       FROM Rounds r
       WHERE r.roundid = :roundid',
      [':roundid' => $roundid],
      PDO::FETCH_ASSOC  // Force associative array
    );

    if (!$round_info) {
      json_failure('round-not-found', 'Round not found');
      return;
    }

    // Debug: Show what we got from the query
    error_log("Round info after SQL query: " . print_r($round_info, true));

    // Check for elimination tournaments and apply appropriate scheduling
    require_once('inc/elimination-config.inc');
    
    error_log("Schedule generation: roundid={$roundid}, classid={$round_info['classid']}, round='{$round_info['roundname']}', n_times_per_lane={$n_times_per_lane}");
    
    // First check if this is a JSON-based elimination tournament
    $elimination_state = get_elimination_tournament_state($round_info['classid']);
    error_log("Elimination state result: " . ($elimination_state ? "FOUND" : "NOT FOUND"));
    
    if ($elimination_state) {
      // This is an elimination tournament - always use JSON configuration values
      $current_round = $elimination_state['current_round'];
      $rounds_config = $elimination_state['age_group']['rounds'];
      
      error_log("Elimination tournament detected: current_round={$current_round}, looking for round='{$round_info['roundname']}'");
      
      // Find the round configuration for this specific round
      $round_config = null;
      foreach ($rounds_config as $config) {
        error_log("Checking config round: '{$config['round_name']}' against '{$round_info['roundname']}'");
        if ($config['round_name'] == $round_info['roundname']) {
          $round_config = $config;
          break;
        }
      }
      
      if ($round_config) {
        $old_value = $n_times_per_lane;
        $races_per_racer = $round_config['races_per_racer'];
        
        if ($races_per_racer == 1) {
          // For rounds with 1 race per racer: use custom elimination scheduling
          write_raceinfo('max-runs-per-car', 0); // Disable max_runs_per_car 
          $n_times_per_lane = 0; // Use special value to trigger custom elimination logic
          error_log("Elimination tournament scheduling: Round {$round_info['roundname']} using custom single-race scheduling for {$races_per_racer} race per racer");
        } else if ($races_per_racer == 3) {
          // For rounds with 3 races per racer: use normal scheduling (1 time per lane)
          write_raceinfo('max-runs-per-car', 0); // Disable max_runs_per_car limit
          $n_times_per_lane = 1; // Each racer appears once per lane (3 total races)
          error_log("Elimination tournament scheduling: Round {$round_info['roundname']} set n_times_per_lane=1 for {$races_per_racer} races per racer (once per lane)");
        } else {
          error_log("ERROR: Unsupported races_per_racer value: {$races_per_racer}");
        }
      } else {
        error_log("ERROR: Could not find elimination round config for: '{$round_info['roundname']}'");
        error_log("Available rounds: " . json_encode(array_column($rounds_config, 'round_name')));
      }
    } else {
      error_log("No elimination state found for classid={$round_info['classid']} - using manual setting: {$n_times_per_lane}");
    }
    
    // Legacy triple elimination logic has been removed - replaced by JSON hardcoded approach

    // Check for unregistered or failed inspection racers
    $stmt = $db->prepare('SELECT carnumber, registered, passedinspection 
                         FROM RaceChart
                         JOIN RegistrationInfo ON RaceChart.racerid = RegistrationInfo.racerid
                         WHERE roundid = :roundid');
    $stmt->execute([':roundid' => $roundid]);

    $unregistered = [];
    $failed_inspection = [];

    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
      if (!$row['registered']) {
        $unregistered[] = $row['carnumber'];
      }
      if (!$row['passedinspection']) {
        $failed_inspection[] = $row['carnumber'];
      }
    }

    // Don't schedule racers who failed inspection
    if (!empty($failed_inspection)) {
      json_failure(
        'inspection_failed',
        'The following racers have not passed inspection and will not be scheduled: ' .
        implode(', ', $failed_inspection)
      );
      return;
    }

    // Allow scheduling but warn about unregistered racers
    if (!empty($unregistered)) {
      error_log("Warning: Unregistered racers in schedule: " . implode(', ', $unregistered));
    }

    // Continue with schedule generation...
    derby_log_info("Generating schedule: Round {$roundid} ({$round_info['roundname']}), lanes: $nlanes, n_times_per_lane: $n_times_per_lane");
    if (schedule_one_round($roundid, $nlanes, $n_times_per_lane, $trace, $group_weighted_cars, $avoid_consecutive, $avoid_same_lane)) {
      derby_log_info("Schedule generated successfully for Round {$roundid}");
      json_success();
      if ($trace) {
        json_out('trace', $trace);
      }

      // Add warning about unregistered racers to response
      if (!empty($unregistered)) {
        json_out(
          'unregistered_warning',
          'The following racers are scheduled but not registered: ' .
          implode(', ', $unregistered)
        );
      }

      require('ajax/query.poll.coordinator.inc');
    } else {
      derby_log_error("Schedule generation failed for Round {$roundid} - too few racers");
      json_failure(
        'too-few-racers',
        'There need to be at least two racers checked in to generate a schedule.'
      );
    }
  }

  assign_master_heats();
  if (use_master_sched()) {
    $current = get_running_round();
    advance_heat($current, 'next-up', /* report failure */ false);
  }
} else {
  json_not_authorized();
}

?>