<?php

require_once('inc/data.inc');
require_once('inc/authorize.inc');
require_once('inc/elimination-config.inc');
require_once('inc/permissions.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  try {
    $classid = $_POST['classid'];
    $configid = isset($_POST['configid']) ? $_POST['configid'] : null;
    $config_name = $_POST['config_name'];
    $rounds_data = json_decode($_POST['rounds_data'], true);
    
    if (!$classid || !$config_name || !$rounds_data) {
      json_failure('missing-data', 'Missing required data');
      return;
    }
    
    if (!is_array($rounds_data) || empty($rounds_data)) {
      json_failure('invalid-rounds', 'Invalid rounds data');
      return;
    }
    
    // Validate rounds data
    foreach ($rounds_data as $i => $round) {
      if (!isset($round['name']) || !isset($round['runs_per_racer'])) {
        json_failure('invalid-round-data', "Round $i is missing required fields");
        return;
      }
      
      if ($round['runs_per_racer'] < 1 || $round['runs_per_racer'] > 6) {
        json_failure('invalid-runs', "Round $i runs per racer must be between 1 and 6");
        return;
      }
      
      if (isset($round['advancement_count']) && $round['advancement_count'] < 1) {
        json_failure('invalid-advancement', "Round $i advancement count must be positive");
        return;
      }
    }
    
    if ($configid) {
      // Update existing configuration
      $result = update_elimination_config($configid, $config_name, $rounds_data);
      if ($result) {
        json_success(array('message' => 'Configuration updated successfully', 'configid' => $configid));
      } else {
        json_failure('update-failed', 'Failed to update configuration');
      }
    } else {
      // Create new configuration
      $new_configid = create_elimination_config($classid, $config_name, $rounds_data);
      if ($new_configid) {
        json_success(array('message' => 'Configuration created successfully', 'configid' => $new_configid));
      } else {
        json_failure('create-failed', 'Failed to create configuration');
      }
    }
    
  } catch (Exception $e) {
    error_log("Error in elimination config save: " . $e->getMessage());
    json_failure('exception', $e->getMessage());
  }
} else {
  json_not_authorized();
}

?>