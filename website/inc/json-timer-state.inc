<?php

require_once('inc/timer-state.inc');
require_once('inc/remote-start.inc');
require_once('inc/timer-state-xml.inc');  // For expand_timer_state_status

// // Old Timer States
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

// // Working Timer States 
function json_timer_state() {
  global $db;

  $timer_state = new TimerState();
  list($msg, $icon) = expand_timer_state_status($timer_state);
  $tstate = $timer_state->state();

  // Fetch timer statuses from the database
  $stmt = $db->query('SELECT lane, timerID, last_heartbeat, ready, is_starter FROM TimerStatus');
  $timers = array();
  while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
      error_log("Fetched timer status: " . print_r($row, true)); // Debugginger
      $timers[] = array(
          'lane' => $row['lane'],
          'timerID' => $row['timerID'] ?? $row['timerid'], // Handle both 'timerID' and 'timerid'
          'last_heartbeat' => $row['last_heartbeat'],
          'ready' => $row['ready'],
          'is_starter' => (bool)$row['is_starter'],
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


// // Enhanced Timer State Management for Individual timers
// function json_timer_state() {
//   global $db;
  
//   $timer_state = new TimerState();
//   list($msg, $icon) = expand_timer_state_status($timer_state);
//   $tstate = $timer_state->state();

//   // Use time() for consistent timestamp handling
//   $current_time = time();

//   // Defined constants for better maintainability
//   define('DISCONNECT_THRESHOLD', 60); // 60 seconds without heartbeat = disconnected
//   define('STALE_THRESHOLD', 300);     // 300 seconds = delete timer entry

//   // Fetch timer statuses with improved state handling
//   $stmt = $db->prepare('SELECT 
//       ts.lane, 
//       ts.timerID, 
//       ts.last_heartbeat, 
//       ts.ready,
//       ts.is_starter,
//       CASE 
//           WHEN ts.ready = 1 AND (? - ts.last_heartbeat) <= ? THEN "READY"
//           WHEN (? - ts.last_heartbeat) > ? THEN "DISCONNECTED"
//           ELSE "WAITING"
//       END as timer_state,
//       CASE 
//           WHEN ts.ready = 1 AND (? - ts.last_heartbeat) <= ? THEN "img/status/ok.png"
//           WHEN (? - ts.last_heartbeat) > ? THEN "img/status/trouble.png"
//           ELSE "img/status/unknown.png"
//       END as timer_icon
//       FROM TimerStatus ts
//       ORDER BY ts.lane ASC');

//   $stmt->execute([
//       $current_time, DISCONNECT_THRESHOLD,
//       $current_time, DISCONNECT_THRESHOLD,
//       $current_time, DISCONNECT_THRESHOLD,
//       $current_time, DISCONNECT_THRESHOLD
//   ]);

//   $timers = [];
//   while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
//       // error_log("Fetched timer status: " . print_r($row, true));
//       $timers[] = [
//           'lane' => (int)$row['lane'],
//           'timerID' => $row['timerid'],
//           'last_heartbeat' => (int)$row['last_heartbeat'],
//           'ready' => (bool)$row['ready'],
//           'is_starter' => (bool)$row['is_starter'],
//           'state' => $row['timer_state'],
//           'icon' => $row['timer_icon'],
//           'last_seen' => ($current_time - $row['last_heartbeat']) . ' seconds ago'
//       ];
//   }

//   // Clean up stale entries using prepared statement
//   $cleanup = $db->prepare('DELETE FROM TimerStatus WHERE (? - last_heartbeat) > ?');
//   $cleanup->execute([$current_time, STALE_THRESHOLD]);

//   return [
//       'lanes' => get_lane_count(),
//       'last-contact' => $timer_state->last_contact(),
//       'state' => $tstate,
//       'icon' => $icon, 
//       'remote-start' => has_remote_start() ? true : false,
//       'message' => $msg,
//       'timers' => $timers
//   ];
// }

function json_timer_details() {
  return array('type' => read_raceinfo('timer-type', ''),
               'human' => read_raceinfo('timer-human', ''),
               'ident' => read_raceinfo('timer-ident', ''),
               'options' => read_raceinfo('timer-options', ''));
}

?>