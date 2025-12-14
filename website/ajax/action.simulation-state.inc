<?php
// action.simulation-state.inc
// Receives virtual display state updates from simulate_racing.py
//
// This endpoint allows the Python simulation script to update the virtual
// timer display (LED colors, pinny values, time displays) shown on the
// coordinator page during testing mode.

require_once('inc/data.inc');
require_once('inc/authorize.inc');

// Allow unauthenticated updates from localhost only (for simulation script)
$is_local = in_array($_SERVER['REMOTE_ADDR'], ['127.0.0.1', '::1']);

if ($is_local || have_permission(TIMER_MESSAGE_PERMISSION)) {
    // Only process updates when testing mode is enabled
    if (!testing_mode_enabled()) {
        json_failure('testing-disabled', 'Testing mode not enabled');
        return;
    }

    $updates_made = 0;

    // Update LED states (JSON: {"1": "red", "2": "green", "3": "blue"})
    if (isset($_POST['led'])) {
        $led = json_decode($_POST['led'], true);
        if (is_array($led)) {
            foreach ($led as $lane => $color) {
                // Validate color is one of the allowed values
                $valid_colors = ['red', 'green', 'blue', 'yellow', 'purple', 'white'];
                if (in_array($color, $valid_colors)) {
                    write_raceinfo("sim-led-lane-$lane", $color);
                    $updates_made++;
                }
            }
        }
    }

    // Update pinny displays (JSON: {"1": "0042", "2": "0015", "3": "----"})
    if (isset($_POST['pinny'])) {
        $pinny = json_decode($_POST['pinny'], true);
        if (is_array($pinny)) {
            foreach ($pinny as $lane => $value) {
                // Sanitize to max 4 characters
                $value = substr(strval($value), 0, 4);
                write_raceinfo("sim-pinny-lane-$lane", $value);
                $updates_made++;
            }
        }
    }

    // Update time displays (JSON: {"1": "3.245", "2": "3.512", "3": ""})
    if (isset($_POST['time'])) {
        $times = json_decode($_POST['time'], true);
        if (is_array($times)) {
            foreach ($times as $lane => $t) {
                write_raceinfo("sim-time-lane-$lane", strval($t));
                $updates_made++;
            }
        }
    }

    // Update simulation status message
    if (isset($_POST['status'])) {
        write_raceinfo('simulation-status', $_POST['status']);
        $updates_made++;
    }

    json_success();
    json_out('updates', $updates_made);

} else {
    json_not_authorized();
}
?>
