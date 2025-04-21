<?php

require_once('inc/standings.inc');
require_once('inc/events.inc');

function make_new_round($classid, $roundno) {
  global $db;
  $stmt = $db->prepare('INSERT INTO Rounds(classid, round, phase, charttype)'
                       .' VALUES(:classid, :roundno, 0, 0)');
  $stmt->execute(array(':classid' => $classid,
                       ':roundno' => $roundno));
  $roundid = read_single_value('SELECT roundid FROM Rounds'
                               .' WHERE round = :roundno'
                               .'  AND classid = :classid',
                               array(':classid' => $classid,
                                     ':roundno' => $roundno));
  record_action(array('action' => 'round.*create',
                      'roundid' => $roundid,
                      'classid' => $classid,
                      'round' => $roundno));
  record_event(EVENT_ROUND_ADDED, array('roundid' => $roundid,
                                        'classid' => $classid,
                                        'other' => 'round '.$roundno));
  return $roundid;
}

function create_triple_elimination_rounds($classid) {
  global $db;
  
  try {
      $db->beginTransaction();
      
      // Ensure required columns exist
      // $db->exec('ALTER TABLE Rounds ADD COLUMN IF NOT EXISTS is_triple_elim BOOLEAN DEFAULT 0');
      // $db->exec('ALTER TABLE Rounds ADD COLUMN IF NOT EXISTS elim_type VARCHAR(20)');
      
      // Define round configurations
      $rounds = [
          [
              'round' => 1,
              'name' => 'Preliminary Round',
              'type' => 'preliminary',
              'runs' => 3
          ],
          [
              'round' => 2,
              'name' => 'Semi-Final Round', 
              'type' => 'semifinal',
              'runs' => 1
          ],
          [
              'round' => 3,
              'name' => 'Final Round',
              'type' => 'final',
              'runs' => 1
          ]
      ];
      
      $roundids = [];
      
      foreach ($rounds as $round) {
          $stmt = $db->prepare(
              'INSERT INTO Rounds (
                  classid,
                  round,
                  roundname,
                  is_triple_elim,
                  elim_type
              ) VALUES (
                  :classid,
                  :round,
                  :roundname,
                  1,
                  :elim_type
              )'
          );
          
          $stmt->execute([
              ':classid' => $classid,
              ':round' => $round['round'],
              ':roundname' => $round['name'],
              ':elim_type' => $round['type']
          ]);
          
          $roundid = $db->lastInsertId();
          write_raceinfo("round_{$roundid}_runs", $round['runs']);
          $roundids[] = $roundid;
      }
      
      $db->commit();
      return $roundids;
      
  } catch (Exception $e) {
      $db->rollBack();
      error_log("Error creating triple elimination rounds: " . $e->getMessage());
      throw $e;
  }
}

function verify_triple_elimination_rounds($classid) {
    global $db;
    
    $rounds = $db->query(
        "SELECT roundid, round, roundname 
         FROM Rounds 
         WHERE classid = {$classid} 
         ORDER BY round"
    )->fetchAll(PDO::FETCH_ASSOC);
    
    $expected_rounds = ['Preliminary Round', 'Semi-Final Round', 'Final Round'];
    
    if (count($rounds) !== 3) {
        error_log("Missing rounds for class {$classid}. Found " . count($rounds) . " rounds.");
        return false;
    }
    
    foreach ($rounds as $i => $round) {
        if ($round['roundname'] !== $expected_rounds[$i]) {
            error_log("Incorrect round name for class {$classid}, round {$round['round']}: 
                      Expected {$expected_rounds[$i]}, got {$round['roundname']}");
            return false;
        }
    }
    
    return true;
}

function calculate_roster_from_classes($classids, $bucketed, $bucket_limit) {
  $standings = new StandingsOracle();

  $bucket_keys = array();
  foreach ($classids as $cl) {
    $bucket_keys[] = $standings->class_key($cl);
  }

  return calculate_roster_from_keys($bucket_keys, $bucketed ? 1 : 0, $bucket_limit, $standings);
}

function calculate_roster_from_subgroups($rankids, $bucketed, $bucket_limit) {
  $standings = new StandingsOracle();

  $bucket_keys = array();
  foreach ($rankids as $rankid) {
    $bucket_keys[] = $standings->rank_key($rankid);
  }

  return calculate_roster_from_keys($bucket_keys, $bucketed ? 1 : 0, $bucket_limit, $standings);
}

// For a follow-on round to an existing racing round ("organic" roster), 
// $roundid must be the highest-numbered round for a class that has racing rounds
function calculate_roster_follow_on_round($classid, $bucketed, $bucket_limit) {
  global $db;

  if (!$bucketed) {
    return calculate_roster_from_classes(array($classid), $bucketed, $bucket_limit);
  }
  
  $stmt = $db->prepare('SELECT rankid FROM Ranks WHERE classid = :classid');
  $stmt->execute(array(':classid' => $classid));
  $rankids = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);

  return calculate_roster_from_subgroups($rankids, $bucketed, $bucket_limit);
}


