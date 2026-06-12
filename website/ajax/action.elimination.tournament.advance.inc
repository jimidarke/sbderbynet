<?php

// Advance elimination tournament to next round
// $_POST['classid'] - Class ID
// $_POST['force'] - Optional: force advancement even if current round not complete

require_once('inc/elimination-config.inc');
require_once('inc/racing-state.inc');
require_once('inc/elimination-advancement.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
    $classid = $_POST['classid'];
    $force = isset($_POST['force']) ? $_POST['force'] : false;
    
    if (!$classid) {
        json_failure('missing_parameter', 'Missing classid parameter');
        return;
    }
    
    // Get tournament state
    $state = get_elimination_tournament_state($classid);
    if (!$state) {
        json_failure('no_tournament', 'No active elimination tournament for this class');
        return;
    }
    
    $current_round = $state['current_round'];
    $total_rounds = $state['total_rounds'];
    
    // Check if we're already at the final round
    if ($current_round >= $total_rounds) {
        json_failure('already_final', 'Tournament is already at the final round');
        return;
    }
    
    // Check if current round is complete (unless forced)
    if (!$force) {
        // Get current round configuration to get the round name
        $current_round_config = $state['age_group']['rounds'][$current_round - 1];
        $current_round_name = $current_round_config['round_name'];
        
        // Check if all heats in current round are completed
        $incomplete_heats = check_round_completion($classid, $current_round_name);
        if ($incomplete_heats > 0) {
            json_failure('round_incomplete', "Current round has {$incomplete_heats} incomplete heats");
            return;
        }
    }
    
    try {
        // Advance tournament
        if (advance_elimination_tournament($classid)) {
            json_success();
            json_out('message', 'Tournament advanced to next round');
            json_out('new_round', $current_round + 1);
        } else {
            json_failure('advance_failed', 'Failed to advance tournament');
        }
    } catch (Exception $e) {
        json_failure('exception', $e->getMessage());
    }
} else {
    json_not_authorized();
}

?>
