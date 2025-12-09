<?php

/**
 * Action endpoint to delete elimination configuration
 *
 * POST parameters:
 *   filename - Configuration filename to delete
 *
 * Returns:
 *   - outcome: success/failure
 *   - message: Success/error message
 */

require_once('inc/elimination-config-file-ops.inc');

if (have_permission(SET_UP_PERMISSION)) {
    try {
        $filename = $_POST['filename'] ?? null;

        if (!$filename) {
            json_failure('missing-filename', 'Filename is required');
            return;
        }

        // Validate filename (security check)
        if (strpos($filename, '..') !== false || strpos($filename, '/') !== false) {
            json_failure('invalid-filename', 'Invalid filename');
            return;
        }

        // Safety check: Cannot delete if active tournaments exist
        $active_classes = get_classes_using_config($filename);
        if (!empty($active_classes)) {
            json_failure('tournament-active',
                       'Cannot delete: active tournaments exist for classes: ' .
                       implode(', ', $active_classes));
            return;
        }

        // Delete configuration file
        if (delete_elimination_config_file($filename)) {
            json_success(array('message' => 'Configuration deleted successfully'));
        } else {
            json_failure('delete-failed', 'Failed to delete configuration file. Check error log for details.');
        }

    } catch (Exception $e) {
        error_log("Error deleting elimination config: " . $e->getMessage());
        json_failure('exception', $e->getMessage());
    }
} else {
    json_not_authorized();
}

?>
