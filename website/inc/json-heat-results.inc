<?php

function json_heat_results($roundid, $heat) {
  global $db;

  $track_length = read_raceinfo('track-length', 40);  // in feet
  $time_format = get_finishtime_formatting_string();

// Simple speed calculation for soapbox derby (no scaling factor)
// $track_length / $finishtime gives feet per second.
//  * 3600 gives feet per hour
//  / 5280 gives miles per hour  
//  * 1.60934 converts miles to kilometers for km/h
  $fps_to_kmh = 3600 / 5280 * 1.60934;

  $stmt = $db->prepare('SELECT lane, finishtime, finishplace, completed'
                       .' FROM RaceChart'
                       .' WHERE roundid = :roundid'
                       .' AND heat = :heat'
                       //.' AND completed IS NOT NULL AND completed != \'\''
                       .' AND (finishtime IS NOT NULL OR finishplace IS NOT NULL)'
                       .' ORDER BY lane');
  $stmt->execute(array(':roundid' => $roundid,
                       ':heat' => $heat));
  $heat_results = array();
  foreach ($stmt as $row) {
    $finishtime = $row['finishtime'];
    $speed = (!is_numeric($finishtime) || $finishtime == 0) ? "--" : sprintf("%4.1f", $track_length / $finishtime * $fps_to_kmh);
    $heat_results[] = array(
      'lane' => $row['lane'],
      'time' => sprintf($time_format, $finishtime),
      'place' => $row['finishplace'],
      'speed' => $speed);
  }
  return $heat_results;
}

?>
