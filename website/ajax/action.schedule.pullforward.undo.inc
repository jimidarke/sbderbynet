<?php

require_once('inc/schedule-adjuster.inc');
require_once('inc/events.inc');

if (!have_permission(CONTROL_RACE_PERMISSION)) {
  json_not_authorized();
  return;
}

$roundid = isset($_POST['roundid']) ? intval($_POST['roundid']) : 0;

if (!$roundid) {
  json_failure('missing_params', 'Missing required parameter: roundid');
  return;
}

// Read stored undo data
$undo_json = read_raceinfo('pull_forward_undo');
if ($undo_json === false) {
  json_failure('no_undo', 'No pull-forward undo data available');
  return;
}

$undo_data = json_decode($undo_json, true);
if (!$undo_data || $undo_data['roundid'] != $roundid) {
  json_failure('wrong_round', 'Undo data does not match the requested round');
  return;
}

// Check that no affected heats have recorded results since the pull-forward
$affected_heats = $undo_data['affected_heats'];
if (!empty($affected_heats)) {
  $placeholders = implode(',', array_fill(0, count($affected_heats), '?'));
  $params = array_merge([$roundid], $affected_heats);
  $results_count = read_single_value(
    "SELECT COUNT(*) FROM RaceChart"
    . " WHERE roundid = ?"
    . " AND heat IN ($placeholders)"
    . " AND (finishtime IS NOT NULL OR finishplace IS NOT NULL)",
    $params
  );
  if ($results_count > 0) {
    json_failure('has_results', 'Cannot undo: some affected heats have already recorded results');
    return;
  }
}

// Restore the original chart by:
// 1. Delete all unraced entries for this round
// 2. Re-insert the snapshot entries
global $db;

try {
  $db->beginTransaction();

  // Delete unraced entries
  $db->prepare(
    'DELETE FROM RaceChart WHERE roundid = :roundid'
    . ' AND finishtime IS NULL AND finishplace IS NULL'
  )->execute(array(':roundid' => $roundid));

  // Get classid
  $classid = read_single_value(
    'SELECT classid FROM Rounds WHERE roundid = :roundid',
    array(':roundid' => $roundid)
  );

  // Re-insert original snapshot
  $stmt = $db->prepare(
    'INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)'
    . ' VALUES(:roundid, :heat, :lane, :racerid, :classid)'
  );

  foreach ($undo_data['snapshot_before'] as $entry) {
    if ($entry['racerid'] !== null) {
      $stmt->execute(array(
        ':roundid' => $roundid,
        ':heat' => $entry['heat'],
        ':lane' => $entry['lane'],
        ':racerid' => $entry['racerid'],
        ':classid' => $classid
      ));
    }
  }

  // Clear undo data
  delete_from_raceinfo('pull_forward_undo');

  // Restore the dropout racer's passedinspection if it was cleared
  if (isset($undo_data['dropout_racerid'])) {
    $db->prepare(
      'UPDATE RegistrationInfo SET passedinspection = 1 WHERE racerid = :racerid'
    )->execute(array(':racerid' => $undo_data['dropout_racerid']));
  }

  $db->commit();

  record_event(EVENT_PULL_FORWARD_UNDO, array(
    'roundid' => $roundid,
    'racerid' => $undo_data['dropout_racerid']
  ));

  assign_master_heats();
  json_success();
  mark_all_kiosks_for_reload();
  require('ajax/query.poll.coordinator.inc');

} catch (Exception $e) {
  $db->rollBack();
  json_failure('undo_failed', 'Failed to undo pull-forward: ' . $e->getMessage());
}
