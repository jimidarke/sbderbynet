<?php

require_once('inc/timer-state.inc');
require_once('inc/remote-start.inc');
require_once('inc/timer-state-xml.inc');  // For expand_timer_state_status


// function json_timer_state() {
//   $timer_state = new TimerState();
//   list($msg, $icon) = expand_timer_state_status($timer_state);
//   $tstate = $timer_state->state();

//   return array(
//     'lanes' => get_lane_count(),
//     'last-contact' => $timer_state->last_contact(),
//     'state' => $tstate,
//     // 'state1' => $tstate,
//     'icon' => $icon,
//     'remote-start' => has_remote_start() ? true : false,
//     'message' => $msg);
// }

function json_timer_state() {
  global $db;

  $timer_state = new TimerState();
  list($msg, $icon) = expand_timer_state_status($timer_state);
  $tstate = $timer_state->state();

  // Fetch timer statuses from the database
  $stmt = $db->query('SELECT lane, timerID, last_heartbeat, ready FROM TimerStatus');
  $timers = array();
  while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
      // error_log("Fetched timer status: " . print_r($row, true)); // Debugging
      $timers[] = array(
          'lane' => $row['lane'],
          'timerID' => $row['timerid'],
          'last_heartbeat' => $row['last_heartbeat'],
          'ready' => $row['ready']
      );
  }

  return array(
      'lanes' => get_lane_count(),
      'last-contact' => $timer_state->last_contact(),
      'state' => $tstate,
      'icon' => $icon,
      'remote-start' => has_remote_start() ? true : false,
      'message' => $msg,
      'timers' => $timers // Include timer statuses
  );
}

function json_timer_details() {
  return array('type' => read_raceinfo('timer-type', ''),
               'human' => read_raceinfo('timer-human', ''),
               'ident' => read_raceinfo('timer-ident', ''),
               'options' => read_raceinfo('timer-options', ''));
}

?>