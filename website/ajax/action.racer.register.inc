<?php
require_once('inc/events.inc');
require_once('inc/schema_version.inc');
require_once('inc/error-logging.inc');

$value = isset($_POST['value']) ? $_POST['value'] : 1;
$racerid = @$_POST['racer'];

if (isset($_POST['barcode'])) {
  require_once('inc/barcode.inc');
  $racerid = barcode_to_racerid($_POST['barcode']);
}

if ($_POST['action'] == 'racer.register') {

  if (!have_permission(CHECK_IN_RACERS_PERMISSION)) {
    echo json_encode(['success' => false, 'error' => 'not_authorized']);
    exit;
  }

  if (register_racer($racerid, $value)) {
    $response = ['success' => true];

    if ($value) {
      $details = read_single_row(
        'SELECT class, firstname, lastname
         FROM RegistrationInfo
         INNER JOIN Classes ON Classes.classid = RegistrationInfo.classid
         WHERE racerid = :racerid',
        [':racerid' => $racerid],
        PDO::FETCH_ASSOC
      );

      if ($details) {
        $response['details'] = $details;
      }
    }

    echo json_encode($response);
    exit;
  } else {
    // register_racer already outputs json_failure, so no need to do anything else
    exit;
  }
}

function register_racer($racerid, $value)
{
  global $db;

  if (empty($racerid)) {
    echo json_encode(['success' => false, 'error' => 'notunique']);
    return false;
  }

  // Prevent unregistration if already registered
  if ($value == 0) {
    $current_status = read_single_value(
      'SELECT registered FROM RegistrationInfo WHERE racerid = :racerid',
      [':racerid' => $racerid]
    );

    if ($current_status == 1) {
      json_failure(code: 'cannot_unregister', description: 'Once registered, a racer cannot be unregistered.');
      exit;
    }
  }

  $scheduled = read_single_value(
    'SELECT COUNT(*) FROM RaceChart
     WHERE racerid = :racerid
       AND (finishtime IS NOT NULL OR finishplace IS NOT NULL)',
    [':racerid' => $racerid],
    0
  );

  if ($scheduled > 0) {
    echo json_encode(['success' => false, 'error' => 'alreadyscheduled']);
    return false;
  }

  if ($value || have_permission(REVERT_CHECK_IN_PERMISSION)) {
    take_action_silently(
      'UPDATE RegistrationInfo
         SET registered = :value' .
        ($value && schema_version() < REGISTRATION_CHECKIN_SCHEMA ? ''
          : ', checkin_time = ' . floor(microtime(true) * 1000)) .
        ' WHERE racerid = :racerid',
      [
        ':value' => $value,
        ':racerid' => $racerid
      ]
    );

    record_event(EVENT_CHECKIN, ['racerid' => $racerid, 'registered' => $value]);
    return true;
  } else {
    echo json_encode(['success' => false, 'error' => 'not_authorized']);
    return false;
  }
}