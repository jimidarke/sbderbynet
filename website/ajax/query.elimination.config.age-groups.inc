<?php

/**
 * Query endpoint to retrieve age groups from a configuration file
 *
 * GET parameters:
 *   config_file - Configuration filename to load
 *   classid - (Optional) Class ID to suggest best match
 *
 * Returns:
 *   - outcome: success/failure
 *   - age_groups: Array of age group information
 *   - suggested_key: (if classid provided) Suggested age group key based on pattern
 */

require_once('inc/elimination-config.inc');

if (have_permission(SET_UP_PERMISSION)) {
    $config_file = $_GET['config_file'] ?? null;
    $classid = $_GET['classid'] ?? null;

    if (!$config_file) {
        json_failure('missing-config-file', 'Configuration file parameter is required');
        return;
    }

    // Validate filename (security check)
    if (strpos($config_file, '..') !== false || strpos($config_file, '/') !== false) {
        json_failure('invalid-filename', 'Invalid configuration filename');
        return;
    }

    // Load configuration from file
    $config = load_elimination_config($config_file);
    if (!$config) {
        json_failure('load-failed', 'Failed to load configuration file: ' . $config_file);
        return;
    }

    // Extract age groups with relevant information
    $age_groups = array();
    $suggested_key = null;
    $class_name = null;

    // Get class name if classid provided
    if ($classid) {
        $class_name = read_single_value('SELECT class FROM Classes WHERE classid = :classid',
                                       array(':classid' => $classid));
    }

    foreach ($config['age_groups'] as $group_key => $group) {
        $age_group_info = array(
            'key' => $group_key,
            'name' => $group['name'],
            'pattern' => $group['class_name_pattern'],
            'expected_racers' => $group['expected_racers'] ?? 0,
            'lanes' => $group['lanes'] ?? 3,
            'rounds_count' => count($group['rounds'] ?? []),
            'rounds_summary' => array()
        );

        // Add round summary
        if (isset($group['rounds']) && is_array($group['rounds'])) {
            foreach ($group['rounds'] as $round) {
                $age_group_info['rounds_summary'][] = array(
                    'name' => $round['round_name'] ?? 'Round ' . $round['round_sequence'],
                    'races_per_racer' => $round['races_per_racer'] ?? 1
                );
            }
        }

        // Check if this age group's pattern matches the class name
        if ($class_name && !$suggested_key) {
            if (preg_match('/' . $group['class_name_pattern'] . '/i', $class_name)) {
                $suggested_key = $group_key;
                $age_group_info['pattern_match'] = true;
            }
        }

        $age_groups[] = $age_group_info;
    }

    // Return age groups information
    header('Content-Type: application/json');
    echo json_encode(array(
        'outcome' => array('summary' => 'success'),
        'age_groups' => $age_groups,
        'suggested_key' => $suggested_key,
        'class_name' => $class_name,
        'config_file' => $config_file,
        'format_name' => $config['format_name'] ?? 'Unknown'
    ));
    exit;
} else {
    json_not_authorized();
}

?>
