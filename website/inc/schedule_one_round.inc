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
    $round_info = read_single_row(
      'SELECT r.roundid, 
             r.round, 
             r.roundname, 
             r.classid,
             COALESCE(r.is_triple_elim, 0) as is_triple_elim,
             COALESCE(r.elim_type, "preliminary") as elim_type,
             r.phase
      FROM Rounds r
      WHERE r.roundid = :roundid',
      [':roundid' => $roundid]
    );

    $round_info = read_single_row(
      'SELECT r.roundid, 
            r.round, 
            r.roundname, 
            r.classid,
            COALESCE(r.is_triple_elim, 0) as is_triple_elim,
            COALESCE(r.elim_type, "preliminary") as elim_type,
            r.phase
     FROM Rounds r
     WHERE r.roundid = :roundid',
      [':roundid' => $roundid]
    );

    // Ensure consistent array format
    if (isset($round_info[0])) {
      $round_info = array(
        'roundid' => $round_info[0],
        'round' => $round_info[1],
        'roundname' => $round_info[2],
        'classid' => $round_info[3],
        'is_triple_elim' => isset($round_info[4]) ? $round_info[4] : 0,
        'elim_type' => isset($round_info[5]) ? $round_info[5] : 'preliminary',
        'phase' => isset($round_info[6]) ? $round_info[6] : null
      );
    }

    // Add safety checks
    $round_info['is_triple_elim'] = isset($round_info['is_triple_elim']) ? $round_info['is_triple_elim'] : 0;
    $round_info['elim_type'] = isset($round_info['elim_type']) ? $round_info['elim_type'] : 'preliminary';

    error_log("Round info: " . print_r($round_info, true));

    if (!$round_info) {
      error_log("Round info not found for roundid: " . $roundid);
      return false;
    }

    // Handle finals first
    if ($round_info['is_triple_elim'] && $round_info['elim_type'] === 'final') {
      return handle_final_round($roundid, $round_info);
    }

    // Set number of runs based on elimination type
    if ($round_info['is_triple_elim']) {
      switch ($round_info['elim_type']) {
        case 'preliminary':
          $n_times_per_lane = 3;
          break;
        case 'semifinal':
          $n_times_per_lane = 1;
          break;
      }
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
        $avoid_same_lane
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

// New helper function to handle final round scheduling
// function handle_final_round($roundid, $round_info) {
//   global $db;

//   try {
//     // Get top 3 from semifinals
//     $stmt = $db->prepare(
//       "SELECT racerid 
//        FROM (
//            SELECT racerid, MIN(finishtime) as best_time
//            FROM RaceChart 
//            WHERE roundid = :semifinal_round
//            AND finishtime IS NOT NULL 
//            GROUP BY racerid
//            ORDER BY best_time ASC
//            LIMIT 3
//        ) top_racers"
//     );

//     $stmt->execute([':semifinal_round' => $roundid - 1]);
//     $finalists = $stmt->fetchAll(PDO::FETCH_COLUMN);

//     if (count($finalists) !== 3) {
//       error_log("Error: Final round requires exactly 3 racers");
//       return false;
//     }

//     $db->beginTransaction();

//     // Clear existing race chart
//     $db->exec('DELETE FROM RaceChart WHERE roundid = ' . $roundid);

//     // Create single heat for finals
//     $stmt = $db->prepare(
//       'INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)
//        VALUES(:roundid, 1, :lane, :racerid, :classid)'
//     );

//     foreach ($finalists as $index => $racerid) {
//       $stmt->execute([
//         ':roundid' => $roundid,
//         ':lane' => $index + 1,
//         ':racerid' => $racerid,
//         ':classid' => $round_info['classid']
//       ]);
//     }

//     $db->commit();
//     return true;

//   } catch (Exception $e) {
//     $db->rollBack();
//     error_log("Error scheduling final round: " . $e->getMessage());
//     return false;
//   }
// }

function handle_final_round($roundid, $round_info) {
    global $db;
    
    try {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        $db->beginTransaction();

        // First verify racers exist in racing group
        $stmt = $db->prepare(
            "SELECT ri.racerid 
             FROM RegistrationInfo ri
             INNER JOIN Rounds r ON ri.classid = r.classid
             WHERE r.roundid = :roundid
             AND ri.registered = 1"
        );
        
        $stmt->execute([':roundid' => $roundid]);
        $valid_racers = $stmt->fetchAll(PDO::FETCH_COLUMN);

        if (empty($valid_racers)) {
            throw new Exception("No valid racers found in racing group");
        }

        // Get top 3 racers from semifinals who are in valid racing group
        $stmt = $db->prepare(
            "SELECT rc.racerid, MIN(rc.finishtime) as best_time
             FROM RaceChart rc
             INNER JOIN RegistrationInfo ri ON rc.racerid = ri.racerid 
             WHERE rc.roundid = :semifinal_round
             AND rc.finishtime IS NOT NULL
             AND ri.registered = 1
             AND ri.racerid IN (" . implode(',', $valid_racers) . ")
             GROUP BY rc.racerid
             ORDER BY best_time ASC
             LIMIT 3"
        );

        $stmt->execute([':semifinal_round' => $roundid - 1]);
        $finalists = $stmt->fetchAll(PDO::FETCH_ASSOC);

        if (count($finalists) !== 3) {
            throw new Exception("Final round requires exactly 3 racers from racing group, found " . count($finalists));
        }

        // Clear existing race chart
        $db->exec('DELETE FROM RaceChart WHERE roundid = ' . $roundid);

        // First add finalists to Roster table
        $stmt = $db->prepare('INSERT INTO Roster (roundid, racerid) VALUES (:roundid, :racerid)');
        foreach ($finalists as $racer) {
            $stmt->execute([
                ':roundid' => $roundid,
                ':racerid' => $racer['racerid']
            ]);
        }

        // Create single heat with ordered lanes
        $stmt = $db->prepare(
            'INSERT INTO RaceChart (roundid, heat, lane, racerid, classid) 
             VALUES (:roundid, :heat, :lane, :racerid, :classid)'
        );

        foreach ($finalists as $index => $racer) {
            $stmt->execute([
                ':roundid' => $roundid,
                ':heat' => 1,
                ':lane' => $index + 1,
                ':racerid' => $racer['racerid'],
                ':classid' => $round_info['classid']
            ]);
        }

        // Verify single heat
        $heat_count = $db->query("SELECT COUNT(DISTINCT heat) FROM RaceChart WHERE roundid = " . $roundid)->fetchColumn();
        if ($heat_count !== 1) {
            throw new Exception("Failed to create single heat for finals");
        }

        $db->commit();
        error_log("Successfully scheduled final round with single heat");
        return true;

    } catch (Exception $e) {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        error_log("Error in final round scheduling: " . $e->getMessage());
        return false;
    }
}