<?php
// Heat scheduling with configurable weights - reorders heats to optimize
// race counts and avoid consecutive races for the same racer.

require_once('inc/schedule_rough.inc');
require_once('inc/schedule_utils.inc');

// Fetch user-configurable weights from the settings
$race_count_weight = read_raceinfo('heat-counts', 10);
$consecutive_weight = read_raceinfo('avoid-consecutive', 1000);
$repeat_weight = read_raceinfo('avoid-same-lane', 1000);
$weight_group_weight = read_raceinfo('group-weighted-cars', 0); // Default: 0 (no effect)

// Ensures race counts remain balanced across all cars
function rate_race_counts(&$next_heat, $n_prev_heats, &$appearances) {
    global $race_count_weight;
    $nlanes = count($next_heat);
    $ncars = count($appearances);
    $new_appearances = $appearances;

    foreach ($next_heat as $car) {
        ++$new_appearances[$car];
    }

    $deviation = 0;
    $target = (($n_prev_heats + 1) * $nlanes) / $ncars;
    foreach ($new_appearances as $count) {
        $deviation += ($count - $target) * ($count - $target);
    }

    return $deviation * $race_count_weight;
}

// Windowed soft penalty: any same-racer reuse inside [1..min_heat_gap-1] heats
// is charged a linearly-decaying penalty (full weight at gap=1, ~zero at the
// window edge).  min_heat_gap=0 collapses to legacy N vs N+1 behaviour.
function rate_consecutive(&$next_heat, $current_heat_index,
                          &$last_appearance, &$last_lane, $min_heat_gap) {
    global $consecutive_weight, $repeat_weight;
    $result = 0;
    $window = $min_heat_gap > 0 ? $min_heat_gap : 2;  // legacy: only gap=1 triggers

    for ($lane = 0; $lane < count($next_heat); ++$lane) {
        $car = $next_heat[$lane];
        if (!isset($last_appearance[$car])) continue;
        $gap = $current_heat_index - $last_appearance[$car];
        if ($gap <= 0 || $gap >= $window) continue;
        // Linear ramp: gap=1 -> full weight (preserves legacy behaviour when
        // window collapses to 2), gap=window-1 -> ~1/window of weight.
        $result += (int)round($consecutive_weight * ($window - $gap + 1) / $window);
        if (isset($last_lane[$car]) && $last_lane[$car] == $lane) {
            $result += $repeat_weight;
        }
    }
    return $result;
}

// Scores a potential next heat based on fairness rules
function rate_next_heat($current_heat_index, &$next_heat, &$appearances,
                        &$last_appearance, &$last_lane, $min_heat_gap) {
    $rating = rate_race_counts($next_heat, $current_heat_index, $appearances);
    if ($current_heat_index > 0) {
        $rating += rate_consecutive($next_heat, $current_heat_index,
                                    $last_appearance, $last_lane, $min_heat_gap);
    }
    return $rating;
}

// Generates the ordered race schedule
function make_ordered_schedule($roundid, $nlanes, $ncars, $n_times_per_lane, $max_runs_per_car, $trace, $group_weighted_cars, $avoid_consecutive, $avoid_same_lane, $min_heat_gap = 0) {
    $rough = make_rough_schedule($nlanes, $ncars, $n_times_per_lane, $max_runs_per_car, $trace);
    if (empty($rough)) {
        return $rough;
    }

    // Track the number of times each car appears
    $appearances = array_fill(0, $ncars, 0);
    // Track the heat index (1-based to match heat numbering) and lane of each
    // racer's most recent appearance.  Used for the windowed rest penalty.
    $last_appearance = array();
    $last_lane = array();

    $ordered = array();
    for ($round = 0; $round < $n_times_per_lane; ++$round) {
        for ($car_index = 0; $car_index < $ncars; ++$car_index) {
            $best_heat_index = -1;
            $best_heat_score = PHP_INT_MAX;
            $current_heat_index = count($ordered) + 1;  // 1-based

            for ($rough_i = 0; $rough_i < count($rough); ++$rough_i) {
                if ($rough[$rough_i]) {
                    $score = rate_next_heat($current_heat_index, $rough[$rough_i],
                                            $appearances, $last_appearance,
                                            $last_lane, $min_heat_gap);
                    if ($score < $best_heat_score) {
                        $best_heat_score = $score;
                        $best_heat_index = $rough_i;
                    }
                }
            }

            if ($best_heat_index == -1) {
                continue;
            }

            $chosen = $rough[$best_heat_index];
            $rough[$best_heat_index] = NULL;
            foreach ($chosen as $lane => $car) {
                ++$appearances[$car];
                $last_appearance[$car] = $current_heat_index;
                $last_lane[$car] = $lane;
                if ($max_runs_per_car > 0 && $appearances[$car] > $max_runs_per_car) {
                    return $ordered;
                }
            }
            $ordered[] = $chosen;
        }
    }

    return $ordered;
}

?>