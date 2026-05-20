<?php

// // Normally we use max-runs-per-car = 0, so that each car runs once per lane.
// // For some unusual situations, we want to limit to just 1 run per car (no
// // matter which lane).  In that case, we first pad out the roster with BYEs so
// // each car can get one run before we would start running anyone's second run.
// // Then we form the rough schedule as a simple rotation chart (because the
// // normal chart generators may put a given car only in heats that include a
// // second run for some other car).  Finally, in make_ordered_schedule, we
// // abandon those heats from the rough schedule that would cause any car to have
// // second run.

// // require_once('inc/schedule_rough.inc');
// // require_once('inc/schedule_ordered.inc');
// // require_once('inc/schedule_utils.inc');
// // require_once('inc/schedule_rotation.inc');
// // require_once('inc/events.inc');

// // Returns roster, where roster[sequence] = racerid,
// // 0 <= sequence < number of racers in roundid.
// function read_roster($roundid, $by_car_number = false) {
//   global $db;
//   $roster = array();
//   $stmt = $db->prepare('SELECT rosterid, Roster.racerid FROM Roster'
//                        .' INNER JOIN RegistrationInfo'
//                        .' ON Roster.racerid = RegistrationInfo.racerid'
//                        .' WHERE roundid = :roundid'
//                        .' AND passedinspection = 1'
//                        .($by_car_number ? ' ORDER BY carnumber, rosterid' : ' ORDER BY rosterid'));
//   $stmt->execute(array(':roundid' => $roundid));
//   foreach ($stmt as $row) {
//     $roster[] = $row['racerid'];
//   }
//   return $roster;
// }

// // Converts a schedule (racers identified by sequence, 0 <= c < $ncars) to a
// // race chart (racers identified by racerid).
// function form_chart(&$schedule, &$roster) {
//   $heats = array();
//   foreach ($schedule as $sched_heat) {
//     $heat = array();
//     foreach ($sched_heat as $index) {
//       $heat[] = $roster[$index];
//     }
//     $heats[] = $heat;
//   }
//   return $heats;
// }

// // Writes the race chart entries into the database.
// function write_chart($roundid, &$heats) {
//   global $db;
//   record_event(EVENT_SCHEDULE_ADDED, array('roundid' => $roundid));
//   $db->exec('DELETE FROM RaceChart WHERE roundid = '.$roundid);
//   $classid = read_single_value('SELECT classid FROM Rounds WHERE roundid = '.$roundid);
//   $stmt = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)'
//                        .' VALUES(:roundid, :heat, :lane, :racerid, :classid)');
//   $heat_index = 0;
//   foreach ($heats as $heat) {
//     ++$heat_index;
//     $lane_index = 0;
//     foreach ($heat as $racerid) {
//       ++$lane_index;
//       if ($racerid) {
//         $stmt->execute(array(':roundid' => $roundid,
//                              ':heat' => $heat_index,
//                              ':lane' => $lane_index,
//                              ':racerid' => $racerid,
//                              ':classid' => $classid));
//       }
//     }
//   }
// }

// // The top-level scheduling function.  Constructs a schedule, converts to a race
// // chart, and writes the race chart into the database.
// function schedule_one_round($roundid, $nlanes, $n_times_per_lane, $trace) {
//   $rotation_schedule = read_raceinfo('rotation-schedule', 0);
//   $roster = read_roster($roundid, /*by_car_number=*/$rotation_schedule);
//   if (count($roster) < 2) {
//     return false;
//   }
//   while (count($roster) < $nlanes) {
//     $roster[] = null;  // Byes to bring up the roster count to at least the number of lanes
//   }
//   $max_runs_per_car = read_raceinfo('max-runs-per-car', 0);
//   while (count($roster) * $max_runs_per_car % $nlanes != 0) {
//     $roster[] = null;
//   }
//   if (!$rotation_schedule) {
//     $sched = make_ordered_schedule($nlanes, count($roster), $n_times_per_lane,
//                                    $max_runs_per_car, $trace);
//   } else {
//     $sched = make_rotation_schedule($nlanes, count($roster), $n_times_per_lane, $trace);
//   }
//   write_chart($roundid, spread_across_unused_lanes(form_chart($sched, $roster)));
//   return true;
// }



// UPDATE: 31-03-2025

require_once('inc/schedule_rough.inc');
require_once('inc/schedule_ordered.inc');
require_once('inc/schedule_utils.inc');
require_once('inc/schedule_rotation.inc');
require_once('inc/events.inc');

