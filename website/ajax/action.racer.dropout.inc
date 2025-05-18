<?php
require_once('inc/data.inc');
require_once('inc/racing-state.inc'); 
// require_once('inc/error-logging.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
    json_not_authorized();
    exit();
}


// error_log("AJAX: racer.dropout: ".$_POST['racerid'].
//     " round: ".$_POST['roundid']);
$racerid = isset($_POST['racerid']) ? $_POST['racerid'] : null;
$roundid = isset($_POST['roundid']) ? $_POST['roundid'] : null;

if (!$racerid || !$roundid) {
    json_failure('missing_params', 'Missing required parameters');
    exit();
}

if (handle_racer_dropout($racerid, $roundid)) {
    json_success();
} else {
    json_failure('dropout_failed', 'Failed to process racer dropout');
}