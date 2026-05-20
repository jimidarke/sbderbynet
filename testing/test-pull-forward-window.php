<?php
// Focused unit test for the windowed pull-forward scoring + warnings.
//
// Mirrors the scoring + warning logic from inc/schedule-adjuster.inc so we
// can drive it without a live DB.  If the canonical file changes, update
// this in lockstep.
//
// Usage:  php testing/test-pull-forward-window.php

function score_pull_forward_candidate(
    $candidate, $gap_heat, $gap_lane, $source_heat,
    $race_chart, $nheats, $min_heat_gap
) {
    $proximity = ($source_heat - $gap_heat) * 100;
    $consecutive = 0;
    $window = $min_heat_gap > 0 ? $min_heat_gap : 2;
    for ($d = 1; $d < $window; ++$d) {
        $weight = (int)round(5000 * ($window - $d + 1) / $window);
        foreach (array($gap_heat - $d, $gap_heat + $d) as $h) {
            if ($h < 0 || $h >= $nheats) continue;
            if ($h == $source_heat) continue;
            if ($race_chart[$h] === null) continue;
            if (in_array($candidate, $race_chart[$h], true)) {
                $consecutive += $weight;
            }
        }
    }
    $lane_penalty = 0;
    for ($h = 0; $h < $nheats; ++$h) {
        if ($h == $gap_heat || $h == $source_heat) continue;
        if ($race_chart[$h] === null) continue;
        if ($race_chart[$h][$gap_lane] == $candidate) $lane_penalty += 200;
    }
    return $proximity + $consecutive + $lane_penalty;
}

function check_warnings($racerid, $placed_heat, $race_chart, $nheats, $min_heat_gap) {
    $warnings = array();
    $window = $min_heat_gap > 0 ? $min_heat_gap : 2;
    $closest = null;
    $closest_heat = null;
    for ($d = 1; $d < $window; ++$d) {
        foreach (array($placed_heat - $d, $placed_heat + $d) as $h) {
            if ($h < 0 || $h >= $nheats) continue;
            if ($race_chart[$h] === null) continue;
            if (in_array($racerid, $race_chart[$h], true)) {
                if ($closest === null || $d < $closest) {
                    $closest = $d;
                    $closest_heat = $h;
                }
            }
        }
    }
    if ($closest === null) return $warnings;
    if ($closest == 1) {
        $warnings[] = array('type' => 'consecutive', 'racerid' => $racerid);
    } else if ($min_heat_gap > 0) {
        $warnings[] = array(
            'type' => 'gap-too-tight',
            'racerid' => $racerid,
            'gap' => $closest,
            'min_heat_gap' => $min_heat_gap,
        );
    }
    return $warnings;
}

$pass = 0;
$fail = 0;

function expect($label, $cond) {
    global $pass, $fail;
    if ($cond) { echo "  PASS  $label\n"; ++$pass; }
    else       { echo "  FAIL  $label\n"; ++$fail; }
}

// Chart: 10 heats, 3 lanes.  Racer 1 is in heats 0 and 4.  Racer 2 in heat 7.
// Lane index 0-based.
$chart = array(
    array(1, 2, 3),  // heat 0
    array(4, 5, 6),  // heat 1
    array(7, 8, 9),  // heat 2
    array(10, 11, 12),  // heat 3
    array(1, 13, 14),  // heat 4 -- racer 1's second race
    array(15, 16, 17),  // heat 5
    array(18, 19, 20),  // heat 6
    array(21, 2, 22),   // heat 7
    array(23, 24, 25),  // heat 8
    array(26, 27, 28),  // heat 9
);
$nheats = 10;

echo "--- score_pull_forward_candidate ---\n";

// Filling heat 1 lane 0 (gap) by pulling racer 1 from heat 4:
//   distance from heat 1: d=1 -> heat 0 has racer 1 -> back-to-back-ish.
//   With min_heat_gap=0 (legacy), expect proximity (3 heats * 100 = 300)
//   + 5000 for d=1 violation + 200 lane penalty (racer 1 is in heat 0 lane 0).
$score_legacy = score_pull_forward_candidate(1, 1, 0, 4, $chart, $nheats, 0);
expect("legacy: 5000 for d=1 + 200 lane penalty",
       $score_legacy == 300 + 5000 + 200);

