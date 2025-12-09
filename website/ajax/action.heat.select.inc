<?php
require_once('inc/error-logging.inc');
require_once('inc/autoadvance.inc');
require_once('inc/racing-state.inc');
require_once('inc/scenes.inc');

$ok = true;

if (have_permission(CONTROL_RACE_PERMISSION)) {
  if (isset($_POST['roundid']) || isset($_POST['heat'])) {
    // Ensure race state is off before changing heats
    set_racing_state(0);

    // Get current round/heat state
    $current = get_running_round();

    // Override current roundid if one is provided
    if (isset($_POST['roundid'])) {
      $current['roundid'] = $_POST['roundid'];
    }

    // Default to heat 1 if roundid was set but no heat was specified
    $heat = 1;

    if (isset($_POST['heat'])) {
      $heat = $_POST['heat'];
    }

    derby_log_info("Heat selected: Round {$current['roundid']} Heat $heat");

    // Attempt to set new heat
    if (!advance_heat($current, $heat, 'json')) {
      derby_log_warning("Failed to advance to Round {$current['roundid']} Heat $heat");
      $ok = false;
    }
  }

  // If now_racing is explicitly set, apply racing state
  if ($ok && isset($_POST['now_racing'])) {
    $racing_on = $_POST['now_racing'] ? 'ON' : 'OFF';
    if (set_racing_state($_POST['now_racing'])) {
      derby_log_info("Racing state set to $racing_on");
      if ($_POST['now_racing']) {
        maybe_apply_racing_scene();
      }
    } else {
      derby_log_error("Failed to set racing state to $racing_on");
      $ok = false;
      write_raceinfo('refused-results', 0);
      $message = isset($_POST['roundid']) ?
        "The first heat in this group has already been run. Please choose a heat without results." :
        "To start racing mode, there must be a valid current heat without results.";

      json_failure('cant_race', $message);
    }
  }
} else {
  json_not_authorized();
  $ok = false;
}

if ($ok) {
  json_success();
}

require('ajax/query.poll.coordinator.inc');
?>