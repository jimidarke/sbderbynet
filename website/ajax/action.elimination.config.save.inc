<?php

/**
 * Action endpoint to save elimination configuration
 *
 * POST parameters:
 *   operation - 'update'|'create' (update existing file or create new)
 *   filename - Configuration filename (for update operation)
 *   config_json - JSON string of full configuration object
 *
 * Returns:
 *   - outcome: success/failure
 *   - filename: Saved filename
 *   - message: Success/error message
 */

require_once('inc/elimination-config.inc');
require_once('inc/elimination-config-file-ops.inc');

if (have_permission(SET_UP_PERMISSION)) {
    try {
        $operation = $_POST['operation'] ?? 'update';
        $filename = $_POST['filename'] ?? null;
        $config_json = $_POST['config_json'] ?? null;

        if (!$config_json) {
            json_failure('missing-data', 'Configuration data is required');
            return;
        }

        // Parse JSON configuration
        $config_data = json_decode($config_json, true);
        if (!$config_data) {
            json_failure('invalid-json', 'Invalid JSON data: ' . json_last_error_msg());
            return;
        }

        // Validate configuration structure
        if (!validate_elimination_config($config_data)) {
            json_failure('invalid-config', 'Configuration validation failed. Check format_name, age_groups, and rounds structure.');
            return;
        }

        // Generate filename for new configs
        if ($operation === 'create') {
            $format_name = $config_data['format_name'] ?? 'unnamed';
            $filename = generate_safe_filename($format_name) . '.json';

            // Check if file already exists
            $config_dir = 'inc/elimination-configs';
            if (file_exists($config_dir . '/' . $filename)) {
                // Append timestamp to make unique
                $filename = generate_safe_filename($format_name) . '-' . date('His') . '.json';
            }
        }

        if (!$filename) {
            json_failure('missing-filename', 'Filename is required for update operation');
            return;
        }

        // Validate filename (security check)
        if (strpos($filename, '..') !== false || strpos($filename, '/') !== false) {
            json_failure('invalid-filename', 'Invalid filename');
            return;
        }

        // Check if modifying active tournament config
        if ($operation === 'update') {
            $active_classes = get_classes_using_config($filename);
            if (!empty($active_classes)) {
                json_failure('tournament-active',
                           'Cannot modify: active tournaments exist for classes: ' .
                           implode(', ', $active_classes));
                return;
            }
        }

        // Save configuration file
        if (save_elimination_config_file($filename, $config_data)) {
            json_success(array(
                'message' => 'Configuration saved successfully',
                'filename' => $filename
            ));
        } else {
            json_failure('save-failed', 'Failed to save configuration file. Check error log for details.');
        }

    } catch (Exception $e) {
        error_log("Error in elimination config save: " . $e->getMessage());
        json_failure('exception', $e->getMessage());
    }
} else {
    json_not_authorized();
}

?>
