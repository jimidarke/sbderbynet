<?php

require_once('inc/schedule-adjuster.inc');
require_once('inc/events.inc');

// NOTE: this file MUST NOT use a bare `return;` at file scope. The dispatcher
// (`action.php:143`) does `if (!@include 'ajax/...') { json_failure('unrecognized', …) }`,
// and PHP's `include` returns NULL on a bare `return;` — `!NULL === true`,
// so the dispatcher overwrites our outcome with "unrecognized". Fall through
// to end-of-file via if/else-if/else instead.

$roundid          = isset($_POST['roundid'])         ? intval($_POST['roundid'])         : 0;
$dropout_racerid  = isset($_POST['dropout_racerid']) ? intval($_POST['dropout_racerid']) : 0;
$dry_run          = isset($_POST['dry-run'])         && $_POST['dry-run'];
$send_broadcast   = isset($_POST['send_broadcast'])  && $_POST['send_broadcast'];
$trace            = isset($_POST['trace'])           && $_POST['trace'];

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
} else if (!$roundid || !$dropout_racerid) {
  json_failure('missing_params', 'Missing required parameters: roundid and dropout_racerid');
} else {
  // Check that the dropout racer actually has unraced heats in this round
  $unraced_count = read_single_value(
    'SELECT COUNT(*) FROM RaceChart'
    . ' WHERE roundid = :roundid AND racerid = :racerid'
    . ' AND finishtime IS NULL AND finishplace IS NULL',
    array(':roundid' => $roundid, ':racerid' => $dropout_racerid)
  );

  if ($unraced_count == 0) {
    json_failure('no_gaps', 'Racer has no unraced heats in this round to fill');
  } else {
    $adj = new ScheduleAdjuster($roundid, $trace);

    // Take a snapshot before changes for undo capability
    $snapshot_before = $adj->snapshot_unraced_chart();

    // Run the pull-forward algorithm
    $adj->pull_forward($dropout_racerid);

    // Compress trailing byes
    $adj->squeeze_out_byes();

    $moves         = $adj->get_pull_forward_moves();
    $trailing_byes = $adj->get_pull_forward_trailing_byes();
    $warnings      = $adj->get_pull_forward_warnings();

    // Enrich moves with racer names for display
    $enriched_moves = array();
    foreach ($moves as $move) {
      $racer_info = read_single_row(
        'SELECT firstname, lastname, carnumber FROM RegistrationInfo WHERE racerid = :racerid',
        array(':racerid' => $move['pulled_racerid']),
        PDO::FETCH_ASSOC
      );
      $move['racer_name'] = $racer_info ? ($racer_info['firstname'] . ' ' . $racer_info['lastname']) : 'Unknown';
      $move['carnumber']  = $racer_info ? $racer_info['carnumber'] : 0;
      $enriched_moves[] = $move;
    }

    // Enrich warnings with racer names
    $enriched_warnings = array();
    foreach ($warnings as $warning) {
      $racer_info = read_single_row(
        'SELECT firstname, lastname, carnumber FROM RegistrationInfo WHERE racerid = :racerid',
        array(':racerid' => $warning['racerid']),
        PDO::FETCH_ASSOC
      );
      $warning['racer_name'] = $racer_info ? ($racer_info['firstname'] . ' ' . $racer_info['lastname']) : 'Unknown';
      $warning['carnumber']  = $racer_info ? $racer_info['carnumber'] : 0;
      $enriched_warnings[] = $warning;
    }

    // Get dropout racer info
    $dropout_info = read_single_row(
      'SELECT firstname, lastname, carnumber FROM RegistrationInfo WHERE racerid = :racerid',
      array(':racerid' => $dropout_racerid),
      PDO::FETCH_ASSOC
    );

    json_out('proposal', array(
      'dropout' => array(
        'racerid'      => $dropout_racerid,
        'name'         => $dropout_info ? ($dropout_info['firstname'] . ' ' . $dropout_info['lastname']) : 'Unknown',
        'carnumber'    => $dropout_info ? $dropout_info['carnumber'] : 0,
        'gaps_created' => $unraced_count
      ),
      'moves'          => $enriched_moves,
      'trailing_byes'  => $trailing_byes,
      'warnings'       => $enriched_warnings,
      'heats_affected' => count($enriched_moves) + count($trailing_byes)
    ));

    if ($trace) {
      json_out('adjuster', $adj->to_json());
    }

    if ($dry_run) {
      json_success();
    } else {
      // Execute: write the modified chart to the database
      $new_chart = $adj->updated_race_chart();
      if ($new_chart === null) {
        json_failure('no_changes', 'Pull-forward produced no schedule changes');
      } else {
        // Store undo data before committing
        write_raceinfo('pull_forward_undo', json_encode(array(
          'roundid'          => $roundid,
          'dropout_racerid'  => $dropout_racerid,
          'timestamp'        => time(),
          'snapshot_before'  => $snapshot_before,
          'affected_heats'   => array_unique(array_merge(
            array_column($moves, 'gap_heat'),
            array_column($moves, 'source_heat')
          ))
        )));

        // Mark the dropout racer as not passed inspection (prevents re-scheduling)
        $db->prepare('UPDATE RegistrationInfo SET passedinspection = 0 WHERE racerid = :racerid')
           ->execute(array(':racerid' => $dropout_racerid));

        $renumbering_map = $adj->renumbering_map();
        update_race_chart($roundid, $new_chart, $renumbering_map);
        assign_master_heats();

        record_event(EVENT_PULL_FORWARD, array(
          'roundid' => $roundid,
          'racerid' => $dropout_racerid
        ));

        // Send broadcast if requested
        if ($send_broadcast && !empty($enriched_moves)) {
          $first_move = $enriched_moves[0];
          $broadcast_msg = $first_move['racer_name'] . ' (#' . $first_move['carnumber']
            . ') please report to staging - moved to Heat ' . $first_move['gap_heat'];
          write_raceinfo('broadcast-message', json_encode(array(
            'message'   => $broadcast_msg,
            'duration'  => 30,
            'timestamp' => time(),
            'expires'   => time() + 30
          )));
        }

        json_out('undo_available', true);
        json_success();
        mark_all_kiosks_for_reload();
        require('ajax/query.poll.coordinator.inc');
      }
    }
  }
}
