<?php

/**
 * File Operations for Elimination Tournament Configurations
 *
 * Handles reading, writing, and managing JSON configuration files for elimination tournaments.
 * Provides safe file operations with locking, backup, and validation.
 */

require_once('inc/data.inc');
require_once('inc/elimination-config.inc');

/**
 * Save elimination configuration to JSON file
 *
 * @param string $filename Base filename (e.g., "soapbox-derby-elimination.json")
 * @param array $config Configuration array to save
 * @param bool $create_backup Create timestamped backup before overwriting
 * @return bool True on success, false on failure
 */
function save_elimination_config_file($filename, $config, $create_backup = true) {
    $config_dir = 'inc/elimination-configs';
    $filepath = $config_dir . '/' . $filename;

    // Validate configuration structure using existing validator
    if (!validate_elimination_config($config)) {
        error_log("Cannot save config: validation failed for $filename");
        return false;
    }

    // Check for active tournaments using this config
    $active_classes = get_classes_using_config($filename);
    if (!empty($active_classes)) {
        error_log("Cannot save config $filename: active tournaments exist for classes: " .
                 implode(', ', $active_classes));
        return false;
    }

    // Create backup if file exists
    if ($create_backup && file_exists($filepath)) {
        $backup_path = $filepath . '.' . date('Y-m-d-His') . '.backup';
        if (!copy($filepath, $backup_path)) {
            error_log("Failed to create backup: $backup_path");
            return false;
        }
        error_log("Created backup: $backup_path");
    }

    // Encode JSON with pretty printing for readability
    $json = json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        error_log("JSON encoding failed: " . json_last_error_msg());
        return false;
    }

    // Write with file locking for safe concurrent access
    $fp = fopen($filepath, 'w');
    if (!$fp) {
        error_log("Cannot open file for writing: $filepath");
        return false;
    }

    // Acquire exclusive lock
    if (!flock($fp, LOCK_EX)) {
        error_log("Cannot acquire file lock: $filepath");
        fclose($fp);
        return false;
    }

    // Write JSON data
    $bytes_written = fwrite($fp, $json);

    // Release lock and close file
    flock($fp, LOCK_UN);
    fclose($fp);

    if ($bytes_written === false || $bytes_written < strlen($json)) {
        error_log("Failed to write complete file: $filepath");
        return false;
    }

    // Verify written file is valid JSON
    $verify_content = file_get_contents($filepath);
    $verify = json_decode($verify_content, true);
    if ($verify === null) {
        error_log("Written file is invalid JSON: $filepath (error: " . json_last_error_msg() . ")");
        return false;
    }

    error_log("Successfully saved elimination config: $filepath");
    return true;
}

/**
 * Get list of classes currently using a configuration file
 *
 * @param string $config_file Configuration filename to check
 * @return array Array of class names if active tournaments exist, empty array otherwise
 */
function get_classes_using_config($config_file) {
    global $db;

    try {
        $stmt = $db->prepare('
            SELECT c.class
            FROM EliminationTournaments et
            JOIN Classes c ON et.classid = c.classid
            WHERE et.config_file = :config_file AND et.active = 1
        ');
        $stmt->execute(array(':config_file' => $config_file));

        $classes = array();
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $classes[] = $row['class'];
        }
        return $classes;
    } catch (Exception $e) {
        error_log("Error checking config usage: " . $e->getMessage());
        return array();
    }
}

/**
 * Delete configuration file with safety checks
 *
 * @param string $filename Configuration filename to delete
 * @return bool True on success, false on failure
 */
function delete_elimination_config_file($filename) {
    $config_dir = 'inc/elimination-configs';
    $filepath = $config_dir . '/' . $filename;

    // Safety check: Cannot delete if in use by active tournaments
    $active_classes = get_classes_using_config($filename);
    if (!empty($active_classes)) {
        error_log("Cannot delete config $filename: active tournaments exist for classes: " .
                 implode(', ', $active_classes));
        return false;
    }

    // Create final backup before deletion
    if (file_exists($filepath)) {
        $backup_path = $filepath . '.deleted-' . date('Y-m-d-His');
        if (!copy($filepath, $backup_path)) {
            error_log("Failed to create deletion backup: $backup_path");
            return false;
        }
        error_log("Created deletion backup: $backup_path");

        // Delete the file
        if (unlink($filepath)) {
            error_log("Deleted elimination config: $filepath");
            return true;
        } else {
            error_log("Failed to delete file: $filepath");
            return false;
        }
    }

    error_log("File does not exist: $filepath");
    return false;
}

/**
 * Clone configuration file with new name
 *
 * @param string $source_filename Source configuration filename
 * @param string $new_name New format name for cloned configuration
 * @return array|false Array with new filename on success, false on failure
 */
function clone_elimination_config_file($source_filename, $new_name) {
    // Load source configuration
    $config = load_elimination_config($source_filename);
    if (!$config) {
        error_log("Failed to load source config for cloning: $source_filename");
        return false;
    }

    // Update metadata for cloned config
    $config['format_name'] = $new_name;
    $config['description'] = '(Cloned from ' . basename($source_filename) . ') ' .
                            ($config['description'] ?? '');
    $config['version'] = '1.0';

    // Generate safe filename from new name
    $safe_name = preg_replace('/[^a-z0-9-]/', '-', strtolower($new_name));
    $safe_name = preg_replace('/-+/', '-', $safe_name);  // Remove duplicate dashes
    $safe_name = trim($safe_name, '-');  // Remove leading/trailing dashes
    $new_filename = $safe_name . '.json';

    // Check if file already exists
    $config_dir = 'inc/elimination-configs';
    $filepath = $config_dir . '/' . $new_filename;
    if (file_exists($filepath)) {
        // Append timestamp to make unique
        $new_filename = $safe_name . '-' . date('His') . '.json';
    }

    // Save as new file (no backup needed for new file)
    if (save_elimination_config_file($new_filename, $config, false)) {
        error_log("Cloned config from $source_filename to $new_filename");
        return array('filename' => $new_filename);
    }

    return false;
}

/**
 * Check if configuration directory is writable
 *
 * @return array Array with 'writable' boolean and optional 'error' message
 */
function check_config_directory_writable() {
    $config_dir = 'inc/elimination-configs';

    if (!is_dir($config_dir)) {
        return array(
            'writable' => false,
            'error' => 'Configuration directory does not exist: ' . $config_dir
        );
    }

    if (!is_writable($config_dir)) {
        return array(
            'writable' => false,
            'error' => 'Configuration directory is not writable. ' .
                      'Check file permissions (should be writable by web server)'
        );
    }

    return array('writable' => true);
}

/**
 * Generate a safe filename from a format name
 *
 * @param string $format_name Format name to convert
 * @return string Safe filename (without .json extension)
 */
function generate_safe_filename($format_name) {
    $safe_name = preg_replace('/[^a-z0-9-]/', '-', strtolower($format_name));
    $safe_name = preg_replace('/-+/', '-', $safe_name);
    $safe_name = trim($safe_name, '-');
    return $safe_name;
}

?>
