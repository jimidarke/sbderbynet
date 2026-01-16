<?php @session_start(); ?>
<?php

// Receive POSTs to perform actions, return XML responses
//
// <action-response> is document root of reply, constructed from $_POST arguments
//
// This script will load the database config (i.e., perform a require_once of
// inc/data.inc) UNLESS the query or action name ends in ".nodata'.  Since
// inc/data.inc will force a page redirect if the database cannot be loaded, any
// queries or actions that potentially run before a database config file exists
// should be in include files that end in ".nodata.inc'.
require_once('inc/permissions.inc');
require_once('inc/authorize.inc');

require_once('inc/action-helpers.inc');
require_once('inc/error-logging.inc');
require_once('inc/error-codes.inc');

$json_out = array();

function json_out($key, $value)
{
  global $json_out;
  $json_out[$key] = $value;
}

function json_success()
{
  json_out('outcome', array(
    'summary' => 'success',
    'code' => 'success',
    'description' => ''
  ));
}

function json_failure($code, $description, $context = null)
{
  global $ERROR_CODES, $LEGACY_CODE_MAP;

  // Map legacy code to standardized code if available
  $std_code = null;
  if (isset($LEGACY_CODE_MAP[$code])) {
    $std_code = $LEGACY_CODE_MAP[$code];
  } elseif (preg_match('/^ERR-[A-Z]+-[123]\d{2}$/', $code)) {
    // Already a standardized code
    $std_code = $code;
  }

  // Get error details for logging
  $error_details = derby_get_error_details($std_code ?? 'ERR-SYS-201');
  $log_level = $error_details['level'] ?? 'ERROR';

  // Log the error with standardized code
  if ($std_code) {
    derby_log($log_level, $description, $std_code, $context);
  } else {
    derby_log($log_level, "[$code] $description", null, $context);
  }

  // Build outcome array
  $outcome = array(
    'summary' => 'failure',
    'code' => $code,  // Keep original code for backward compatibility
    'description' => $description
  );

  // Add standardized code if different from original
  if ($std_code && $std_code !== $code) {
    $outcome['error_code'] = $std_code;
  }

  json_out('outcome', $outcome);
}

function json_sql_failure($sql)
{
  global $db;
  $info = $db->errorInfo();
  json_failure('sql', "$sql failed: $info[2]", array(
    'sqlstate' => $info[0],
    'driver_code' => $info[1],
    'query' => substr($sql, 0, 200)  // Truncate long queries
  ));
}

function json_not_authorized()
{
  json_failure('notauthorized', "Not authorized -- please see race coordinator.");
}

if (empty($_POST) && empty($_GET)) {
  echo '<!DOCTYPE html><html><head><title>Not a Page</title></head><body><h1>This is not a page.</h1></body></html>';
  exit(1);
}

$is_action = !empty($_POST);
$inc = $is_action ? ($_POST['action'] ?? '') : ($_GET['query'] ?? '');

$in_json = $inc !== 'timer-message' && strpos($inc, 'snapshot') === false
  // These are to provide an error message for older derby-timer.jar
  && $inc !== 'login' && $inc !== 'roles';

if ($in_json) {
  header('Content-Type: application/json; charset=utf-8');
} else {
  header('Content-Type: text/xml; charset=utf-8');
  echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
}

if (is_string($inc) && substr($inc, -7) != '.nodata') {
  require_once('inc/data.inc');
  if (
    strpos($inc, 'ballot.get') === false &&
    strpos($inc, 'session.write') === false &&
    strpos($inc, 'role.login') === false
  ) {
    session_write_close();
  }
}

if ($is_action) {
  $args = array();
  foreach ($_POST as $attr => $val) {
    $args[$attr] = $attr == 'password' ? '...' : $val;
  }
  json_out('action', $args);
  json_out('outcome', array(
    'summary' => 'in-progress',
    'code' => 'in-progress',
    'description' => 'No outcome defined.'
  ));
  if (
    isset($db) &&
    !($args['action'] == 'timer-message' && $args['message'] == 'HEARTBEAT') &&
    array_search($args['action'], array('role.login', 'vote.cast', 'replay-message')) === false
  ) {
    record_action($args);
  }
}

$prefix = $is_action ? 'action' : 'query';
if (!@include 'ajax/' . $prefix . '.' . $inc . '.inc') {
  if ($in_json) {
    json_failure('unrecognized', "Unrecognized $prefix: $inc");
  } else {
    start_response();
    echo '<failure code="unrecognized">Unrecognized ' . $prefix . ': ' . $inc . '</failure>';
    end_response();
  }
}

if ($in_json) {
  if (empty($json_out)) {
    $json_out = new stdClass();
  }
  echo json_encode($json_out, JSON_PRETTY_PRINT | JSON_NUMERIC_CHECK);
  echo "\n";
}


?>
