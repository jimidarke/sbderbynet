<?php

// Initialize elimination tournament for a class
// $_POST['classid'] - Class ID to initialize tournament for
// $_POST['config_file'] - Configuration file to use

require_once('inc/elimination-config.inc');

if (have_permission(SET_UP_PERMISSION)) {
    $classid = $_POST['classid'];
    $config_file = $_POST['config_file'];
    $age_group_key = $_POST['age_group_key'] ?? null;  // NEW: Explicit age group selection

    if (!$classid || !$config_file) {
        header('Content-Type: application/json');
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 'description' => 'Missing required parameters')
        ));
        exit;
    }
    
    // Check if class exists
    $class_name = read_single_value('SELECT class FROM Classes WHERE classid = :classid', 
                                   array(':classid' => $classid));
    if (!$class_name) {
        header('Content-Type: application/json');
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 'description' => 'Class not found')
        ));
        exit;
    }
    
    // Check if elimination tournament already exists
    if (is_elimination_tournament_active($classid)) {
        header('Content-Type: application/json');
        echo json_encode(array(
            'outcome' => array('summary' => 'error', 
                             'description' => 'Elimination tournament already active for this class')
        ));
        exit;
    }
    
    // Initialize tournament
    header('Content-Type: application/json');
    if (initialize_elimination_tournament($classid, $config_file, $age_group_key)) {
        echo json_encode(array(
            'outcome' => array('summary' => 'success'),
            'message' => 'Elimination tournament initialized for ' . $class_name
        ));
    } else {
        echo json_encode(array(
            'outcome' => array('summary' => 'error',
                             'description' => 'Failed to initialize elimination tournament. Check that class name matches an age group pattern, or specify age_group_key explicitly.')
        ));
    }
    exit;
} else {
    json_not_authorized();
    exit;
}

?>