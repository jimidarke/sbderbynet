 <?php
require_once('inc/json-current-heat.inc');
require_once('inc/autoadvance.inc');
require_once('inc/ordinals.inc');

require_once('inc/rounds.inc');

$now_running = get_running_round();

// $_GET['roundid']
$roundid = $now_running['roundid'];
if (isset($_GET['roundid'])) $roundid = $_GET['roundid'];
$with_details = isset($_GET['details']);  // Set for testing

json_out('schedule-signature', schedule_signature());

$use_points = read_raceinfo_boolean('use-points');
$time_format = 'x'.get_finishtime_formatting_string();

$results = array();
$stmt = $db->prepare('SELECT'
                     .' resultid, Rounds.roundid, heat, lane, racerid, finishtime, finishplace, completed'
                     .' FROM Rounds'
                     .' INNER JOIN RaceChart'
                     .' ON RaceChart.roundid = Rounds.roundid'
                     .' WHERE RaceChart.roundid = :roundid'
                     .'  OR completed > '.db_compare_completed(':since'));
$stmt->execute(array(':roundid' => $roundid,
                     // Include new results from the last 5 minutes, even if not
                     // in the same round
                     ':since' => date('Y-m-d H:i:s', time() - 300)));
foreach ($stmt as $row) {
  if (!isset($row['finishtime']) && !isset($row['finishplace'])) {
    $val = '--';
  } else if ($use_points) {
    $val = ordinal($row['finishplace']);
  } else {
    $val = sprintf($time_format, $row['finishtime']);
  }
  $result = $with_details ? $row : array('resultid' => $row['resultid']);
  $result['outcome'] = $val;
  $results[] = $result;
}
json_out('results', $results);

json_out('current-heat', json_current_heat($now_running));

$next = get_next_heat($now_running, 'next');
if ($next !== false) {
  json_out('next-heat', array('roundid' => $next['roundid'],
                              'heat' => $next['heat']));
}

// ---------------------------------------------------------------------------
// racer_summaries — per-racer aggregates for the results-by-racer kiosk.
// Keyed by roundid; the paginator picks the round to display from
// current-heat.roundid. Each racer entry includes: best_ms, avg_ms,
// runs_done, runs_total, and an ordered runs[] array of times.
// ---------------------------------------------------------------------------
require_once('inc/photo-config.inc');
require_once('inc/name-mangler.inc');
require_once('inc/schema_version.inc');

$show_racer_photos = read_raceinfo_boolean('show-racer-photos-rr');
$show_car_photos   = read_raceinfo_boolean('show-car-photos-rr');
$name_style        = read_name_style();
$time_format_plain = get_finishtime_formatting_string();
$head_render       = $show_racer_photos ? headshots()->lookup(RENDER_RACER_RESULTS) : false;
$car_render        = ($show_car_photos && schema_version() >= 2)
                     ? car_photo_repository()->lookup(RENDER_RACER_RESULTS)
                     : false;

$summary_sql =
   'SELECT RegistrationInfo.racerid,'
  .' carnumber, firstname, lastname, imagefile,'
  .(schema_version() >= 2 ? ' carphoto,' : '')
  .' Rounds.roundid, RaceChart.heat, RaceChart.lane,'
  .' RaceChart.finishtime, RaceChart.finishplace, RaceChart.completed'
  .' FROM RaceChart'
  .' INNER JOIN RegistrationInfo ON RegistrationInfo.racerid = RaceChart.racerid'
  .' INNER JOIN Roster ON Roster.racerid = RegistrationInfo.racerid'
  .' INNER JOIN Rounds ON Rounds.roundid = Roster.roundid'
  .' WHERE Rounds.roundid = RaceChart.roundid'
  .' AND Rounds.roundid = :roundid'
  .' ORDER BY carnumber, RaceChart.heat, RaceChart.lane';

$summary_stmt = $db->prepare($summary_sql);
$summary_stmt->execute(array(':roundid' => $roundid));

$summaries = array();   // racerid => row
foreach ($summary_stmt as $row) {
  $rid = $row['racerid'];
  if (!isset($summaries[$rid])) {
    $photo = '';
    if ($head_render && !empty($row['imagefile'])) {
      $photo = $head_render->url_for_row($row);
    }
    if (!$photo && $car_render && !empty($row['carphoto'])) {
      $photo = $car_render->url_for_row($row);
    }
    $summaries[$rid] = array(
      'racerid'     => (int)$rid,
      'carnumber'   => $row['carnumber'],
      'name'        => mangled_name($row, $name_style),
      'photo'       => $photo ? $photo : '',
      'roundid'     => (int)$row['roundid'],
      'runs_total'  => 0,
      'runs_done'   => 0,
      'best_ms'     => null,
      'avg_ms'      => null,
      '_sum_ms'     => 0.0,
      'runs'        => array(),
    );
  }
  $s = &$summaries[$rid];
  $s['runs_total']++;
  $finished = !empty($row['completed']) && isset($row['finishtime']);
  $time_ms = $finished ? round(((float)$row['finishtime']) * 1000) : null;
  if ($finished) {
    $s['runs_done']++;
    $s['_sum_ms'] += $time_ms;
    if ($s['best_ms'] === null || $time_ms < $s['best_ms']) {
      $s['best_ms'] = $time_ms;
    }
  }
  $s['runs'][] = array(
    'lane'     => (int)$row['lane'],
    'heat'     => (int)$row['heat'],
    'time_ms'  => $time_ms,
    'place'    => isset($row['finishplace']) ? (int)$row['finishplace'] : null,
    'finished' => $finished,
  );
  unset($s);
}

$summary_out = array();
foreach ($summaries as $rid => $s) {
  if ($s['runs_done'] > 0) {
    $s['avg_ms'] = (int)round($s['_sum_ms'] / $s['runs_done']);
  }
  unset($s['_sum_ms']);
  $summary_out[] = $s;
}

json_out('racer_summaries', array(
  'roundid'         => (int)$roundid,
  'time_format'     => $time_format_plain,
  'racers'          => $summary_out,
));
?>
