<?php

require_once('inc/timer-state.inc');
require_once('inc/remote-start.inc');
require_once('inc/timer-state-xml.inc');  // For expand_timer_state_status
require_once('inc/error-logging.inc');  // For derby_log_warning
require_once('inc/data.inc');  // For read_single_value
require_once('inc/heartbeat-config.inc');  // For timeout thresholds

// Working Timer States with Health Status
function json_timer_state() {
  global $db;

  $timer_state = new TimerState();
  list($msg, $icon) = expand_timer_state_status($timer_state);
  $tstate = $timer_state->state();
  $current_time = time();

  // Fetch timer statuses from the database
  $timers = array();
  $online_count = 0;
  $ready_count = 0;

  try {
      // First check if TimerStatus table exists
      $table_exists = read_single_value("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='TimerStatus'") > 0;

      if (!$table_exists) {
          derby_log_warning("TimerStatus table does not exist in database");
      } else {
          $stmt = $db->query('SELECT lane, timerid as timerID, last_heartbeat, ready, is_starter FROM TimerStatus ORDER BY lane ASC');
          if ($stmt) {
              while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                  $seconds_since_heartbeat = $current_time - (int)$row['last_heartbeat'];
                  $is_online = $seconds_since_heartbeat <= FRONTEND_OFFLINE_THRESHOLD;

                  // Build timer status array with proper column mapping
                  $timers[] = array(
                      'lane' => (int)$row['lane'],
                      'timerID' => $row['timerID'] ?? $row['timerid'],
                      'last_heartbeat' => (int)$row['last_heartbeat'],
                      'ready' => (bool)$row['ready'],
                      'is_starter' => (bool)$row['is_starter'],
                      'is_online' => $is_online,
                      'seconds_ago' => $seconds_since_heartbeat,
                  );

                  // Count online finish timers (not starter)
                  if ($is_online && !$row['is_starter']) {
                      $online_count++;
                      if ($row['ready']) {
                          $ready_count++;
                      }
                  }
              }
          }
      }
  } catch (Exception $e) {
      derby_log_warning("Error fetching timer status from database: " . $e->getMessage());
  }

  // Determine system health status based on timer availability
  $race_active = read_raceinfo('NowRacingState', 0) != 0;
  $required_timers = MIN_TIMERS_FOR_RACE;
  $health_status = 'healthy';
  $health_message = '';

  if ($race_active) {
      // During active racing, missing timers are critical
      if ($online_count < $required_timers) {
          $health_status = 'critical';
          $health_message = "WARNING: Only {$online_count}/{$required_timers} timers online during active race!";
      } elseif ($ready_count < $required_timers) {
          $health_status = 'warning';
          $health_message = "Some timers not ready ({$ready_count}/{$required_timers})";
      }
  } else {
      // When not racing, missing timers are degraded (warning)
      if ($online_count < $required_timers) {
          $health_status = 'degraded';
          $health_message = "{$online_count}/{$required_timers} finish timers online";
      }
  }

  return array(
      'lanes' => get_lane_count(),
      'last-contact' => $timer_state->last_contact(),
      'state' => $tstate,
      'icon' => $icon,
      'remote-start' => has_remote_start() ? true : false,
      'message' => $msg,
      'timers' => $timers,
      // Health status fields for state integrity
      'server_time' => $current_time,
      'timers_online' => $online_count,
      'timers_ready' => $ready_count,
      'timers_required' => $required_timers,
      'health_status' => $health_status,
      'health_message' => $health_message,
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