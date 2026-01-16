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

// Applies penalties for consecutive races and lane repetition when enabled
function rate_consecutive(&$prev_heat, &$next_heat) {
    global $consecutive_weight, $repeat_weight;
    $result = 0;

    for ($lane = 0; $lane < count($next_heat); ++$lane) {
        for ($prev_lane = 0; $prev_lane < count($prev_heat); ++$prev_lane) {
            if ($prev_heat[$prev_lane] == $next_heat[$lane]) {
                $result += $consecutive_weight;
                if ($lane == $prev_lane) {
                    $result += $repeat_weight;
                }
            }
        }
    }
    return $result;
}

// Scores a potential next heat based on fairness rules
function rate_next_heat(&$prev_heat, $n_prev_heats, &$next_heat, &$appearances) {
    $rating = rate_race_counts($next_heat, $n_prev_heats, $appearances);
    if ($n_prev_heats > 0) {
        $rating += rate_consecutive($prev_heat, $next_heat);
    }
    return $rating;
}

// Generates the ordered race schedule
function make_ordered_schedule($roundid, $nlanes, $ncars, $n_times_per_lane, $max_runs_per_car, $trace, $group_weighted_cars, $avoid_consecutive, $avoid_same_lane) {
    $rough = make_rough_schedule($nlanes, $ncars, $n_times_per_lane, $max_runs_per_car, $trace);
    if (empty($rough)) {
        return $rough;
    }

    // Track the number of times each car appears
    $appearances = array_fill(0, $ncars, 0);

    $ordered = array();
    $prev_heat = array();
    for ($round = 0; $round < $n_times_per_lane; ++$round) {
        for ($car_index = 0; $car_index < $ncars; ++$car_index) {
            $best_heat_index = -1;
            $best_heat_score = PHP_INT_MAX;

            for ($rough_i = 0; $rough_i < count($rough); ++$rough_i) {
                if ($rough[$rough_i]) {
                    $score = rate_next_heat($prev_heat, count($ordered), $rough[$rough_i], $appearances);
                    if ($score < $best_heat_score) {
                        $best_heat_score = $score;
                        $best_heat_index = $rough_i;
                    }
                }
            }

            if ($best_heat_index == -1) {
                continue; 
            }

            $prev_heat = $rough[$best_heat_index];
            $rough[$best_heat_index] = NULL;
            foreach ($prev_heat as $car) {
                ++$appearances[$car];
                if ($max_runs_per_car > 0 && $appearances[$car] > $max_runs_per_car) {
                    return $ordered;
                }
            }
            $ordered[] = $prev_heat;
        }
    }

    return $ordered;
}

?>