<?php

// Single source of truth for elimination tournament advancement.
// Used by BOTH the explicit coordinator action
// (ajax/action.elimination.tournament.advance.inc) and the automatic
// round-completion path (inc/racing-state.inc advance_round()).
// Historically three divergent implementations existed (this one, an
// inline copy in advance_round, and a StandingsOracle-based roster
// calculation in playlist.inc) which could disagree on scoring and
// duplicated Roster rows; everything now funnels through here.

require_once('inc/data.inc');
require_once('inc/elimination-config.inc');

/**
 * Check if a round is complete
 * @param int $classid Class ID
 * @param string $round_name Round name (e.g. "1 Preliminary")
 * @return int Number of incomplete heats
 */
function check_round_completion($classid, $round_name) {
    global $db;
    
    $stmt = $db->prepare('SELECT COUNT(*) FROM RaceChart rc
                         INNER JOIN Rounds r ON rc.roundid = r.roundid
                         WHERE r.classid = :classid AND r.roundname = :round_name
                         AND (rc.finishtime IS NULL AND rc.finishplace IS NULL)');
    $stmt->execute(array(':classid' => $classid, ':round_name' => $round_name));
    
    return $stmt->fetchColumn();
}

/**
 * Advance elimination tournament to next round
 * @param int $classid Class ID
 * @return bool Success
 */
function advance_elimination_tournament($classid) {
    global $db;
    
    try {
        $db->beginTransaction();
        
        // Get current tournament state
        $state = get_elimination_tournament_state($classid);
        if (!$state) {
            throw new Exception("No active tournament found");
        }
        
        $current_round = $state['current_round'];
        $next_round = $current_round + 1;
        
        // Get current round configuration
        $current_round_config = $state['age_group']['rounds'][$current_round - 1];
        
        // Calculate advancement based on current round results
        $advancing_racers = calculate_round_advancement($classid, $current_round, $current_round_config);
        
        if (empty($advancing_racers)) {
            throw new Exception("No racers qualified for advancement");
        }
        
        // Update tournament to next round
        $stmt = $db->prepare('UPDATE EliminationTournaments 
                             SET current_round = :next_round 
                             WHERE classid = :classid AND active = 1');
        $stmt->execute(array(':next_round' => $next_round, ':classid' => $classid));
        
        // Record advancement
        record_elimination_advancement($state['tournament']['tournament_id'], 
                                     $current_round, $next_round, $advancing_racers);
        
        // Create roster for next round
        create_next_round_roster($classid, $next_round, $advancing_racers);
        
        $db->commit();
        return true;
        
    } catch (Exception $e) {
        $db->rollBack();
        error_log("Failed to advance elimination tournament: " . $e->getMessage());
        throw $e;
    }
}

/**
 * Calculate which racers advance from current round
 * @param int $classid Class ID
 * @param int $round_number Current round number
 * @param array $round_config Round configuration
 * @return array Array of racerid => score pairs
 */
function calculate_round_advancement($classid, $round_number, $round_config) {
    global $db;
    
    $scoring_method = elimination_effective_scoring_method($round_config);
    $advance_count = intval($round_config['advance_count']);

    // Build query based on scoring method.  DNF runs carry the 99.999
    // sentinel and participate in every aggregate by design (a DNF is a
    // heavy penalty, not a discarded run).
    if ($scoring_method === 'total_time') {
        $select_clause = 'SUM(rc.finishtime) as score';
    } elseif ($scoring_method === 'best_time') {
        $select_clause = 'MIN(rc.finishtime) as score';
    } elseif ($scoring_method === 'average_time') {
        $select_clause = 'AVG(rc.finishtime) as score';
    } elseif ($scoring_method === 'drop_slowest') {
        // Drop the slowest run, average the rest; a single-run racer keeps
        // that time.  Same expression as sql_scoring_expression() scoring=1.
        $select_clause = 'CASE COUNT(*) WHEN 1 THEN MAX(rc.finishtime)'
                       . ' ELSE (SUM(rc.finishtime) - MAX(rc.finishtime)) / (COUNT(*) - 1) END as score';
    } else {
        throw new Exception("Unsupported scoring method: " . $scoring_method);
    }

    if ($advance_count <= 0) {
        return array();
    }

    // Match on roundname (string like "1 Preliminary"), NOT round (integer sequence)
    $round_name = $round_config['round_name'];

    // Fetch the FULL ranking and apply the advancement cut in PHP: every
    // racer whose score ties the last advancing score advances too.  A bare
    // LIMIT would truncate boundary ties nondeterministically.
    // The RegistrationInfo join drops withdrawn racers: pull-forward marks
    // a mid-event dropout by clearing passedinspection, and without this
    // filter a dropout's 1-run total_time aggregate beats every full
    // 3-run total — a withdrawn racer would top the advancement list.
    $stmt = $db->prepare("SELECT rc.racerid, {$select_clause}
                         FROM RaceChart rc
                         INNER JOIN Rounds r ON rc.roundid = r.roundid
                         INNER JOIN RegistrationInfo ri ON ri.racerid = rc.racerid
                         WHERE r.classid = :classid AND r.roundname = :round_name
                         AND rc.finishtime IS NOT NULL AND rc.finishtime > 0
                         AND ri.passedinspection = 1 AND ri.exclude = 0
                         GROUP BY rc.racerid
                         ORDER BY score ASC, rc.racerid ASC");

    $stmt->execute(array(
        ':classid' => $classid,
        ':round_name' => $round_name
    ));

    $results = array();
    $cutoff_score = null;
    $position = 0;
    foreach ($stmt as $row) {
        $position++;
        $score = floatval($row['score']);
        if ($position > $advance_count &&
            ($cutoff_score === null || abs($score - $cutoff_score) > ELIMINATION_SCORE_EPSILON)) {
            break;
        }
        if ($position == $advance_count) {
            $cutoff_score = $score;
        }
        $results[$row['racerid']] = $score;
    }

    return $results;
}

/**
 * Record advancement in database
 * @param int $tournament_id Tournament ID
 * @param int $from_round From round number
 * @param int $to_round To round number  
 * @param array $advancing_racers Racers advancing with scores
 */
function record_elimination_advancement($tournament_id, $from_round, $to_round, $advancing_racers) {
    global $db;
    
    $stmt = $db->prepare('INSERT INTO EliminationAdvancement 
                         (tournament_id, from_round, to_round, racerid, rank_in_round, score, advanced, advanced_at)
                         VALUES (:tournament_id, :from_round, :to_round, :racerid, :rank, :score, 1, datetime("now"))');
    
    // Competition ranking (1,2,2,4): tied scores share a rank, the next
    // distinct score resumes at its ordinal position.
    $rank = 0;
    $position = 0;
    $prev_score = null;
    foreach ($advancing_racers as $racerid => $score) {
        $position++;
        if ($prev_score === null || abs($score - $prev_score) > ELIMINATION_SCORE_EPSILON) {
            $rank = $position;
            $prev_score = $score;
        }
        $stmt->execute(array(
            ':tournament_id' => $tournament_id,
            ':from_round' => $from_round,
            ':to_round' => $to_round,
            ':racerid' => $racerid,
            ':rank' => $rank,
            ':score' => $score
        ));
    }
}

/**
 * Create roster for next round
 * @param int $classid Class ID
 * @param int $next_round_number Next round number
 * @param array $advancing_racers Advancing racers
 */
function create_next_round_roster($classid, $next_round_number, $advancing_racers) {
    global $db;
    
    // Get tournament state to get the round name for the next round
    $state = get_elimination_tournament_state($classid);
    if (!$state) {
        throw new Exception("No active tournament found");
    }
    
    // Get next round configuration to get the round name
    $next_round_config = $state['age_group']['rounds'][$next_round_number - 1];
    $next_round_name = $next_round_config['round_name'];
    
    // Get next round ID using the round name
    $roundid = read_single_value('SELECT roundid FROM Rounds
                                 WHERE classid = :classid AND roundname = :round_name',
                                array(':classid' => $classid, ':round_name' => $next_round_name));
    
    if (!$roundid) {
        throw new Exception("Next round not found in database: {$next_round_name}");
    }
    
    // Clear existing roster for this round
    $db->prepare('DELETE FROM Roster WHERE roundid = :roundid')
       ->execute(array(':roundid' => $roundid));
    
    // Add advancing racers to roster
    $stmt = $db->prepare('INSERT INTO Roster (roundid, racerid) VALUES (:roundid, :racerid)');
    foreach (array_keys($advancing_racers) as $racerid) {
        $stmt->execute(array(':roundid' => $roundid, ':racerid' => $racerid));
    }
}

?>
