<?php

/**
 * Elimination Configuration Management
 * 
 * Handles loading, validation, and application of elimination tournament configurations
 * from JSON files. Supports hardcoded tournament formats for predictable race management.
 */

require_once('inc/data.inc');
require_once('inc/classes.inc');

/**
 * Load all available elimination configuration files
 * @return array Array of configuration file info
 */
function load_elimination_config_list() {
    $config_dir = 'inc/elimination-configs';
    $configs = array();
    
    if (is_dir($config_dir)) {
        $files = glob($config_dir . '/*.json');
        foreach ($files as $file) {
            $content = file_get_contents($file);
            if ($content !== false) {
                $config = json_decode($content, true);
                if ($config !== null && isset($config['format_name'])) {
                    $configs[] = array(
                        'file' => basename($file),
                        'path' => $file,
                        'name' => $config['format_name'],
                        'description' => isset($config['description']) ? $config['description'] : '',
                        'version' => isset($config['version']) ? $config['version'] : '1.0'
                    );
                }
            }
        }
    }
    
    return $configs;
}

/**
 * Load a specific elimination configuration
 * @param string $config_file Configuration file name
 * @return array|false Configuration data or false on error
 */
function load_elimination_config($config_file) {
    $config_path = 'inc/elimination-configs/' . $config_file;
    
    if (!file_exists($config_path)) {
        error_log("Elimination config file not found: " . $config_path);
        return false;
    }
    
    $content = file_get_contents($config_path);
    if ($content === false) {
        error_log("Failed to read elimination config file: " . $config_path);
        return false;
    }
    
    $config = json_decode($content, true);
    if ($config === null) {
        error_log("Invalid JSON in elimination config file: " . $config_path);
        return false;
    }
    
    // Validate basic structure
    if (!validate_elimination_config($config)) {
        return false;
    }
    
    return $config;
}

/**
 * Validate elimination configuration structure
 * @param array $config Configuration to validate
 * @return bool True if valid
 */
function validate_elimination_config($config) {
    // Check required top-level fields
    $required_fields = array('format_name', 'age_groups');
    foreach ($required_fields as $field) {
        if (!isset($config[$field])) {
            error_log("Missing required field in elimination config: " . $field);
            return false;
        }
    }
    
    // Validate each age group
    foreach ($config['age_groups'] as $group_key => $group) {
        if (!validate_age_group_config($group, $group_key)) {
            return false;
        }
    }
    
    return true;
}

/**
 * Validate age group configuration
 * @param array $group Age group configuration
 * @param string $group_key Age group key for error reporting
 * @return bool True if valid
 */
function validate_age_group_config($group, $group_key) {
    $required_fields = array('name', 'class_name_pattern', 'rounds');
    foreach ($required_fields as $field) {
        if (!isset($group[$field])) {
            error_log("Missing required field '{$field}' in age group '{$group_key}'");
            return false;
        }
    }
    
    // Validate rounds
    if (!is_array($group['rounds']) || empty($group['rounds'])) {
        error_log("Invalid rounds configuration for age group '{$group_key}'");
        return false;
    }
    
    foreach ($group['rounds'] as $index => $round) {
        if (!validate_round_config($round, $group_key, $index)) {
            return false;
        }
    }
    
    return true;
}

/**
 * Validate round configuration
 * @param array $round Round configuration
 * @param string $group_key Age group key for error reporting
 * @param int $round_index Round index for error reporting
 * @return bool True if valid
 */
function validate_round_config($round, $group_key, $round_index) {
    $required_fields = array('round_sequence', 'round_name', 'races_per_racer', 
                           'advancement_rule', 'scoring_method');
    foreach ($required_fields as $field) {
        if (!isset($round[$field])) {
            error_log("Missing required field '{$field}' in round {$round_index} for age group '{$group_key}'");
            return false;
        }
    }
    
    // Validate advancement rule
    $valid_advancement_rules = array('top_count', 'percentage', 'placement');
    if (!in_array($round['advancement_rule'], $valid_advancement_rules)) {
        error_log("Invalid advancement rule '{$round['advancement_rule']}' in round {$round_index} for age group '{$group_key}'");
        return false;
    }
    
    // Validate scoring method
    $valid_scoring_methods = array('total_time', 'best_time', 'average_time', 'placement');
    if (!in_array($round['scoring_method'], $valid_scoring_methods)) {
        error_log("Invalid scoring method '{$round['scoring_method']}' in round {$round_index} for age group '{$group_key}'");
        return false;
    }
    
    return true;
}

