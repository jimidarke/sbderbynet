<?php

// Advance elimination tournament to next round
// $_POST['classid'] - Class ID
// $_POST['force'] - Optional: force advancement even if current round not complete

require_once('inc/elimination-config.inc');
require_once('inc/racing-state.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
    $classid = $_POST['classid'];
    $force = isset($_POST['force']) ? $_POST['force'] : false;
    
    if (!$classid) {
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 'description' => 'Missing classid parameter')
        ));
        exit;
    }
    
    // Get tournament state
    $state = get_elimination_tournament_state($classid);
    if (!$state) {
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 
                             'description' => 'No active elimination tournament for this class')
        ));
        exit;
    }
    
    $current_round = $state['current_round'];
    $total_rounds = $state['total_rounds'];
    
    // Check if we're already at the final round
    if ($current_round >= $total_rounds) {
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 
                             'description' => 'Tournament is already at the final round')
        ));
        exit;
    }
    
    // TODO: Check if current round is complete (unless forced)
    if (!$force) {
        // Check if all heats in current round are completed
        $incomplete_heats = check_round_completion($classid, $current_round);
        if ($incomplete_heats > 0) {
            echo json_encode(array(
                'outcome' => array('summary' => 'error', 
                                 'description' => "Current round has {$incomplete_heats} incomplete heats")
            ));
            exit;
        }
    }
    
    try {
        // Advance tournament
        if (advance_elimination_tournament($classid)) {
            echo json_encode(array(
                'outcome' => array('summary' => 'success'),
                'message' => 'Tournament advanced to next round',
                'new_round' => $current_round + 1
            ));
        } else {
            echo json_encode(array(
                'outcome' => array('summary' => 'error', 
                                 'description' => 'Failed to advance tournament')
            ));
        }
    } catch (Exception $e) {
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 'description' => $e->getMessage())
        ));
    }
} else {
    json_not_authorized();
}

/**
 * Check if a round is complete
 * @param int $classid Class ID
 * @param int $round_number Round number
 * @return int Number of incomplete heats
 */
function check_round_completion($classid, $round_number) {
    global $db;
    
    $stmt = $db->prepare('SELECT COUNT(*) FROM RaceChart rc
                         INNER JOIN Rounds r ON rc.roundid = r.roundid
                         WHERE r.classid = :classid AND r.round = :round_number
                         AND (rc.finishtime IS NULL AND rc.finishplace IS NULL)');
    $stmt->execute(array(':classid' => $classid, ':round_number' => $round_number));
    
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
    
    $scoring_method = $round_config['scoring_method'];
    $advance_count = $round_config['advance_count'];
    
    // Build query based on scoring method
    if ($scoring_method === 'total_time') {
        $select_clause = 'SUM(rc.finishtime) as score';
        $order_clause = 'score ASC';
    } elseif ($scoring_method === 'best_time') {
        $select_clause = 'MIN(rc.finishtime) as score';
        $order_clause = 'score ASC';
    } elseif ($scoring_method === 'average_time') {
        $select_clause = 'AVG(rc.finishtime) as score';
        $order_clause = 'score ASC';
    } else {
        throw new Exception("Unsupported scoring method: " . $scoring_method);
    }
    
    $stmt = $db->prepare("SELECT rc.racerid, {$select_clause}
                         FROM RaceChart rc
                         INNER JOIN Rounds r ON rc.roundid = r.roundid
                         WHERE r.classid = :classid AND r.round = :round_number
                         AND rc.finishtime IS NOT NULL AND rc.finishtime > 0
                         GROUP BY rc.racerid
                         ORDER BY {$order_clause}
                         LIMIT :limit");
    
    $stmt->execute(array(
        ':classid' => $classid,
        ':round_number' => $round_number,
        ':limit' => $advance_count
    ));
    
    $results = array();
    foreach ($stmt as $row) {
        $results[$row['racerid']] = $row['score'];
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
    
    $rank = 1;
    foreach ($advancing_racers as $racerid => $score) {
        $stmt->execute(array(
            ':tournament_id' => $tournament_id,
            ':from_round' => $from_round,
            ':to_round' => $to_round,
            ':racerid' => $racerid,
            ':rank' => $rank,
            ':score' => $score
        ));
        $rank++;
    }
}

/**
 * Create roster for next round
 * @param int $classid Class ID
 * @param int $round_number Next round number
 * @param array $advancing_racers Advancing racers
 */
function create_next_round_roster($classid, $round_number, $advancing_racers) {
    global $db;
    
    // Get next round ID
    $roundid = read_single_value('SELECT roundid FROM Rounds 
                                 WHERE classid = :classid AND round = :round_number',
                                array(':classid' => $classid, ':round_number' => $round_number));
    
    if (!$roundid) {
        throw new Exception("Next round not found in database");
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