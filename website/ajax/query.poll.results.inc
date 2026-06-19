 <?php
require_once('inc/json-current-heat.inc');
require_once('inc/autoadvance.inc');
require_once('inc/ordinals.inc');

require_once('inc/rounds.inc');
require_once('inc/standings.inc');   // sql_scoring_expression()

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

// ---------------------------------------------------------------------------
// score + place — reuse the canonical scoring expression from standings.inc so
// the kiosk number matches the official round standings. One row per racer over
// finished results, with the same filters standings uses (passedinspection,
// exclude, finish-present). sql_scoring_expression honors the 'scoring' setting
// (0=average all, 1=drop slowest, 2=fastest) and use-points.
// ---------------------------------------------------------------------------
$scoring_expr = sql_scoring_expression('finishtime', 'finishplace');
$score_sql =
   'SELECT RaceChart.racerid AS racerid, '.$scoring_expr.' AS score'
  .' FROM RaceChart'
  .' INNER JOIN RegistrationInfo ON RegistrationInfo.racerid = RaceChart.racerid'
  .' INNER JOIN Roster ON Roster.racerid = RaceChart.racerid'
  .'                  AND Roster.roundid = RaceChart.roundid'
  .' WHERE RaceChart.roundid = :roundid'
  .'   AND passedinspection = 1 AND exclude = 0'
  .'   AND (finishtime IS NOT NULL OR finishplace IS NOT NULL)'
  .' GROUP BY RaceChart.racerid';
$score_stmt = $db->prepare($score_sql);
$score_stmt->execute(array(':roundid' => $roundid));

$scored = array();   // racerid => float score
foreach ($score_stmt as $r) {
  if ($r['score'] !== null) $scored[(int)$r['racerid']] = (float)$r['score'];
}

// Rank ascending (lower score = better = 1st). Tie when score equals the
// previous emitted score (asort means $sc >= last, so <= reduces to ==),
// mirroring StandingsTracker exactly (competition ranking 1,1,3).
asort($scored);
$place_by_racer = array();
$rank = 0; $last_place = 0; $last_score = null;
foreach ($scored as $rid => $sc) {
  $rank++;
  if ($last_score !== null && $sc <= $last_score) {
    $place_by_racer[$rid] = $last_place;
  } else {
    $place_by_racer[$rid] = $rank;
    $last_place = $rank;
  }
  $last_score = $sc;
}

$summary_out = array();
foreach ($summaries as $rid => $s) {
  if ($s['runs_done'] > 0) {
    $s['avg_ms'] = (int)round($s['_sum_ms'] / $s['runs_done']);
  }
  unset($s['_sum_ms']);

  if (isset($scored[$rid])) {
    $sc = $scored[$rid];
    $s['score']     = $sc;                       // numeric, for client sort/tiebreak
    $s['place']     = $place_by_racer[$rid];     // 1 = first
    $s['score_str'] = $use_points
                        ? rtrim(rtrim(sprintf('%.2f', $sc), '0'), '.')  // avg place, e.g. "2.5"
                        : sprintf($time_format_plain, $sc);             // plain (no 'x' prefix)
  } else {
    $s['score']     = null;
    $s['place']     = null;       // no finished runs → unplaced → client sorts to top (worst)
    $s['score_str'] = '--';
  }
  $summary_out[] = $s;
}

json_out('racer_summaries', array(
  'roundid'         => (int)$roundid,
  'time_format'     => $time_format_plain,
  'racers'          => $summary_out,
));
?>