/**
 * Find matching age group configuration for a class
 * @param array $config Elimination configuration
 * @param int $classid DerbyNet class ID
 * @return array|false Age group configuration or false if no match
 */
function find_age_group_for_class($config, $classid) {
    global $db;
    
    // Get class name from database
    $class_name = read_single_value('SELECT class FROM Classes WHERE classid = :classid', 
                                   array(':classid' => $classid));
    
    if (!$class_name) {
        error_log("Class not found for classid: " . $classid);
        return false;
    }
    
    // Try to match against age group patterns
    foreach ($config['age_groups'] as $group_key => $group) {
        if (preg_match('/' . $group['class_name_pattern'] . '/i', $class_name)) {
            return array_merge($group, array('group_key' => $group_key));
        }
    }
    
    error_log("No age group pattern matched for class: " . $class_name);
    return false;
}

/**
 * Get current elimination tournament state for a class
 * @param int $classid DerbyNet class ID
 * @return array|false Tournament state or false if no active tournament
 */
function get_elimination_tournament_state($classid) {
    global $db;
    
    $stmt = $db->prepare('SELECT * FROM EliminationTournaments WHERE classid = :classid AND active = 1');
    $stmt->execute(array(':classid' => $classid));
    $tournament = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$tournament) {
        return false;
    }
    
    // Load configuration
    $config = load_elimination_config($tournament['config_file']);
    if (!$config) {
        error_log("Failed to load config for tournament: " . $tournament['config_file']);
        return false;
    }
    
    // Find age group configuration
    $age_group = find_age_group_for_class($config, $classid);
    if (!$age_group) {
        return false;
    }
    
    return array(
        'tournament' => $tournament,
        'config' => $config,
        'age_group' => $age_group,
        'current_round' => $tournament['current_round'],
        'total_rounds' => count($age_group['rounds'])
    );
}

/**
 * Initialize elimination tournament for a class
 * @param int $classid DerbyNet class ID  
 * @param string $config_file Configuration file to use
 * @return bool True on success
 */
