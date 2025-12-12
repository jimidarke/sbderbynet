<?php
require_once('inc/scenes.inc');
require_once('inc/roster.inc');
require_once('inc/schedule_one_round.inc');
require_once('inc/autoadvance.inc');
require_once('inc/rounds.inc');

function create_playlist_table()
{
  create_scene_tables();
  run_sql_script('playlist-table');
}

function first_playlist_entry()
{
  try {
    return read_single_row(
      'SELECT roundid, Playlist.*'
      . ' FROM Playlist LEFT OUTER JOIN Rounds'
      . '   USING (classid, round)'
      . ' WHERE ('
      . '   roundid IS NULL'
      . '   OR'
      . '   NOT EXISTS(SELECT 1 FROM RaceChart'
      . '              WHERE roundid = Rounds.roundid)'
      . '   OR'
      . '   EXISTS(SELECT 1 FROM RaceChart'
      . '          WHERE roundid = Rounds.roundid'
      . '            AND finishtime IS NULL AND finishplace IS NULL)'
      . '       )'
      . ' ORDER BY seq',
      array(),
      PDO::FETCH_ASSOC
    );
  } catch (PDOException $p) {
    if (is_no_such_table_exception($p)) {
      create_playlist_table();
      return array();
    } else {
      echo "SQL error code " . $p->getCode() . "\n";
      echo $p;
    }
  }
}

function playlist_entry_for($roundid)
{
  try {
    return read_single_row(
      'SELECT * FROM Playlist'
      . ' INNER JOIN Rounds USING (classid, round)'
      . ' WHERE roundid = :roundid',
      array(':roundid' => $roundid),
      PDO::FETCH_ASSOC
    );
  } catch (PDOException $p) {
    if (is_no_such_table_exception($p)) {
      create_playlist_table();
      return array();
    } else {
      echo "SQL error code " . $p->getCode() . "\n";
      echo $p;
    }
  }
}

// Finds the next queue entry after the given one.
function playlist_entry_after($seq)
{
  return read_single_row(
    'SELECT * FROM Playlist'
    . ' WHERE seq = (SELECT MIN(seq) FROM Playlist'
    . '              WHERE seq > :seq)',
    array(':seq' => $seq),
    PDO::FETCH_ASSOC
  );
}

// Returns true if there are no scheduled heats for this round without results.
// Note that it returns true if there are just no scheduled heats at all.
function round_is_completed($roundid)
{
  return read_single_value(
    'SELECT COUNT(*) FROM RaceChart'
    . ' WHERE roundid = :roundid'
    . '  AND (completed IS NULL OR completed = \'\')',
    array(':roundid' => $roundid)
  ) == 0;
}

// Returns false, and emits <failure>, if unable to activate the queue entry
function activate_playlist_entry(&$playlist_entry)
{
  global $db;
  $roundid = read_single_value(
    'SELECT roundid FROM Rounds'
    . ' WHERE classid = :classid AND round = :round',
    array(
      ':classid' => $playlist_entry['classid'],
      ':round' => $playlist_entry['round']
    )
  );
  if (!$roundid) {
    $roundid = make_new_round($playlist_entry['classid'], $playlist_entry['round']);
  }
  if (
    read_single_value(
      'SELECT COUNT(*) FROM Roster WHERE roundid = :roundid',
      array(':roundid' => $roundid)
    ) == 0
  ) {
    if ($playlist_entry['round'] == 1) {
      list($constituents, $rankids) =
        read_single_row(
          'SELECT constituents, rankids FROM Classes'
          . ' WHERE classid = :classid',
          array(':classid' => $playlist_entry['classid'])
        );
      if (empty($rankids)) {
        $finalists = calculate_roster_from_classes(
          explode(',', $constituents),
          $playlist_entry['bucketed'],
          $playlist_entry['bucket_limit']
        );
      } else {
        $finalists = calculate_roster_from_subgroups(
          explode(',', $rankids),
          $playlist_entry['bucketed'],
          $playlist_entry['bucket_limit']
        );
      }
    } else {
      $finalists = calculate_roster_follow_on_round(
        $playlist_entry['classid'],
        $playlist_entry['bucketed'],
        $playlist_entry['bucket_limit']
      );
    }
    json_out('finalists', $finalists);
    write_roster_entries($roundid, $playlist_entry['classid'], $finalists);
  }
  if (
    $playlist_entry['n_times_per_lane'] > 0 &&
    read_single_value(
      'SELECT COUNT(*) FROM RaceChart'
      . ' WHERE roundid = :roundid',
      array(':roundid' => $roundid)
    ) == 0
  ) {
    $nlanes = get_lane_count();
    if ($nlanes > 0) {
      schedule_one_round($roundid, $nlanes, $playlist_entry['n_times_per_lane'], /* trace */ false);
    }
  }

  $current = get_running_round();
  $current['roundid'] = $roundid;
  $heat = read_single_value(
    'SELECT MIN(heat) FROM RaceChart'
    . ' WHERE roundid = :roundid'
    . '  AND (completed IS NULL OR completed = \'\')',
    array(':roundid' => $roundid)
  );
  return advance_heat($current, $heat, /* report_failure */ true);
}

