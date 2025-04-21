<?php

// To control the timer, and optionally the replay application, we
// keep a NowRacingState setting (value 0 or 1) in the database.
//
// NowRacingState 0 aborts any pending timer activity, aborts the
// replay app's recording and refuses any heat results sent from the
// timer.
//
// NowRacingState 1 implements a proper "hands-free racing" mode: upon
// the conclusion of one heat, the next heat becomes current, the
// timer and replay applications are primed for the next heat.  Any
// incoming timer results in this state are recorded, and trigger the
// replay application, before advancing to the next heat.
//
// If an auto heat advance fails (because we just ran the last heat in
// the round), NowRacingState turns off.  Additionally, manually
// changing the current heat turns off NowRacingState.
//
// An attempt to re-enable NowRacingState will be refused if the
// current round has recorded finish times; the operator will have to
// choose "re-run heat" to discard them before NowRacingState can be
// resumed.
//
// NowRacingState is included as the ['now_racing'] element in the
// array returned by get_running_round().

require_once('inc/replay.inc');

require_once('inc/data.inc');

// Check if the racer is registered
// function check_registration_status($roundid) {
//   global $db;

//   $stmt = $db->prepare('SELECT carnumber, registered 
//                        FROM RaceChart 
//                        JOIN RegistrationInfo ON RaceChart.racerid = RegistrationInfo.racerid
//                        WHERE roundid = :roundid 
//                        AND registered = 0');
//   $stmt->execute([':roundid' => $roundid]);

//   $unregistered = [];
//   while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
//       $unregistered[] = $row['carnumber'];
//   }

//   if (!empty($unregistered)) {
//       return [
//           'allowed' => false,
//           'message' => 'Cannot start racing: The following racers are not registered: ' . 
//                       implode(', ', $unregistered)
//       ];
//   }

//   return ['allowed' => true];
// }



function check_registration_status($roundid)
{
  global $db;

  $stmt = $db->prepare('SELECT carnumber, registered 
                       FROM RaceChart 
                       JOIN RegistrationInfo ON RaceChart.racerid = RegistrationInfo.racerid
                       WHERE roundid = :roundid 
                       AND registered = 0');
  $stmt->execute([':roundid' => $roundid]);

  $unregistered = [];
  while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $unregistered[] = $row['carnumber'];
  }

  if (!empty($unregistered)) {
    $message = 'Cannot start racing: The following racers with Pinny Numbers: ' .
      implode(', ', $unregistered) . ' are not registered';

    // Send both failure and notification data
    json_failure('unregistered_racers', $message);
    json_out('registration_status', [
      'status' => 'error',
      'message' => $message,
      'unregistered' => $unregistered
    ]);
    return false;
  }

  // Send success notification
  json_out('registration_status', [
    'status' => 'success',
    'message' => 'All racers are registered'
  ]);
  return true;
}

function racing_state_allowed(&$current)
{
  if (!isset($current['roundid']) || !isset($current['heat'])) {
    return false;
  }
  if ($current['roundid'] == TIMER_TEST_ROUNDID) {
    return true;
  }

  // Triple Elimination rounds
    // Get round info
    $round_info = read_single_row(
      'SELECT r.roundname, r.classid, c.class 
       FROM Rounds r
       JOIN Classes c ON c.classid = r.classid
       WHERE r.roundid = :roundid',
      [':roundid' => $current['roundid']]
  );

  if ($round_info) {
      // Check round type requirements
      $roundname = $round_info['roundname'] ?? null;
      
      if ($roundname) {
          switch ($roundname) {
              case 'Semi-Final':
                  $prelim_complete = check_preliminary_complete($current['roundid'] - 1);
                  if (!$prelim_complete) {
                      write_raceinfo('racing_blocked_reason', 
                          'Cannot start Semi-Finals until Preliminary round is complete');
                      return false;
                  }
                  break;
                  
              case 'Final':
                  $semi_complete = check_round_complete($current['roundid'] - 1);
                  if (!$semi_complete) {
                      write_raceinfo('racing_blocked_reason', 
                          'Cannot start Finals until Semi-Final round is complete');
                      return false;
                  }
                  break;
          }
      }
  }


  // // Check registration status first
  // $registration_check = check_registration_status($current['roundid']);
  // if (!$registration_check['allowed']) {
  //     write_raceinfo('racing_blocked_reason', $registration_check['message']);
  //     return false;
  // }


  // Check registration status first
  if (!check_registration_status($current['roundid'])) {
    return false;
  }

  $finished = read_single_value(
    'SELECT COUNT(*) FROM RaceChart'
    . ' WHERE roundid = :roundid'
    . '  AND  heat = :heat'
    . '  AND  (finishtime IS NOT NULL OR finishplace IS NOT NULL)',
    array(
      ':roundid' => $current['roundid'],
      ':heat' => $current['heat']
    )
  );
  if ($finished > 0) {
    return false;
  }
  $ready = read_single_value(
    'SELECT COUNT(*) FROM RaceChart'
    . ' WHERE roundid = :roundid'
    . '  AND  heat = :heat'
    . '  AND  finishtime IS NULL AND finishplace IS NULL',
    array(
      ':roundid' => $current['roundid'],
      ':heat' => $current['heat']
    )
  );
  if ($ready == 0) {
    return false;
  }

  return true;
}

