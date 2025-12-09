<?php

// Query elimination tournament status for all classes 
// Returns a map of classid -> tournament info

require_once('inc/elimination-config.inc');

if (have_permission(VIEW_RACE_RESULTS_PERMISSION)) {
    global $db;

    $result = array();

    // Get all tournaments from the database
    $stmt = $db->query(
        "SELECT et.classid, et.config_file, et.age_group_key, et.current_round, et.total_rounds, et.active
         FROM EliminationTournaments et
         WHERE et.active = 1"
    );

    if ($stmt) {
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $classid = $row['classid'];

            // Load config to get names
            $config = load_elimination_config($row['config_file']);
            $age_group_name = '';
            if ($config && isset($config['age_groups'][$row['age_group_key']])) {
                $age_group_name = $config['age_groups'][$row['age_group_key']]['name'];
            }

            $result[$classid] = array(
                'tournament_active' => true,
                'current_round' => intval($row['current_round']),
                'total_rounds' => intval($row['total_rounds']),
                'age_group_name' => $age_group_name,
                'config_file' => $row['config_file']
            );
        }
    }

    header('Content-Type: application/json');
    echo json_encode(array(
        'outcome' => array('summary' => 'success'),
        'tournaments' => $result
    ));
    exit;
} else {
    json_not_authorized();
    exit;
}
