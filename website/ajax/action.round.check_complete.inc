<?php
require_once('inc/data.inc');
require_once('inc/racing-state.inc');

$roundid = isset($_POST['roundid']) ? $_POST['roundid'] : null;

if (!$roundid) {
    json_failure('missing_params', 'Missing roundid parameter');
    exit();
}

// Get round info to check if it's final round
$round_info = read_single_row(
    'SELECT r.roundid, r.elim_type, r.round 
     FROM Rounds r
     WHERE r.roundid = :roundid',
    [':roundid' => $roundid]
);

// Check if round is completed
$completed = check_round_complete($roundid);

json_out('completed', $completed);
json_success();