function check_preliminary_complete($roundid) {
  global $db;
  
  $stmt = $db->prepare(
      "SELECT COUNT(*) as incomplete
       FROM (
           SELECT racerid 
           FROM RaceChart 
           WHERE roundid = :roundid 
           GROUP BY racerid 
           HAVING COUNT(finishtime) < 3
       )"
  );
  $stmt->execute([':roundid' => $roundid]);
  
  return $stmt->fetchColumn() == 0;
}

function check_round_complete($roundid)
{
  global $db;

  $stmt = $db->prepare(
    'SELECT COUNT(*) as total,
              COUNT(finishtime) as finished
       FROM RaceChart 
       WHERE roundid = :roundid'
  );
  $stmt->execute([':roundid' => $roundid]);
  $result = $stmt->fetch(PDO::FETCH_ASSOC);

  return $result['total'] > 0 && $result['total'] == $result['finished'];
}


function advance_round($roundid)
{
  global $db;

  $round_info = read_single_row(
    'SELECT r.roundname, r.classid, c.class 
       FROM Rounds r
       JOIN Classes c ON c.classid = r.classid
       WHERE r.roundid = :roundid',
    [':roundid' => $roundid]
  );

  if (!$round_info) {
    return false;
  }

  switch ($round_info['roundname']) {
    case 'Preliminary':
      // Get top 21 based on average times
      $stmt = $db->prepare(
        "SELECT racerid,
                      AVG(finishtime) as avg_time
               FROM RaceChart 
               WHERE roundid = :roundid
               AND finishtime IS NOT NULL
               GROUP BY racerid
               HAVING COUNT(*) >= 3
               ORDER BY avg_time ASC
               LIMIT 21"
      );
      $stmt->execute([':roundid' => $roundid]);
      $qualifiers = $stmt->fetchAll(PDO::FETCH_COLUMN);

      // Add to next round (Semi-Finals)
      $next_round = $roundid + 1;
      foreach ($qualifiers as $racer) {
        add_to_round($next_round, $racer);
      }
      break;

    case 'Semi-Final':
      // Get top 3 from semifinals
      $stmt = $db->prepare(
        "SELECT racerid
               FROM RaceChart 
               WHERE roundid = :roundid
               AND finishtime IS NOT NULL
               ORDER BY finishtime ASC
               LIMIT 3"
      );
      $stmt->execute([':roundid' => $roundid]);
      $qualifiers = $stmt->fetchAll(PDO::FETCH_COLUMN);

      // Add to finals
      $next_round = $roundid + 1;
      foreach ($qualifiers as $racer) {
        add_to_round($next_round, $racer);
      }
      break;
  }

  return true;
}

function add_to_round($roundid, $racerid)
{
  global $db;

  $stmt = $db->prepare(
    'INSERT INTO Roster (roundid, racerid, classid)
       SELECT :roundid, :racerid, r.classid
       FROM Rounds r
       WHERE r.roundid = :roundid'
  );

  return $stmt->execute([
    ':roundid' => $roundid,
    ':racerid' => $racerid
  ]);
}


function get_racing_state()
{
  return read_raceinfo('NowRacingState', 0) != 0;
}

// Returns FALSE if an attempt to turn on NowRacingState is refused.
// Turning off NowRacingState always succeeds.
function set_racing_state($state)
{
  $state = ($state ? 1 : 0);

  $current = get_running_round();
  if ($state) {
    if (!racing_state_allowed($current)) {
      $reason = read_raceinfo(
        'racing_blocked_reason',
        'Cannot start racing - validation failed'
      );
      write_raceinfo('racing_blocked_reason', ''); // Clear the message
      json_out('error', $reason);
      return false;
    }

    if (!$current['now_racing']) {
      send_replay_START($current);
    }
  } else {
    if ($current['now_racing']) {
      send_replay_CANCEL();
    }
  }

  write_raceinfo('NowRacingState', $state);
  write_raceinfo('refused-results', 0);

  return true;
}

function cancel_running_round()
{
  set_racing_state(0);
  set_current_heat(-1, -1);
  write_raceinfo('ClassID', -1);
}

function maybe_cancel_running_round($roundid)
{
  $now_running = get_running_round();
  if ($roundid == $now_running['roundid']) {
    cancel_running_round();
  }
}

