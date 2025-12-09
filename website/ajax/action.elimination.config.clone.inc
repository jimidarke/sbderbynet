<?php

/**
 * Action endpoint to clone elimination configuration
 *
 * POST parameters:
 *   source_filename - Source configuration filename to clone
 *   new_name - New format name for the cloned configuration
 *
 * Returns:
 *   - outcome: success/failure
 *   - filename: New configuration filename
 *   - message: Success/error message
 */

require_once('inc/elimination-config-file-ops.inc');

if (have_permission(SET_UP_PERMISSION)) {
    try {
        $source_filename = $_POST['source_filename'] ?? null;
        $new_name = $_POST['new_name'] ?? null;

        if (!$source_filename || !$new_name) {
            json_failure('missing-data', 'Source filename and new name are required');
            return;
        }

        // Validate source filename (security check)
        if (strpos($source_filename, '..') !== false || strpos($source_filename, '/') !== false) {
            json_failure('invalid-filename', 'Invalid source filename');
            return;
        }

        // Clone configuration file
        $result = clone_elimination_config_file($source_filename, $new_name);

        if ($result && isset($result['filename'])) {
            json_success(array(
                'message' => 'Configuration cloned successfully',
                'filename' => $result['filename']
            ));
        } else {
            json_failure('clone-failed', 'Failed to clone configuration file. Check error log for details.');
        }

    } catch (Exception $e) {
        error_log("Error cloning elimination config: " . $e->getMessage());
        json_failure('exception', $e->getMessage());
    }
} else {
    json_not_authorized();
}

?>