function read_roster($roundid, $by_car_number = false)
{
  global $db;
  $roster = array();
  $group_by_weight = read_raceinfo('group-weighted-cars', 0);  // Updated key

  $stmt = $db->prepare('SELECT rosterid, Roster.racerid, RegistrationInfo.carweight FROM Roster'
    . ' INNER JOIN RegistrationInfo ON Roster.racerid = RegistrationInfo.racerid'
    . ' WHERE roundid = :roundid AND passedinspection = 1'
    . ($by_car_number ? ' ORDER BY carnumber, rosterid' : ' ORDER BY rosterid'));
  $stmt->execute(array(':roundid' => $roundid));

  foreach ($stmt as $row) {
    $roster[] = array('racerid' => $row['racerid'], 'carweight' => $row['carweight']);
  }

  // Sort by weight if grouping is enabled
  if ($group_by_weight) {
    usort($roster, function ($a, $b) {
      return $a['carweight'] <=> $b['carweight'];
    });
  }
  // error_log(print_r($roster, true));
  return array_column($roster, 'racerid');  // Return only racer IDs
}

// Converts a schedule to a race chart
function form_chart(&$schedule, &$roster)
{
  $heats = array();
  foreach ($schedule as $sched_heat) {
    $heat = array();
    foreach ($sched_heat as $index) {
      $heat[] = $roster[$index];
    }
    $heats[] = $heat;
  }
  return $heats;
}

// Writes the race chart to the database
function write_chart($roundid, &$heats)
{
  global $db;
  record_event(EVENT_SCHEDULE_ADDED, array('roundid' => $roundid));
  $db->exec('DELETE FROM RaceChart WHERE roundid = ' . $roundid);
  $classid = read_single_value('SELECT classid FROM Rounds WHERE roundid = ' . $roundid);
  $stmt = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)'
    . ' VALUES(:roundid, :heat, :lane, :racerid, :classid)');
  $heat_index = 0;
  foreach ($heats as $heat) {
    ++$heat_index;
    $lane_index = 0;
    foreach ($heat as $racerid) {
      ++$lane_index;
      if ($racerid) {
        $stmt->execute(array(
          ':roundid' => $roundid,
          ':heat' => $heat_index,
          ':lane' => $lane_index,
          ':racerid' => $racerid,
          ':classid' => $classid
        ));
      }
    }
  }
}