// $bucket_keys: An array of standings key symbols
// $bucket_multiplier is 0 for no bucketing (take top overall), or 1 for bucketing by key
// $bucket_limit: How many racers per bucket.  May be exceeded for ties within a bucket.
// $standings: A StandingsOracle instance
function calculate_roster_from_keys($bucket_keys, $bucket_multiplier, $bucket_limit, &$standings) {
    global $db;
    error_log("Starting roster calculation with " . count($bucket_keys) . " bucket keys and limit " . $bucket_limit);

    // Initialize buckets array
    $buckets = array_fill(0, $bucket_multiplier ? count($bucket_keys) : 1, array());

    // For non-bucketed mode, use a single bucket
    if ($bucket_multiplier == 0) {
        error_log("Using single bucket mode (no bucketing)");
        $bucket_keys = array($bucket_keys[0]); // Just use first key
    }

    // Sort results by score (ascending for time-based, lower is better)
    usort($standings->result_summary, function($a, $b) {
        return $a['score'] <=> $b['score'];
    });

    // Track processed racers to avoid duplicates
    $processed_racers = array();

    // If bucket_limit is 0, include all racers
    if ($bucket_limit == 0) {
        $bucket_limit = count($standings->result_summary);
        error_log("No bucket limit specified, using all racers: " . $bucket_limit);
    }

    foreach ($standings->result_summary as &$row) {
        // Skip if already processed this racer
        if (in_array($row['racerid'], $processed_racers)) {
            continue;
        }

        error_log("Processing racer {$row['racerid']} with score {$row['score']}");
        
        foreach ($row['outcome'] as $key => $place) {
            $bucketno = array_search($key, $bucket_keys);
            if ($bucketno !== false) {
                $bucket_index = $bucket_multiplier ? $bucketno : 0;
                
                // Add racer if:
                // 1. Bucket is under limit OR
                // 2. Racer is tied with last place in bucket
                $current_bucket = &$buckets[$bucket_index];
                if (count($current_bucket) < $bucket_limit || 
                    (count($current_bucket) > 0 && end($current_bucket)['score'] == $row['score'])) {
                    
                    $current_bucket[] = array(
                        'racerid' => $row['racerid'],
                        'score' => $row['score']
                    );
                    $processed_racers[] = $row['racerid'];
                    error_log("Added racer {$row['racerid']} to bucket {$bucket_index} (count: " . count($current_bucket) . ")");
                } else {
                    error_log("Skipping racer {$row['racerid']} - bucket {$bucket_index} full");
                }
                break; // Once added to a bucket, move to next racer
            }
        }
    }

    // Combine all buckets into finalists array
    $finalists = array();
    foreach ($buckets as $bucket_number => $bucket) {
        error_log("Processing bucket {$bucket_number} with " . count($bucket) . " racers");
        foreach ($bucket as $racer) {
            $finalists[] = array(
                'racerid' => intval($racer['racerid']),
                'score' => floatval($racer['score'])
            );
        }
    }

    error_log("Final roster contains " . count($finalists) . " racers");
    
    return $finalists;
}

function write_roster_entries($new_roundid, $classid, &$finalists) {
  global $db;
  $stmt = $db->prepare('INSERT INTO Roster(roundid, classid, racerid)'
                       .' VALUES(:roundid, :classid, :racerid)');
  foreach ($finalists as $racer) {
    $stmt->execute(array(':roundid' => $new_roundid,
                         ':classid' => $classid,
                         ':racerid' => $racer['racerid']));
  }
}

function add_to_round($roundid, $racerid) {
    global $db;
    
    // Get the round info first
    $round_info = read_single_row(
        'SELECT r.roundid, r.classid, r.elim_type 
         FROM Rounds r
         WHERE r.roundid = :roundid',
        [':roundid' => $roundid],
        PDO::FETCH_ASSOC
    );

    if (!$round_info) {
        error_log("Cannot add racer to round - round not found: " . $roundid);
        return false;
    }

    try {
        // Add racer to roster with proper classid from rounds table
        $stmt = $db->prepare(
            'INSERT INTO Roster (roundid, racerid, classid)
             VALUES (:roundid, :racerid, :classid)'
        );
        
        $stmt->execute([
            ':roundid' => $roundid,
            ':racerid' => $racerid,
            ':classid' => $round_info['classid']
        ]);

        error_log("Added racer {$racerid} to round {$roundid} for class {$round_info['classid']}");
        return true;
    } catch (Exception $e) {
        error_log("Error adding racer to round: " . $e->getMessage());
        return false;
    }
}

?>