function advance_triple_elimination($roundid) {
    global $db;
    error_log("Starting triple elimination advancement for round: " . $roundid);
    
    try {
        $db->beginTransaction();
        
        // Get current round info
        $round_info = read_single_row(
            'SELECT r.roundid, r.elim_type, r.classid, r.round, r.roundname 
             FROM Rounds r 
             WHERE r.roundid = :roundid',
            [':roundid' => $roundid]
        );

        if (!$round_info) {
            error_log("Error: Round not found: " . $roundid);
            throw new Exception("Round not found: " . $roundid);
        }

        error_log("Processing " . $round_info['roundname'] . " round");

        switch ($round_info['elim_type']) {
            case 'preliminary':
                // Verify all racers completed 3 runs
                $incomplete = read_single_value(
                    "SELECT COUNT(*) FROM (
                        SELECT racerid FROM RaceChart 
                        WHERE roundid = :roundid 
                        GROUP BY racerid 
                        HAVING COUNT(finishtime) < 3
                    )",
                    [':roundid' => $roundid]
                );

                if ($incomplete > 0) {
                    error_log("Error: Preliminary round incomplete - some racers missing runs");
                    throw new Exception("All racers must complete 3 runs before advancing");
                }

                // Get top 27 based on average time
                $stmt = $db->prepare(
                    "SELECT racerid 
                     FROM (
                         SELECT racerid, AVG(finishtime) as avg_time
                         FROM RaceChart 
                         WHERE roundid = :roundid
                         AND finishtime IS NOT NULL
                         GROUP BY racerid
                         HAVING COUNT(*) = 3
                         ORDER BY avg_time ASC
                         LIMIT 27
                     ) qualified"
                );
                $stmt->execute([':roundid' => $roundid]);
                $qualifiers = $stmt->fetchAll(PDO::FETCH_COLUMN);

                error_log("Found " . count($qualifiers) . " qualifiers for semifinals");

                // Get semifinal round
                $semifinal = read_single_row(
                    'SELECT roundid FROM Rounds 
                     WHERE classid = :classid 
                     AND elim_type = :elim_type',
                    [
                        ':classid' => $round_info['classid'],
                        ':elim_type' => 'semifinal'
                    ]
                );

                if (!$semifinal) {
                    error_log("Error: Semifinal round not found");
                    throw new Exception("Semifinal round not found");
                }

                // Clear existing semifinal roster
                $db->exec('DELETE FROM Roster WHERE roundid = ' . $semifinal['roundid']);
                
                // Add qualifiers to semifinal round
                foreach ($qualifiers as $racerid) {
                    add_to_round($semifinal['roundid'], $racerid);
                }

                // Generate semifinal schedule
                $nlanes = read_raceinfo('lane_count', 0);
                if (!schedule_one_round($semifinal['roundid'], $nlanes, 1, false)) {
                    error_log("Error: Failed to generate semifinal schedule");
                    throw new Exception("Failed to generate semifinal schedule");
                }

                error_log("Successfully scheduled semifinal round");
                break;

            case 'semifinal':
                // Get top 9 from semifinals based on single run time
                $stmt = $db->prepare(
                    "SELECT racerid
                     FROM RaceChart 
                     WHERE roundid = :roundid
                     AND finishtime IS NOT NULL
                     ORDER BY finishtime ASC
                     LIMIT 9"
                );
                $stmt->execute([':roundid' => $roundid]);
                $qualifiers = $stmt->fetchAll(PDO::FETCH_COLUMN);

                error_log("Found " . count($qualifiers) . " qualifiers for finals");

                // Get final round
                $final = read_single_row(
                    'SELECT roundid FROM Rounds 
                     WHERE classid = :classid 
                     AND elim_type = :elim_type',
                    [
                        ':classid' => $round_info['classid'],
                        ':elim_type' => 'final'
                    ]
                );

                if (!$final) {
                    error_log("Error: Final round not found");
                    throw new Exception("Final round not found");
                }

                // Clear existing final roster
                $db->exec('DELETE FROM Roster WHERE roundid = ' . $final['roundid']);
                
                // Add qualifiers to final round
                foreach ($qualifiers as $racerid) {
                    add_to_round($final['roundid'], $racerid);
                }

                // Generate final schedule
                $nlanes = read_raceinfo('lane_count', 0);
                if (!schedule_one_round($final['roundid'], $nlanes, 1, false)) {
                    error_log("Error: Failed to generate final schedule");
                    throw new Exception("Failed to generate final schedule");
                }

                error_log("Successfully scheduled final round");
                break;
        }
        
        $db->commit();
        return true;
        
    } catch (Exception $e) {
        $db->rollBack();
        error_log("Error in advance_triple_elimination: " . $e->getMessage());
        throw $e;
    }
}

?>