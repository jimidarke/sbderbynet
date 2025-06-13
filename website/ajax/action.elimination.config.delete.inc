<?php

require_once('inc/data.inc');
require_once('inc/authorize.inc');
require_once('inc/elimination-config.inc');
require_once('inc/permissions.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  try {
    $configid = $_POST['configid'];
    
    if (!$configid) {
      json_failure('missing-configid', 'Configuration ID is required');
      return;
    }
    
    $result = delete_elimination_config($configid);
    
    if ($result) {
      json_success(array('message' => 'Configuration deleted successfully'));
    } else {
      json_failure('delete-failed', 'Failed to delete configuration');
    }
    
  } catch (Exception $e) {
    error_log("Error deleting elimination config: " . $e->getMessage());
    json_failure('exception', $e->getMessage());
  }
} else {
  json_not_authorized();
}

?>