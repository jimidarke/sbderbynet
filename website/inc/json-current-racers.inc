<?php

require_once('inc/data.inc');
require_once('inc/photo-config.inc');
require_once('inc/name-mangler.inc');
require_once('inc/schema_version.inc');

// Expects $now_running array with roundid and heat elements

// Pass a photo_render value to include a photo URL for each racer.
// $photo_render if a PhotoRender or false
function json_current_racers(&$now_running, $name_style, $photo_render, $photo_render2 = false) {
  global $db;

  $use_subgroups = use_subgroups();
  $time_format = get_finishtime_formatting_string();

  // LEFT JOINs (not INNER) so roster-less ad-hoc rows — racerid NULL, no matching
  // RegistrationInfo/Ranks — still appear. For those the pinny comes from
  // RaceChart.display_pinny (the coordinator-typed number); for normal scheduled
  // racing it comes from RegistrationInfo.carnumber. The race server reads this
  // 'carnumber' field as the lane pinny (derbyapi aliases it to racerid), so no
  // Python change is needed. display_pinny exists only at schema >= 18.
  $stmt = $db->prepare('SELECT lane, RegistrationInfo.racerid,'
                       .(schema_version() >= 18
                         ? ' COALESCE(RaceChart.display_pinny, RegistrationInfo.carnumber) AS carnumber,'
                         : ' RegistrationInfo.carnumber AS carnumber,')
                       .' lastname, firstname, carname, rank,'
                       .' finishtime, finishplace, imagefile, '
                       .(schema_version() >= 2 ? 'carphoto' : "'' AS carphoto").', '
                       .(schema_version() >= PARTITION_SCHEMA ? ' note' : "'' AS note")
                       .' FROM RaceChart'
                       .' LEFT JOIN RegistrationInfo ON RaceChart.racerid = RegistrationInfo.racerid'
                       .' LEFT JOIN Ranks ON RegistrationInfo.rankid = Ranks.rankid'
                       .' WHERE roundid = :roundid'
                       .' AND heat = :heat'
                       .' ORDER BY lane');
  $stmt->execute(array(':roundid' => $now_running['roundid'],
                       ':heat' => $now_running['heat']));
  $racers = array();

  foreach ($stmt as $row) {
    $racer = array(
      'lane' => $row['lane'],
      'racerid' => $row['racerid'],
      'name' => mangled_name($row, $name_style),
      'carname' => $row['carname'],
      'carnumber' => $row['carnumber'],
      'note' => $row['note'],
      'photo' => $photo_render ? $photo_render->url_for_row($row) : '',
      'finishtime' => $row['finishtime'] ? sprintf($time_format, $row['finishtime']) : '',
      'finishplace' => $row['finishplace'] ? $row['finishplace'] : '');
    if ($photo_render2) {
      $racer['photo2'] = $photo_render2->url_for_row($row);
    }
    if ($use_subgroups) {
      $racer['subgroup'] = $row['rank'];
    }
    $racers[] = $racer;
  }

  return $racers;
}
?>