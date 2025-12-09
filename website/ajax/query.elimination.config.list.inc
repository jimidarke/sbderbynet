<?php

// Query to get list of available elimination configurations

require_once('inc/elimination-config.inc');

if (have_permission(SET_UP_PERMISSION)) {
    $configs = load_elimination_config_list();
    
    $response = array(
        'outcome' => array('summary' => 'success'),
        'configs' => $configs
    );
    
    header('Content-Type: application/json');
    echo json_encode($response);
    exit;
} else {
    json_not_authorized();
    exit;
}