// Main scheduling function
function schedule_one_round(
  $roundid,
  $nlanes,
  $n_times_per_lane,
  $trace,
  $group_weighted_cars = 0,
  $avoid_consecutive = 0,
  $avoid_same_lane = 0
) {
  global $db;

  // First clear existing schedule
  $db->exec('DELETE FROM RaceChart WHERE roundid = ' . $roundid);

  // Verify racers exist in racing group before scheduling
  $stmt = $db->prepare(
    "SELECT ri.racerid 
     FROM RegistrationInfo ri
     INNER JOIN Rounds r ON ri.classid = r.classid
     WHERE r.roundid = :roundid
    --  AND ri.excluded = 0
     AND ri.registered = 1"  // Added registered check
  );

  $stmt->execute([':roundid' => $roundid]);
  $valid_racers = $stmt->fetchAll(PDO::FETCH_COLUMN);

  // Only schedule racers that are in the racing group
  if (!empty($valid_racers)) {
    // Legacy triple elimination logic removed - replaced by JSON hardcoded approach
    $round_info = read_single_row(
      'SELECT r.roundid, 
             r.round, 
             r.roundname, 
             r.classid,
             r.phase
      FROM Rounds r
      WHERE r.roundid = :roundid',
      [':roundid' => $roundid]
    );

    if (!$round_info) {
      error_log("Round info not found for roundid: " . $roundid);
      return false;
    }

    // Check for elimination tournament configuration and override n_times_per_lane if needed
    // This ensures proper scheduling whether called from action.schedule.generate.inc or playlist.inc
    require_once('inc/elimination-config.inc');
    $elimination_state = get_elimination_tournament_state($round_info['classid']);

    if ($elimination_state) {
      $rounds_config = $elimination_state['age_group']['rounds'];
      $round_config = null;

      // Find the round configuration for this specific round
      foreach ($rounds_config as $config) {
        if ($config['round_name'] == $round_info['roundname']) {
          $round_config = $config;
          break;
        }
      }

      if ($round_config) {
        $races_per_racer = $round_config['races_per_racer'];
        error_log("schedule_one_round: Detected elimination round '{$round_info['roundname']}' with races_per_racer={$races_per_racer}");

        if ($races_per_racer == 1) {
          // For rounds with 1 race per racer: use custom elimination scheduling
          error_log("schedule_one_round: Using single-race elimination scheduling for '{$round_info['roundname']}'");
          return schedule_elimination_single_race($roundid, $nlanes);
        } else if ($races_per_racer == 3) {
          // For rounds with 3 races per racer: override to n_times_per_lane=1
          $n_times_per_lane = 1;
          error_log("schedule_one_round: Using n_times_per_lane=1 for '{$round_info['roundname']}' (3 races per racer)");
        }
      }
    }

    // Check for custom elimination tournament single-race scheduling (legacy path)
    if ($n_times_per_lane == 0) {
      return schedule_elimination_single_race($roundid, $nlanes);
    }

    $rotation_schedule = read_raceinfo('rotation-schedule', 0);
    $roster = read_roster($roundid, $rotation_schedule);

    if (count($roster) < 2) {
      return false;
    }

    while (count($roster) < $nlanes) {
      $roster[] = null;  // Add BYEs to match lane count
    }

    $max_runs_per_car = read_raceinfo('max-runs-per-car', 0);
    while (count($roster) * $max_runs_per_car % $nlanes != 0) {
      $roster[] = null;
    }

    // Per-class minimum heat-gap window (soft penalty).  Falls back to 6 when
    // the column is unset (e.g. legacy class created before schema 17).  6 is
    // empirically the sweet spot for 3-lane soapbox: reliably produces min-gap
    // >= 5 across 26-31 racer rounds without the over-spread regression we
    // see at 8+ (where the windowed penalty dilutes the d=1 bias enough that
    // the greedy occasionally accepts a min=3 in exchange for distant gains).
    $min_heat_gap = read_single_value(
      'SELECT COALESCE(min_heat_gap, 6) FROM Classes WHERE classid = :classid',
      array(':classid' => $round_info['classid']));
    if ($min_heat_gap === false || $min_heat_gap === null) $min_heat_gap = 6;
    $min_heat_gap = (int)$min_heat_gap;

    // $roster = array_intersect($roster, $valid_racers);

    if (!$rotation_schedule) {
      $sched = make_ordered_schedule(
        $roundid,
        $nlanes,
        count($roster),
        $n_times_per_lane,
        $max_runs_per_car,
        $trace,
        $group_weighted_cars,
        $avoid_consecutive,
        $avoid_same_lane,
        $min_heat_gap
      );
    } else {
      $sched = make_rotation_schedule($nlanes, count($roster), $n_times_per_lane, $trace);
    }

    $chart = form_chart($sched, $roster);
    $spread_chart = spread_across_unused_lanes($chart);
    write_chart($roundid, $spread_chart);
    return true;
  } else {
    error_log("No valid racers found in racing group for round " . $roundid);
    return false;
  }
}

// Legacy triple elimination helper functions removed - replaced by JSON hardcoded approach

/**
 * Custom scheduling for elimination tournaments with 1 race per racer
 * Creates a simple sequential schedule where each racer gets exactly one race
 */
function schedule_elimination_single_race($roundid, $nlanes) {
  global $db;
  
  try {
    // Get roster of racers for this round
    $roster = read_roster($roundid, false);
    if (empty($roster)) {
      error_log("No racers found in roster for roundid: " . $roundid);
      return false;
    }
    
    error_log("Creating single-race elimination schedule for " . count($roster) . " racers on " . $nlanes . " lanes");
    
    // Clear existing race chart
    $db->exec('DELETE FROM RaceChart WHERE roundid = ' . $roundid);
    
    // Get classid for the round
    $classid = read_single_value('SELECT classid FROM Rounds WHERE roundid = ' . $roundid);
    
    // Create sequential heats
    $stmt = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)
                         VALUES(:roundid, :heat, :lane, :racerid, :classid)');
    
    $heat_number = 1;
    $lane_number = 1;
    
    foreach ($roster as $racerid) {
      if ($racerid) { // Skip null/bye entries
        $stmt->execute(array(
          ':roundid' => $roundid,
          ':heat' => $heat_number,
          ':lane' => $lane_number,
          ':racerid' => $racerid,
          ':classid' => $classid
        ));
        
        $lane_number++;
        if ($lane_number > $nlanes) {
          $lane_number = 1;
          $heat_number++;
        }
      }
    }
    
    record_event(EVENT_SCHEDULE_ADDED, array('roundid' => $roundid));
    
    $total_entries = count(array_filter($roster)); // Count non-null entries
    $total_heats = ceil($total_entries / $nlanes);
    error_log("Created elimination schedule: {$total_entries} entries across {$total_heats} heats");
    
    return true;
    
  } catch (Exception $e) {
    error_log("Error in schedule_elimination_single_race: " . $e->getMessage());
    return false;
  }
}