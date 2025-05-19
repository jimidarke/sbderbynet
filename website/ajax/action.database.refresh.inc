<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');

header('Content-Type: application/json');

try {
    // Get current connection info
    $connInfo = get_active_connection_info();
    
    // Get settings from current database
    $settings = [
        'test-mode' => read_raceinfo('test-mode', 0),
        'name-style' => read_name_style(),
        'scoring' => read_raceinfo('scoring', 0),
        'heat-counts' => read_raceinfo('heat-counts'),
        'avoid-consecutive' => read_raceinfo('avoid-consecutive'),
        'group-weighted-cars' => read_raceinfo('group-weighted-cars'),
        'avoid-same-lane' => read_raceinfo('avoid-same-lane'),
        'weight-units' => read_raceinfo('weight-units'),
        // Add other settings you need to refresh
    ];

    // Return combined data
    echo json_encode([
        'status' => 'success',
        'connection' => $connInfo,
        'settings' => $settings
    ]);
    
} catch (Exception $e) {
    echo json_encode([
        'status' => 'error',
        'message' => $e->getMessage()
    ]);
}