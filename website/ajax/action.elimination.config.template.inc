<?php

require_once('inc/data.inc');
require_once('inc/authorize.inc');
require_once('inc/elimination-config.inc');
require_once('inc/permissions.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  try {
    $classid = $_POST['classid'];
    $template_key = $_POST['template_key'];
    $config_name = $_POST['config_name'];
    
    if (!$classid || !$template_key) {
      json_failure('missing-data', 'Class ID and template key are required');
      return;
    }
    
    $configid = apply_elimination_template($classid, $template_key, $config_name);
    
    if ($configid) {
      json_success(array(
        'message' => 'Template applied successfully', 
        'configid' => $configid
      ));
    } else {
      json_failure('template-failed', 'Failed to apply template');
    }
    
  } catch (Exception $e) {
    error_log("Error applying elimination template: " . $e->getMessage());
    json_failure('exception', $e->getMessage());
  }
} else {
  json_not_authorized();
}

?>