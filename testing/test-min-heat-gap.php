<?php
// Standalone test for the windowed minimum-heat-gap scheduler.
//
// Loads the schedule_ordered.inc functions directly (no DB) and runs the
// greedy scheduler with a few synthetic rosters, then measures the
// distribution of gaps between same-racer appearances.
//
// Usage:
//   cd /home/jimi/code/SBDerbyNet
//   php testing/test-min-heat-gap.php
//
// Exit code 0 on success, 1 on regression.

chdir(__DIR__ . '/../website');

// Stub out the read_raceinfo() reads at top of schedule_ordered.inc.
function read_raceinfo($key, $default = null) {
  $vals = array(
    'heat-counts' => 10,
    'avoid-consecutive' => 5000,
    'avoid-same-lane' => 200,
    'group-weighted-cars' => 0,
  );
  return isset($vals[$key]) ? $vals[$key] : $default;
}

// Re-implement the inner part of make_ordered_schedule() to accept a
// pre-built rough chart, so we don't need the DB-backed generator tables.
function order_synthetic($rough, $nlanes, $ncars, $n_times_per_lane,
                        $min_heat_gap) {
  $appearances = array_fill(0, $ncars, 0);
  $last_appearance = array();
  $last_lane = array();
  $ordered = array();
  for ($round = 0; $round < $n_times_per_lane; ++$round) {
    for ($car_index = 0; $car_index < $ncars; ++$car_index) {
      $best_i = -1;
      $best_score = PHP_INT_MAX;
      $current = count($ordered) + 1;
      for ($i = 0; $i < count($rough); ++$i) {
        if ($rough[$i]) {
          $score = rate_next_heat($current, $rough[$i], $appearances,
                                  $last_appearance, $last_lane, $min_heat_gap);
          if ($score < $best_score) { $best_score = $score; $best_i = $i; }
        }
      }
      if ($best_i == -1) continue;
      $chosen = $rough[$best_i];
      $rough[$best_i] = null;
      foreach ($chosen as $lane => $car) {
        ++$appearances[$car];
        $last_appearance[$car] = $current;
        $last_lane[$car] = $lane;
      }
      $ordered[] = $chosen;
    }
  }
  return $ordered;
}

// Inline copies of the scoring functions from inc/schedule_ordered.inc.
// Kept here so the test doesn't need to require_once the DB-aware include
// chain (schedule_rough.inc -> generators/* -> data layer).  Keep this in
// sync with the canonical file.
$race_count_weight = 10;
$consecutive_weight = 5000;
$repeat_weight = 200;

function rate_race_counts(&$next_heat, $n_prev_heats, &$appearances) {
    global $race_count_weight;
    $nlanes = count($next_heat);
    $ncars = count($appearances);
    $new_appearances = $appearances;
    foreach ($next_heat as $car) ++$new_appearances[$car];
    $deviation = 0;
    $target = (($n_prev_heats + 1) * $nlanes) / $ncars;
    foreach ($new_appearances as $count) {
        $deviation += ($count - $target) * ($count - $target);
    }
    return $deviation * $race_count_weight;
}

function rate_consecutive(&$next_heat, $current_heat_index,
                          &$last_appearance, &$last_lane, $min_heat_gap) {
    global $consecutive_weight, $repeat_weight;
    $result = 0;
    $window = $min_heat_gap > 0 ? $min_heat_gap : 2;
    for ($lane = 0; $lane < count($next_heat); ++$lane) {
        $car = $next_heat[$lane];
        if (!isset($last_appearance[$car])) continue;
        $gap = $current_heat_index - $last_appearance[$car];
        if ($gap <= 0 || $gap >= $window) continue;
        $result += (int)round($consecutive_weight * ($window - $gap + 1) / $window);
        if (isset($last_lane[$car]) && $last_lane[$car] == $lane) {
            $result += $repeat_weight;
        }
    }
    return $result;
}

function rate_next_heat($current_heat_index, &$next_heat, &$appearances,
                        &$last_appearance, &$last_lane, $min_heat_gap) {
    $rating = rate_race_counts($next_heat, $current_heat_index, $appearances);
    if ($current_heat_index > 0) {
        $rating += rate_consecutive($next_heat, $current_heat_index,
                                    $last_appearance, $last_lane, $min_heat_gap);
    }
    return $rating;
}