/* When racing ends, at the completion of a round (all heats have been run), if
  the current head of Playlist matches the just-ending roundid, then:
  - Activate the next queue entry (generate the schedule if need be, set the current round).
  - If sceneid_at_finish, then set that, otherwise
  - if continue_racing_at_end, then set racing on (it was just turned off), otherwise
  - do nothing (leave racing off)
*/
function perform_playlist_after_round($roundid) {
    global $db;

    if (use_master_sched()) {
        return;
    }

    // Get current round info
    $round_info = read_single_row(
        'SELECT r.roundid, r.classid, r.round, r.roundname,
                c.class as den_name
         FROM Rounds r
         JOIN Classes c ON c.classid = r.classid
         WHERE r.roundid = :roundid',
        [':roundid' => $roundid],
        PDO::FETCH_ASSOC
    );

    error_log("Round info retrieved: " . json_encode($round_info));

    if (!$round_info) {
        error_log("Round not found: " . $roundid);
        return;
    }

    if (round_is_completed($roundid)) {
        error_log("Round {$round_info['roundname']} is complete, advancing...");

        // Get advancement limit from elimination tournament JSON configuration
        require_once('inc/elimination-config.inc');
        $bucket_limit = 3; // Default fallback
        $n_times_per_lane = 1; // Default for elimination rounds

        $elimination_state = get_elimination_tournament_state($round_info['classid']);
        if ($elimination_state) {
            // Find the current round's configuration by round name
            $rounds_config = $elimination_state['age_group']['rounds'];
            $current_round_config = null;

            foreach ($rounds_config as $config) {
                if ($config['round_name'] == $round_info['roundname']) {
                    $current_round_config = $config;
                    break;
                }
            }

            if ($current_round_config) {
                // Use advance_count from JSON configuration
                $bucket_limit = $current_round_config['advance_count'];
                error_log("Using elimination tournament config: advance_count={$bucket_limit} for round '{$round_info['roundname']}'");

                // Get next round's races_per_racer for scheduling
                $next_round_sequence = $current_round_config['round_sequence'] + 1;
                foreach ($rounds_config as $config) {
                    if ($config['round_sequence'] == $next_round_sequence) {
                        $n_times_per_lane = ($config['races_per_racer'] == 3) ? 1 : 0;
                        error_log("Next round races_per_racer={$config['races_per_racer']}, n_times_per_lane={$n_times_per_lane}");
                        break;
                    }
                }
            } else {
                error_log("No elimination config found for round '{$round_info['roundname']}', using default bucket_limit=3");
            }
        } else {
            error_log("No active elimination tournament for classid={$round_info['classid']}, using default bucket_limit=3");
        }

        // Get the next round information
        $next_round = read_single_row(
            'SELECT roundid
             FROM Rounds
             WHERE classid = :classid
             AND round = :next_round',
            [
                ':classid' => $round_info['classid'],
                ':next_round' => ($round_info['round'] + 1)
            ],
            PDO::FETCH_ASSOC
        );

        if (!$next_round) {
            error_log("No next round found for classid {$round_info['classid']}, current round {$round_info['round']}");
            return;
        }

        error_log("Found next round: " . json_encode($next_round));

        try {
            // Begin transaction
            $db->beginTransaction();

            // Create playlist entry for next round
            $stmt = $db->prepare(
                'INSERT INTO Playlist (
                    classid, round, n_times_per_lane, continue_racing,
                    seq, bucketed, bucket_limit
                ) VALUES (
                    :classid,
                    :round,
                    :n_times_per_lane,
                    1,
                    (SELECT COALESCE(MAX(seq), 0) + 1 FROM Playlist),
                    0,
                    :bucket_limit
                )'
            );

            $stmt->execute([
                ':classid' => $round_info['classid'],
                ':round' => $round_info['round'] + 1,
                ':n_times_per_lane' => $n_times_per_lane,
                ':bucket_limit' => $bucket_limit
            ]);

            error_log("Created playlist entry for next round with bucket_limit={$bucket_limit}");

            // Initialize standings
            $standings = new StandingsOracle();
            $bucket_keys = array(stkey_round($roundid));

            // Calculate roster using advance_count from JSON configuration
            $finalists = calculate_roster_from_keys(
                $bucket_keys,
                0,  // No bucketing
                $bucket_limit,
                $standings
            );

            error_log("Calculated " . count($finalists) . " finalists with bucket_limit={$bucket_limit}");

            // Add racers to next round's roster
            if (!empty($finalists)) {
                foreach ($finalists as $finalist) {
                    add_to_round($next_round['roundid'], $finalist['racerid']);
                }
                error_log("Added " . count($finalists) . " racers to next round");
            }

            // Activate the next round
            $entry = playlist_entry_for($next_round['roundid']);
            if ($entry) {
                error_log("Activating next round: " . $next_round['roundid']);
                activate_playlist_entry($entry);
            }

            // Commit transaction
            $db->commit();

        } catch (Exception $e) {
            $db->rollBack();
            error_log("Error in playlist advancement: " . $e->getMessage());
        }
    }
}
?>