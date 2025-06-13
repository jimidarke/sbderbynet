<?php

require_once('inc/data.inc');
require_once('inc/authorize.inc');
require_once('inc/elimination-config.inc');
require_once('inc/permissions.inc');

if (have_permission(CONTROL_RACE_PERMISSION)) {
  try {
    $templates = get_elimination_templates();
    json_success(array('templates' => $templates));
    
  } catch (Exception $e) {
    error_log("Error querying elimination templates: " . $e->getMessage());
    json_failure('exception', $e->getMessage());
  }
} else {
  json_not_authorized();
}

?>