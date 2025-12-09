<?php

/**
 * Query endpoint to retrieve detailed elimination configuration
 *
 * GET parameters:
 *   filename - Configuration filename to load
 *
 * Returns:
 *   - outcome: success/failure
 *   - filename: Configuration filename
 *   - config: Full configuration object
 *   - locked: Boolean indicating if config is locked (tournament active)
 *   - active_classes: Array of class names using this config
 */

require_once('inc/elimination-config.inc');
require_once('inc/elimination-config-file-ops.inc');

if (have_permission(SET_UP_PERMISSION)) {
    $filename = $_GET['filename'] ?? null;

    if (!$filename) {
        json_failure('missing-filename', 'Filename parameter is required');
        return;
    }

    // Validate filename (basic security check)
    if (strpos($filename, '..') !== false || strpos($filename, '/') !== false) {
        json_failure('invalid-filename', 'Invalid filename');
        return;
    }

    // Load configuration from file
    $config = load_elimination_config($filename);
    if (!$config) {
        json_failure('load-failed', 'Failed to load configuration file: ' . $filename);
        return;
    }

    // Check if config is in use by active tournaments
    $active_classes = get_classes_using_config($filename);
    $is_locked = !empty($active_classes);

    // Return configuration details
    header('Content-Type: application/json');
    echo json_encode(array(
        'outcome' => array('summary' => 'success'),
        'filename' => $filename,
        'config' => $config,
        'locked' => $is_locked,
        'active_classes' => $active_classes
    ));
    exit;
} else {
    json_not_authorized();
}

?>
