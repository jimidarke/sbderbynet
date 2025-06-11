<?php

// Query elimination tournament status for a class
// $_GET['classid'] - Class ID to check

require_once('inc/elimination-config.inc');

if (have_permission(VIEW_RACE_RESULTS_PERMISSION)) {
    $classid = $_GET['classid'] ?? null;
    
    if (!$classid) {
        header('Content-Type: application/json');
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 'description' => 'Missing classid parameter')
        ));
        exit;
    }
    
    $tournament_info = get_elimination_tournament_info($classid);
    
    header('Content-Type: application/json');
    if ($tournament_info) {
        echo json_encode(array(
            'outcome' => array('summary' => 'success'),
            'tournament' => $tournament_info,
            'active' => true
        ));
    } else {
        echo json_encode(array(
            'outcome' => array('summary' => 'success'),
            'active' => false,
            'message' => 'No active elimination tournament for this class'
        ));
    }
    exit;
} else {
    json_not_authorized();
    exit;
}