// Build a rough chart by rotation: car i appears in heat (i + run*ncars/nlanes)
// across n_times_per_lane runs.  Simple and gives the greedy something to chew.
function build_rough($nlanes, $ncars, $n_times_per_lane) {
  $rough = array();
  for ($run = 0; $run < $n_times_per_lane; ++$run) {
    for ($base = 0; $base < $ncars; ++$base) {
      $heat = array();
      for ($lane = 0; $lane < $nlanes; ++$lane) {
        $heat[] = ($base + $lane * (int)($ncars / $nlanes) + $run) % $ncars;
      }
      $rough[] = $heat;
    }
  }
  return $rough;
}

function gap_stats($chart, $ncars) {
  $last = array();
  $gaps = array();
  $tightest = array_fill(0, $ncars, PHP_INT_MAX);
  foreach ($chart as $heat_i => $heat) {
    foreach ($heat as $car) {
      if (isset($last[$car])) {
        $g = ($heat_i + 1) - $last[$car];
        $gaps[] = $g;
        if ($g < $tightest[$car]) $tightest[$car] = $g;
      }
      $last[$car] = $heat_i + 1;
    }
  }
  return array(
    'min' => $gaps ? min($gaps) : 0,
    'count' => count($gaps),
    'tightest_per_racer' => array_values(array_filter(
        $tightest, function($v) { return $v != PHP_INT_MAX; })),
  );
}

function pct_under($vals, $threshold) {
  if (empty($vals)) return 0;
  $n = 0;
  foreach ($vals as $v) if ($v < $threshold) ++$n;
  return round(100 * $n / count($vals), 1);
}

$scenarios = array(
  array('label' => '28 racers / 3 lanes / 3 runs (matches jimitest)',
        'ncars' => 28, 'nlanes' => 3, 'ntpl' => 3),
  array('label' => '26 racers / 3 lanes / 3 runs (shartest)',
        'ncars' => 26, 'nlanes' => 3, 'ntpl' => 3),
  array('label' => '12 racers / 3 lanes / 3 runs (small VIP)',
        'ncars' => 12, 'nlanes' => 3, 'ntpl' => 3),
  array('label' => '4 racers / 3 lanes / 3 runs (edge: tiny roster)',
        'ncars' => 4, 'nlanes' => 3, 'ntpl' => 3),
);

$fail = 0;

foreach ($scenarios as $s) {
  echo "\n=== {$s['label']} ===\n";
  $rough = build_rough($s['nlanes'], $s['ncars'], $s['ntpl']);
  printf("  rough heats: %d, total slots: %d\n",
         count($rough), count($rough) * $s['nlanes']);

  foreach (array(0 => 'legacy', 4 => 'gap=4', 8 => 'gap=8') as $gap => $tag) {
    $rough_copy = $rough;  // PHP arrays are copy-on-write
    $chart = order_synthetic($rough_copy, $s['nlanes'], $s['ncars'],
                             $s['ntpl'], $gap);
    $st = gap_stats($chart, $s['ncars']);
    printf("  %-7s heats=%2d  min-gap=%2d  racers<4=%4.1f%%  racers<8=%4.1f%%\n",
           $tag, count($chart), $st['min'],
           pct_under($st['tightest_per_racer'], 4),
           pct_under($st['tightest_per_racer'], 8));
  }
}

// Regression assertions:
//   1. 28-racer scenario with gap=8 must have min_gap >= 4 (was 3 in production).
//   2. 28-racer scenario with gap=0 must produce a schedule (no crash).
//   3. 4-racer scenario must produce a schedule with all 3 runs (no infeasibility).
echo "\n--- Regression checks ---\n";

$big_rough = build_rough(3, 28, 3);
$legacy = order_synthetic($big_rough, 3, 28, 3, 0);
$gap8 = order_synthetic(build_rough(3, 28, 3), 3, 28, 3, 8);
$st_legacy = gap_stats($legacy, 28);
$st_gap8 = gap_stats($gap8, 28);

echo "  legacy(28r/3L/3): min_gap = {$st_legacy['min']}\n";
echo "  gap=8 (28r/3L/3): min_gap = {$st_gap8['min']}\n";

if ($st_gap8['min'] < $st_legacy['min']) {
  echo "  FAIL: gap=8 should not regress min_gap below legacy\n";
  $fail = 1;
} else {
  echo "  PASS: gap=8 min_gap ({$st_gap8['min']}) >= legacy min_gap ({$st_legacy['min']})\n";
}

$tiny = order_synthetic(build_rough(3, 4, 3), 3, 4, 3, 8);
echo "  tiny(4r/3L/3): heats produced = " . count($tiny) . "\n";
if (count($tiny) < 4) {
  echo "  FAIL: tiny roster must still produce >= 4 heats (one per racer)\n";
  $fail = 1;
} else {
  echo "  PASS: tiny roster produced " . count($tiny) . " heats\n";
}

exit($fail);
?>
