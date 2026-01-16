<?php
// action.simulate-race.inc
// Triggers race simulation via Python subprocess
//
// This action is only available when testing mode is enabled in Settings.
// It spawns simulate_racing.py in fast mode to run a single simulated race.

require_once('inc/data.inc');
require_once('inc/authorize.inc');

if (have_permission(SET_UP_PERMISSION)) {
    // Verify testing mode is enabled
    if (!testing_mode_enabled()) {
        json_failure('testing-disabled',
            'Enable Testing Mode in Settings first.');
        return;
    }

    // Verify racing is active
    $now_racing = read_raceinfo('NowRacingState', 0);
    if (!$now_racing) {
        json_failure('not-racing',
            'Turn on Racing mode before simulating.');
        return;
    }

    // Check if simulation already running (prevent spam)
    $last_sim = read_raceinfo('simulation-started', 0);
    if (time() - $last_sim < 8) {
        json_failure('sim-in-progress',
            'Simulation already in progress. Please wait.');
        return;
    }

    // Mark simulation start time
    write_raceinfo('simulation-started', time());

    // Initialize virtual display to staging state (blue LEDs)
    $lane_count = get_lane_count();
    for ($lane = 1; $lane <= $lane_count; $lane++) {
        write_raceinfo("sim-led-lane-$lane", 'blue');
        write_raceinfo("sim-pinny-lane-$lane", '----');
        write_raceinfo("sim-time-lane-$lane", '');
    }

    // Build the simulation command
    // Path assumes standard deployment on Raspberry Pi / Linux server
    $python = '/usr/bin/python3';
    $script = '/var/lib/infra/app/simulate_racing.py';
    $log = '/var/log/derbynet-simulation.log';

    // Validate script exists
    if (!file_exists($script)) {
        // Try alternate location for development/testing
        $alt_script = dirname(__FILE__) . '/../../extras/soapbox/infra/server/simulate_racing.py';
        if (file_exists($alt_script)) {
            $script = $alt_script;
        } else {
            json_failure('script-not-found',
                'Simulation script not found. Check server configuration.');
            return;
        }
    }

    // Fast mode: single race with configured lane count
    // The --fast flag injects times via API after 5s delay
    $cmd = sprintf(
        '%s %s --fast --max-races=1 --lanes=%d >> %s 2>&1 &',
        escapeshellcmd($python),
        escapeshellcmd($script),
        $lane_count,
        escapeshellarg($log)
    );

    // Log the command for debugging
    error_log("Simulate race command: " . $cmd);

    // Execute in background (non-blocking)
    exec($cmd, $output, $return_var);

    json_success();
    json_out('message', 'Simulation started. Results will appear in ~5-7 seconds.');
    json_out('lanes', $lane_count);

} else {
    json_not_authorized();
}
?>