function initialize_elimination_tournament($classid, $config_file) {
    global $db;
    
    // Load and validate configuration
    $config = load_elimination_config($config_file);
    if (!$config) {
        return false;
    }
    
    // Find matching age group
    $age_group = find_age_group_for_class($config, $classid);
    if (!$age_group) {
        return false;
    }
    
    try {
        $db->beginTransaction();
        
        // Apply scheduling rules from configuration
        apply_elimination_scheduling_rules($config);
        
        // Deactivate any existing tournaments for this class
        $stmt = $db->prepare('UPDATE EliminationTournaments SET active = 0 WHERE classid = :classid');
        $stmt->execute(array(':classid' => $classid));
        
        // Create new tournament record
        $stmt = $db->prepare('INSERT INTO EliminationTournaments 
                             (classid, config_file, age_group_key, current_round, total_rounds, active, created_at)
                             VALUES (:classid, :config_file, :age_group_key, 1, :total_rounds, 1, datetime("now"))');
        $stmt->execute(array(
            ':classid' => $classid,
            ':config_file' => $config_file,
            ':age_group_key' => $age_group['group_key'],
            ':total_rounds' => count($age_group['rounds'])
        ));
        
        $tournament_id = $db->lastInsertId();
        
        // Create rounds in database
        foreach ($age_group['rounds'] as $round_config) {
            create_elimination_round($classid, $tournament_id, $round_config);
        }
        
        $db->commit();
        
        error_log("Initialized elimination tournament for class {$classid} with config {$config_file}");
        return true;
        
    } catch (Exception $e) {
        $db->rollBack();
        error_log("Failed to initialize elimination tournament: " . $e->getMessage());
        return false;
    }
}

/**
 * Apply scheduling rules from elimination configuration
 * @param array $config Elimination configuration
 */
function apply_elimination_scheduling_rules($config) {
    if (!isset($config['scheduling_rules']['heat_ordering'])) {
        return;
    }
    
    $heat_ordering = $config['scheduling_rules']['heat_ordering'];
    
    // Apply heat ordering weights from configuration
    if (isset($heat_ordering['heat_counts'])) {
        write_raceinfo('heat-counts', $heat_ordering['heat_counts']);
    }
    if (isset($heat_ordering['group_weighted_cars'])) {
        write_raceinfo('group-weighted-cars', $heat_ordering['group_weighted_cars']);
    }
    if (isset($heat_ordering['avoid_consecutive'])) {
        write_raceinfo('avoid-consecutive', $heat_ordering['avoid_consecutive']);
    }
    if (isset($heat_ordering['avoid_same_lane'])) {
        write_raceinfo('avoid-same-lane', $heat_ordering['avoid_same_lane']);
    }
    
    error_log("Applied elimination scheduling rules: avoid_consecutive=" . 
              ($heat_ordering['avoid_consecutive'] ?? 'default') . 
              ", heat_counts=" . ($heat_ordering['heat_counts'] ?? 'default') .
              ", group_weighted_cars=" . ($heat_ordering['group_weighted_cars'] ?? 'default') .
              ", avoid_same_lane=" . ($heat_ordering['avoid_same_lane'] ?? 'default'));
}

/**
 * Create elimination round in database
 * @param int $classid Class ID
 * @param int $tournament_id Tournament ID
 * @param array $round_config Round configuration
 * @return int|false Round ID or false on error
 */
function create_elimination_round($classid, $tournament_id, $round_config) {
    global $db;
    
    $round_name = $round_config['round_name'];
    
    // Insert round using existing schema columns
    $stmt = $db->prepare('INSERT INTO Rounds (classid, round, roundname, is_triple_elim, elim_type)
                         VALUES (:classid, :round, :roundname, 1, :elim_type)');
    
    $stmt->execute(array(
        ':classid' => $classid,
        ':round' => $round_config['round_sequence'],
        ':roundname' => $round_name,
        ':elim_type' => $round_config['round_name']
    ));
    
    return $db->lastInsertId();
}

/**
 * Check if a class is using elimination tournament format
 * @param int $classid Class ID
 * @return bool True if elimination tournament is active
 */
function is_elimination_tournament_active($classid) {
    global $db;
    
    $count = read_single_value('SELECT COUNT(*) FROM EliminationTournaments 
                              WHERE classid = :classid AND active = 1',
                              array(':classid' => $classid));
    return $count > 0;
}

/**
 * Get elimination tournament configuration for coordinator display
 * @param int $classid Class ID
 * @return array|false Tournament info for display or false if none
 */
function get_elimination_tournament_info($classid) {
    $state = get_elimination_tournament_state($classid);
    if (!$state) {
        return false;
    }
    
    $current_round_config = $state['age_group']['rounds'][$state['current_round'] - 1];
    
    return array(
        'tournament_id' => $state['tournament']['tournament_id'],
        'format_name' => $state['config']['format_name'],
        'age_group_name' => $state['age_group']['name'],
        'current_round' => $state['current_round'],
        'total_rounds' => $state['total_rounds'],
        'current_round_name' => $current_round_config['round_name'],
        'races_per_racer' => $current_round_config['races_per_racer'],
        'advancement_info' => format_advancement_info($current_round_config)
    );
}

/**
 * Format advancement information for display
 * @param array $round_config Round configuration
 * @return string Formatted advancement description
 */
function format_advancement_info($round_config) {
    if ($round_config['advancement_rule'] === 'placement') {
        return "Final round - determines final standings";
    } elseif ($round_config['advancement_rule'] === 'top_count') {
        return "Top {$round_config['advance_count']} advance to next round";
    } elseif ($round_config['advancement_rule'] === 'percentage') {
        return "Top {$round_config['advance_percentage']}% advance to next round";
    }
    return "Unknown advancement rule";
}

?>