// With min_heat_gap=8, same scenario:
//   d=1: heat 0 contains racer 1 -> weight = 5000*8/8 = 5000
//   d=2..7: no other occurrences
//   + 200 lane penalty for racer 1 in heat 0 lane 0
$score_w8 = score_pull_forward_candidate(1, 1, 0, 4, $chart, $nheats, 8);
expect("window=8: 5000 d=1 + 200 lane penalty",
       $score_w8 == 300 + 5000 + 200);

// Place gap at heat 6 lane 0, pulling racer 2 from heat 7.
//   Source heat = 7 (skipped in penalty loop).
//   d=1..5: no racer 2 in those heats
//   d=6: heat 0 has racer 2 -> weight 5000*(8-6+1)/8 = 5000*3/8 = 1875
//   Lane penalty: racer 2 in heat 0 lane 1 (not lane 0) -> 0
//   Proximity = (7-6)*100 = 100. Total = 100 + 1875 = 1975.
$score_w6 = score_pull_forward_candidate(2, 6, 0, 7, $chart, $nheats, 8);
expect("window=8: d=6 violation costs 1875", $score_w6 == 100 + 1875);

// With min_heat_gap=4, d=6 is outside the window -> no penalty.
$score_w4 = score_pull_forward_candidate(2, 6, 0, 7, $chart, $nheats, 4);
expect("window=4: d=6 outside window, only proximity", $score_w4 == 100);

// Place gap at heat 3 lane 0, pulling racer 1 (currently in heat 4).
//   Source heat = 4, so heat 4 skipped in penalty loop.
//   d=1: heat 2 (no), heat 4 (source, skipped) -> 0
//   d=2: heat 1 (no), heat 5 (no) -> 0
//   d=3: heat 0 (HAS racer 1) -> weight 5000*(8-3+1)/8 = 5000*6/8 = 3750
//   d=4..7: no occurrences
//   Lane penalty: racer 1 in heat 0 lane 0 -> +200
//   Proximity = (4-3)*100 = 100.
$score_d3 = score_pull_forward_candidate(1, 3, 0, 4, $chart, $nheats, 8);
expect("window=8: d=3 (3750) + lane (200) + proximity (100)",
       $score_d3 == 100 + 3750 + 200);

echo "\n--- check_warnings ---\n";

// Placing racer 1 at heat 1: their other race is heat 0 (consecutive).
$w = check_warnings(1, 1, $chart, $nheats, 8);
expect("placing racer 1 at heat 1: consecutive warning",
       count($w) == 1 && $w[0]['type'] == 'consecutive');

// Placing racer 1 at heat 3 with window=8: closest is heat 0 (d=3) or heat 4 (d=1).
// heat 4 is in the chart so it's the closest -> back-to-back.
$w = check_warnings(1, 3, $chart, $nheats, 8);
expect("placing racer 1 at heat 3 with racer in heat 4: consecutive",
       count($w) == 1 && $w[0]['type'] == 'consecutive');

// Placing racer 2 at heat 4 with window=8: racer 2 is in heat 7 (d=3).
$w = check_warnings(2, 4, $chart, $nheats, 8);
expect("placing racer 2 at heat 4: gap-too-tight (d=3, window=8)",
       count($w) == 1 && $w[0]['type'] == 'gap-too-tight'
       && $w[0]['gap'] == 3 && $w[0]['min_heat_gap'] == 8);

// Same scenario with window=0 (legacy): only back-to-back triggers a warning.
$w = check_warnings(2, 4, $chart, $nheats, 0);
expect("legacy: d=3 produces no warning", count($w) == 0);

// Placing racer 1 at heat 6: no other races in [3..9] except heat 4 (d=2).
$w = check_warnings(1, 6, $chart, $nheats, 8);
expect("placing racer 1 at heat 6: gap-too-tight (d=2)",
       count($w) == 1 && $w[0]['type'] == 'gap-too-tight'
       && $w[0]['gap'] == 2);

echo "\n$pass passed, $fail failed\n";
exit($fail > 0 ? 1 : 0);
?>
