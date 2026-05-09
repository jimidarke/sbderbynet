<?php // $_GET['roundid'] and $_GET['heat'] identify the "current" heat as the
 // coordinator page sees it.

require_once('inc/aggregate_round.inc');
require_once('inc/json-classes.inc');
require_once('inc/json-current-heat.inc');
require_once('inc/json-current-racers.inc');
require_once('inc/json-heat-results.inc');
require_once('inc/json-last-heat.inc');
require_once('inc/json-replay.inc');
require_once('inc/json-rounds.inc');
require_once('inc/json-timer-state.inc');
require_once('inc/name-mangler.inc');
require_once('inc/racing-state.inc');

// Device status is used by the coordinator to show the status of the timer
require_once('inc/json-device-status.inc');

// print_r($_GET);die;

$now_running = get_running_round();
json_out('current-heat', json_current_heat($now_running));
json_out('racers', json_current_racers($now_running, FULL_NAME, /* photos */ false));
json_out('timer-state', json_timer_state());
json_out('replay-state', json_replay());
json_out('last-heat', json_last_heat());
json_out('refused-results', read_raceinfo('refused-results', 0));
json_out('current-scene', read_raceinfo('current_scene', ''));

json_out('heat-results',
         json_heat_results(isset($_GET['roundid']) ? $_GET['roundid'] : '0',
                           isset($_GET['heat']) ? $_GET['heat'] : '1'));

json_out('classes', json_all_classes());
json_out('rounds', json_all_rounds($now_running));

// Pull-forward undo availability
$pf_undo_json = read_raceinfo('pull_forward_undo');
if ($pf_undo_json !== false) {
  $pf_undo = json_decode($pf_undo_json, true);
  if ($pf_undo) {
    json_out('pull-forward-undo', array(
      'roundid' => $pf_undo['roundid'],
      'dropout_racerid' => $pf_undo['dropout_racerid'],
      'timestamp' => $pf_undo['timestamp']
    ));
  }
}

// Pre-defined aggregate classes that could be scheduled for racing.  Each
// constituent must have raced, or, if an aggregate, itself be available for
// scheduling.
//
// Work through aggregate constituents tc; an aggregate is ready if all its
// racing constituents have raced: there are no unfinished RaceChart entries, or
// there's just no Round for the class (non-racing aggregate).

$nonracing_aggregates = nonracing_aggregate_classids();

$aggregates_ready_to_populate = array();
// $aggregates_ready_to_populate is what gets sent to the dashboard.
// $classids_ready_to_populate is the classids (only) from those aggregates.
$classids_ready_to_populate = array();
do {
  $repeat = false;
  foreach (aggregate_classes() as $agg_class) {
    if (in_array($agg_class['classid'], $nonracing_aggregates) &&
        !in_array($agg_class['classid'], $classids_ready_to_populate)) {
      // $agg_class has no racing rounds (yet), but might be ready to build a roster
      $ready_to_populate = true;
      foreach ($agg_class['constituents'] as $classid) {
        if (!in_array($classid, $classids_ready_to_populate) &&
            read_single_value('SELECT COUNT(*) FROM RaceChart'
                              .' JOIN Rounds'
                              .' ON RaceChart.roundid = Rounds.roundid'
                              .' WHERE Rounds.classid = :classid'
                              .'  AND (completed IS NULL OR completed = \'\')',
                              array(':classid' => $classid)) > 0) {
          $ready_to_populate = false;
          break;
        }
      }
      if ($ready_to_populate) {
        $classids_ready_to_populate[] = $agg_class['classid'];
        $aggregates_ready_to_populate[] = array(
          'classid' => $agg_class['classid'],
          'by-subgroup' => empty($agg_class['rankids']) ? false : true,
          'class' => $agg_class['class']);
        $repeat = true;
      }
    }
  }
} while ($repeat);

json_out('ready-aggregate', $aggregates_ready_to_populate);

// Race state integrity check - detects edge cases where state is inconsistent
json_out('race-integrity', check_race_integrity());

// Emergency broadcast state - for coordinator page to show current emergency status
$emergency_json = read_raceinfo('emergency-broadcast', '');
if (!empty($emergency_json)) {
    $emergency_data = json_decode($emergency_json, true);
    if ($emergency_data && isset($emergency_data['active']) && $emergency_data['active']) {
        json_out('emergency-broadcast', $emergency_data);
    }
}

?>
