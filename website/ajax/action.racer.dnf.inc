<?php
// Mark a racer as DNF (Did Not Finish) in the current heat
// Sets their time to 99.999 seconds as requested

require_once('inc/data.inc');
require_once('inc/racing-state.inc');
require_once('inc/events.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
    json_not_authorized();
    exit();
}

$racerid = isset($_POST['racerid']) ? $_POST['racerid'] : null;
$roundid = isset($_POST['roundid']) ? $_POST['roundid'] : null;
$heat = isset($_POST['heat']) ? $_POST['heat'] : null;

if (!$racerid || !$roundid || !$heat) {
    json_failure('missing_params', 'Missing required parameters: racerid, roundid, heat');
    exit();
}

try {
    global $db;
    $db->beginTransaction();

    // Set the racer's time to the DNF sentinel for the specific heat
    $stmt = $db->prepare(
        'UPDATE RaceChart
         SET finishtime = ' . DNF_TIME . ',
             finishplace = 0
         WHERE roundid = :roundid 
         AND racerid = :racerid 
         AND heat = :heat'
    );
    
    $result = $stmt->execute([
        ':roundid' => $roundid,
        ':racerid' => $racerid,
        ':heat' => $heat
    ]);

    if ($result && $stmt->rowCount() > 0) {
        // Record the DNF event
        record_event(EVENT_HEAT_MANUALLY_ENTERED, 
                    ['roundid' => $roundid, 'heat' => $heat, 'racerid' => $racerid, 'action' => 'DNF']);
        
        $db->commit();

        // Result correction (DNF) → refresh the spectator pages promptly.
        request_cloud_push();

        json_success();
    } else {
        $db->rollBack();
        json_failure('no_update', 'No racer found to mark as DNF for the specified heat');
    }

} catch (Exception $e) {
    $db->rollBack();
    error_log("Error marking racer as DNF: " . $e->getMessage());
    json_failure('dnf_failed', 'Failed to mark racer as DNF: ' . $e->getMessage());
}
?>