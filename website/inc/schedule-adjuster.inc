<?php

require_once('inc/schedule_utils.inc');
require_once('inc/masterheat.inc');
require_once('inc/kiosks.inc');
require_once('inc/racing-state.inc');
require_once('inc/rounds.inc');

// Time limit for finding the "best" schedule for injection of a single racer.
define("INJECTION_TIME_LIMIT", 10);  // in seconds

// The overall request has to complete in this time, no matter how many racers
// we attempt to inject.
define("OVERALL_TIME_LIMIT", 1 * 60);


function n_runs_per_lane($roundid) {
  global $db;

  // Pick a populated lane
  $lane = read_single_value('SELECT MIN(lane) FROM RaceChart WHERE roundid = :roundid',
                            array(':roundid' => $roundid));
  $nracers = read_single_value('SELECT COUNT(DISTINCT racerid) FROM RaceChart'
                               .' WHERE roundid = :roundid AND lane = :lane',
                               array(':roundid' => $roundid,
                                     ':lane' => $lane));
  $nheats = read_single_value('SELECT COUNT(*) FROM RaceChart'
                               .' WHERE roundid = :roundid AND lane = :lane',
                               array(':roundid' => $roundid,
                                     ':lane' => $lane));
  return intdiv($nheats, $nracers);
}

class ScheduleAdjuster {
  private $roundid;
  private $nlanes;
  private $lane_mask;  // 1's mark masked lanes NOT in use
  private $nlanes_usable;
  private $n_runs_per_lane;
  private $now_running;  // classid, roundid, heat, now_racing

  // $race_chart is an array of heats, each heat being an array of $nlanes
  // elements populated with racerids.  If $race_chart[$h] is null, then the
  // corresponding heat has already been run and cannot be rescheduled.
  private $race_chart;
  private $nheats;
  private $nheats_unraced;
  private $nheats_new;

  // For heats that have already been run and might need to be renumbered due to
  // heats being added or deleted to the race_chart.  Each entry is the heat
  // number of the corresponding already-run heat, or null for a not-yet-run
  // heat.  Initially, $heat_numbers[H] = H + 1 (e.g., the 0th entry is for heat
  // 1), but that can change as the race_chart is updated.
  private $heat_numbers;

  // Set true if the race_chart was updated for departed racer(s), added
  // racer(s), or squeezed-out byes.
  private $chart_modified = false;
  // We can't prove that adjustment is always possible.  If we attempted a
  // change but couldn't complete it, race_chart may be modified but shouldn't
  // be written back to the database.
  private $adjustment_failed = false;

  private $has_byes = false;  // Are there any byes in the existing chart?

  // An array indexed by lane, each value being an array of heat indices with
  // byes for that lane.
  private $byes;

  // Deadline (as a time() value) to give up searching for an optimal solution.
  private $deadline;
  private $keep_going = true;

  private $best_proposal = null;  // array( 'score', 'injection_heats', 'displacement_heats' )
  private $nproposals;

  private $trace = null;
  public $times = array();
  private $time0;

  public function to_json() {
    return array('roundid' => $this->roundid,
                 'nlanes' => $this->nlanes,
                 'lane_mask' => $this->lane_mask,
                 'nlanes_usable' => $this->nlanes_usable,
                 'n_runs_per_lane' => $this->n_runs_per_lane,
                 'race_chart' => $this->race_chart,
                 'heat_numbers' => $this->heat_numbers,
                 'nheats' => $this->nheats,
                 'nheats_unraced' => $this->nheats_unraced,
                 'nheats_new' => $this->nheats_new,
                 'has_byes' => $this->has_byes,
                 'best_proposal' => $this->best_proposal,
                 'nproposals' => $this->nproposals,
                 'trace' => $this->trace,
                 'times' => $this->times,
    );
  }

  public function chart_debug() {
    return array_map(function(&$ht) {
      if ($ht === null)
        return $ht;
      return implode(" ", array_map(function($r) { return ($r === null) ? "-" : $r; }, $ht));
    },
      $this->race_chart);
  }

  public function __construct($roundid, $trace = false) {
    $this->time0 = time();
    $this->roundid = $roundid;
    $this->nlanes = get_lane_count();
    $this->lane_mask = intval(read_raceinfo('unused-lane-mask', 0));
    $this->nlanes_usable = $this->nlanes - count_one_bits($this->lane_mask);
    $this->n_runs_per_lane = n_runs_per_lane($roundid);
    $this->now_running = get_running_round();
    $this->load_race_chart();

    $heats_raced = 0;
    for ($h = 0; $h < count($this->heat_numbers); ++$h) {
      if ($this->heat_numbers[$h] !== null) {
        $this->race_chart[$h] = null;
        ++$heats_raced;
      }
    }
    $this->nheats = count($this->race_chart);
    $this->nheats_unraced = $this->nheats - $heats_raced;
    if ($trace) {
      $this->trace = array( 'trace', $this->to_json() );
    }
    $this->times['constructed'] = time() - $this->time0;
  }

  public function updated_race_chart() {
    if (!$this->chart_modified || $this->adjustment_failed) {
      return null;
    }
    return $this->race_chart;
  }

  public function renumbering_map() {
    $value = array();

    for ($h = 0; $h < count($this->heat_numbers); ++$h) {

      if ($this->heat_numbers[$h] === null ||
          $this->heat_numbers[$h] == $h + 1) {
        continue;
      }
      $fromheat = $this->heat_numbers[$h];
      $toheat = $h + 1;
      while ($toheat >= count($value)) {
        $value[] = null;
      }
      $value[$toheat] = $fromheat;
      if ($this->trace) $this->trace[] = "Renumber heat $fromheat to be heat $toheat";
    }

    if ($this->trace) $this->trace[] = array('renumbering_map', $value);
    return $value;
  }

  private function load_race_chart() {
    global $db;
    $this->race_chart = array();
    $this->heat_numbers = array();
    $stmt = $db->prepare('SELECT heat, lane, racerid,'
                         .' (finishtime IS NOT NULL'
                         .'      OR finishplace IS NOT NULL) AS has_result'
                         .' FROM RaceChart'
                         .' WHERE roundid = :roundid'
                         .' ORDER BY heat, lane');
    $stmt->execute(array(':roundid' => $this->roundid));
    foreach ($stmt as $row) {
      while ($row['heat'] > count($this->race_chart)) {
        $this->race_chart[] = array_fill(0, $this->nlanes, null);
        $this->heat_numbers[] = null;
      }
      if ($row['has_result']) {
        $this->heat_numbers[$row['heat'] - 1] = $row['heat'];
      }
      $this->race_chart[$row['heat'] - 1][$row['lane'] - 1] = intval($row['racerid']);
    }

    $this->look_for_byes();

    return $completed_heat_indices;
  }

  private function look_for_byes() {
    $this->has_byes = false;
    $this->byes = array_fill(0, $this->nlanes, null);
    for ($lane = 0; $lane < $this->nlanes; ++$lane) {
      $this->byes[$lane] = array();
      if (($this->lane_mask & (1 << $lane)) == 0) {  // Active lane
        for ($h = 0; $h < $this->nheats; ++$h) {
          if ($this->race_chart[$h] !== null && $this->race_chart[$h][$lane] === null) {
            $this->byes[$lane][] = $h;
            $this->has_byes = true;
          }
        }
      }
    }
    return $this->has_byes;
  }


  // An assoc of assocs to keep track of how many times each pair of racers
  // appear in the same heat.
  private function compute_matchups($replacements = false) {
    if ($replacements === false) {
      $replacements = array();
    }
    $nheats = count($this->race_chart);
    $matchups = array();
    for ($h = 0; $h < $nheats; ++$h) {
      $heat = &$this->race_chart[$h];
      if (isset($replacements[strval($h)])) {
        $heat = &$replacements[strval($h)];
      }

      foreach ($heat as $racer1) {
        if ($racer1 === null) {
          continue;
        }
        if (!isset($matchups[$racer1])) {
          $matchups[$racer1] = array();
        }
        foreach ($heat as $racer2) {
          if ($racer2 === null || intval($racer1) >= intval($racer2)) {
            continue;
          }
          if (!isset($matchups[$racer1][$racer2])) {
            $matchups[$racer1][$racer2] = 0;
          }
          ++$matchups[$racer1][$racer2];
        }
      }
    }
    return $matchups;
  }

  private function compute_matchup_stats(&$matchups) {
    $nracers = count($matchups);
    if ($nracers <= 1) return array('nracers' => $nracers);
    $mean = 0;
    foreach ($matchups as $racer1 => &$pairings) {
      foreach ($pairings as $racer2 => $m) {
        $mean += 2 * $m;
      }
    }
    $mean = $mean / ($nracers * ($nracers - 1));
    unset($pairings);

    $sigma2 = 0;
    foreach ($matchups as $racer1 => &$pairings) {
      foreach ($pairings as $racer2 => $m) {
        $sigma2 -= 2 * (2 * $m * $mean - $m * $m);
      }
    }
    $sigma2 = $mean * $mean + $sigma2 / ($nracers * ($nracers - 1));

    return array('nracers' => $nracers,
                 'mean' => $mean,
                 'variance' => $sigma2);
  }

  private function summarize_matchups(&$matchups) {
    $summary = array();
    foreach ($matchups as $racer1 => &$pairings) {
      foreach ($pairings as $racer2 => $m) {
        $summary[] = array(intval($racer1), intval($racer2), $m);
      }
    }
    return $summary;
  }

  // Remove (convert to byes) the appearance of any racer that's no longer in
  // the round's Roster.
  public function remove_departed() {
    global $db;
    $stmt = $db->prepare('SELECT DISTINCT racerid '.sql_for_departed(':roundid'));
    $stmt->execute(array(':roundid' => $this->roundid));
    $departed = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);
    foreach ($departed as $gone) {
      $this->has_byes = true;
      foreach ($this->race_chart as &$heat) {
        if ($heat != null) {
          for ($lane = 0; $lane < $this->nlanes; ++$lane) {
            if ($heat[$lane] == $gone) {
              $heat[$lane] = null;
              $this->chart_modified = true;
              if ($this->trace) {
                $this->trace[] = "Removed departed racer $gone from 0-based lane $lane";
                $this->trace[] = $this->chart_debug();
              }
            }
          }
        }
      }
    }
    $this->look_for_byes();
  }

  public function squeeze_out_byes() {
    while ($this->look_for_byes()) {
      if ($this->trace) {
        $this->trace[] = "Squeezing out byes: ".json_encode($this->byes);
      }
      for ($lane = 0; $lane < $this->nlanes; ++$lane) {
        if (($this->lane_mask & (1 << $lane)) == 0 &&  // Active lane
            count($this->byes[$lane]) == 0) {
          if ($this->trace) {
            $this->trace[] = "No byes available for lane $lane";
          }
          return;
        }
      }
      if (!$this->squeeze_out_one_heat_of_byes()) {
        if ($this->trace) $this->trace[] = "squeeze_out_byes giving up.";
        return;
      }
    }
  }

  private function squeeze_out_one_heat_of_byes() {
    for ($h = 0; $h < $this->nheats; ++$h) {
      if ($this->race_chart[$h] == null) {
        continue;
      }

      $relos = array_fill(0, $this->nlanes, null);
      $h_plausible = true;
      for ($lane = 0; $lane < $this->nlanes; ++$lane) {
        if (($this->lane_mask & (1 << $lane)) != 0) {
          if ($this->trace) $this->trace[] = "Lane ".($lane + 1)." is masked out";
          $relos[$lane] = null;
        } else {
          $candidate = $this->race_chart[$h][$lane];
          $relos[$lane] = null;
          foreach ($this->byes[$lane] as $bh) {
            if (in_array($candidate, $this->race_chart[$bh])) {
              if ($this->trace)
                $this->trace[] = "Considering dissolving heat $h: "
                               ."Can't put racer $candidate in lane "
                               .($lane + 1)." of heat $bh: ".json_encode($this->race_chart[$bh]);
              continue;
            }
            $relos[$lane] = $bh;
            break;
          }
          if (!$relos[$lane]) {
            $h_plausible = false;
            break;
          }
        }
      }

      if ($h_plausible) {
        if ($this->trace) {
          $this->trace[] = "Squeezing out heat $h: ".implode(" ", $this->race_chart[$h]);
        }
        for ($lane = 0; $lane < $this->nlanes; ++$lane) {
          if ($relos[$lane] != null) {
            $this->race_chart[$relos[$lane]][$lane] = $this->race_chart[$h][$lane];
          }
        }
        array_splice($this->race_chart, $h, 1);
        array_splice($this->heat_numbers, $h, 1);
        $this->chart_modified = true;
        --$this->nheats;
        --$this->nheats_unraced;
        if ($this->roundid == $this->now_running['roundid']) {
          set_racing_state(false);
        }
        return true;
      }
    }
    return false;
  }

  private $injection_heats;
  private $displacement_heats;

  public function inject_new_racer($new_racer_id) {
    for ($run = 0; $run < $this->n_runs_per_lane; ++$run) {
      if ($this->trace) {
        $this->trace[] = "Injecting for run $run of ".$this->n_runs_per_lane;
      }

      $this->add_minimal_new_heats();
      for ($extra = 0; $extra < $this->nlanes_usable; ++$extra) {
        $this->times["run-$run-extra-$extra-start"] = time() - $this->time0;
        $this->best_proposal = null;
        $this->nproposals = 0;
        $this->inject_new_racer_once($new_racer_id);
        if ($this->best_proposal !== null || !$this->keep_going) {
          if (!$this->keep_going) {
            $this->times["run-$run-timed-out"] = true;
          }
          $this->times["run-$run-injected"] = time() - $this->time0;
          break;
        }

        if ($this->trace) {
          $this->trace[] = "* Trying again after $extra extra heat(s)";
        }
        $this->race_chart[] = array_fill(0, $this->nlanes, null);
        ++$this->nheats;
        ++$this->nheats_new;
      }

      if ($this->best_proposal !== null) {
        $this->race_chart
          = $this->make_new_injection_race_chart($this->best_proposal['injection_heats'],
                                                 $this->best_proposal['displacement_heats'],
                                                 $new_racer_id);
        $this->chart_modified = true;
        $this->times["run-$run-racechart"] = time() - $this->time0;
      } else {
        $this->adjustment_failed = true;
        if ($this->trace) $this->trace[] = "Adjustment failed.";
      }
    }
  }

  private function add_minimal_new_heats() {
    $this->nheats_new = max($this->has_byes ? 0 : 1, $this->nlanes_usable - $this->nheats_unraced);
    if ($this->trace) {
      $this->trace[] = "Minimum $this->nheats_new new heats";
    }

    for ($h = 0; $h < $this->nheats_new; ++$h) {
      $this->race_chart[] = array_fill(0, $this->nlanes, null);
      ++$this->nheats;
    }
  }

  private function inject_new_racer_once($new_racer_id) {
    $this->deadline = time() + intdiv(INJECTION_TIME_LIMIT, $this->n_runs_per_lane);
    $this->keep_going = true;
    $this->best_proposal = null;

    $this->injection_heats = array_fill(0, $this->nlanes, null);
    $this->displacement_heats = array_fill(0, $this->nlanes, null);
    $this->inject_new_racer_at_lane($new_racer_id, /*$new_racer_lane*/0);
  }

  private function inject_new_racer_at_lane($new_racer_id, $new_racer_lane) {
    if ($this->trace) {
      $this->trace[] = "inject_new_racer_at_lane $new_racer_lane: "
                     .implode(" ", array_filter($this->injection_heats));
    }
    if (time() > $this->deadline) {
      $this->keep_going = false;
      return;
    }
    if ($new_racer_lane >= $this->nlanes) {
      if ($this->trace) {
        $this->trace[] = "Proposal! ".implode(" ", array_filter($this->injection_heats));
      }
      $this->consider_proposal($new_racer_id);
      if (!$this->keep_going) {
        return;
      }
    } else {
      if (($this->lane_mask & (1 << $new_racer_lane)) != 0) {
        $this->injection_heats[$new_racer_lane] = null;
        $this->displacement_heats[$new_racer_lane] = null;
        if ($this->trace) {
          $this->trace[] = "decline masked lane $new_racer_lane";
        }
        $this->inject_new_racer_at_lane($new_racer_id, 1 + $new_racer_lane);
      } else {
        for ($heat = 0; $heat < $this->nheats; ++$heat) {
          if (!$this->keep_going) {
            return;
          }
          $this->inject_new_racer_at_lane_in_heat($new_racer_id, $new_racer_lane, $heat);
        }
      }
    }
  }

  private function inject_new_racer_at_lane_in_heat($new_racer_id, $new_racer_lane, $heat) {
    if (time() > $this->deadline) {
      $this->keep_going = false;
      return;
    }
    if ($this->race_chart[$heat] === null ||
        in_array($new_racer_id, $this->race_chart[$heat], true) ||
        in_array($heat, $this->injection_heats, true)) {
      if ($this->trace) {
        if ($this->race_chart[$heat] === null) {
          $reason = "heat finished";
        } else if (in_array($new_racer_id, $this->race_chart[$heat], true)) {
          $reason = "new racer already present";
        } else {
          $reason = "new racer already injected";
        }
        $this->trace[] = "Reject heat $heat for lane $new_racer_lane because $reason: "
                       .implode(" ", array_filter($this->injection_heats));
      }
    } else {
      $displaced = $this->race_chart[$heat][$new_racer_lane];
      $this->injection_heats[$new_racer_lane] = $heat;
      if ($displaced === null) {
        $this->inject_new_racer_at_lane($new_racer_id, 1 + $new_racer_lane);
      } else {
        for ($dheat = $this->nheats - $this->nheats_new; $dheat < $this->nheats; ++$dheat) {
          if (time() > $this->deadline) {
            $this->keep_going = false;
          }
          if (!$this->keep_going) {
            return;
          }
          if ($this->race_chart[$dheat] !== null &&
              !in_array($displaced, $this->race_chart[$dheat], true)) {
            if ($this->trace) {
              $this->trace[] = "Displace racer $displaced to heat $dheat for lane $new_racer_lane: "
                             .implode(" ", array_filter($this->injection_heats));
            }

            $this->displacement_heats[$new_racer_lane] = $dheat;
            $this->race_chart[$dheat][$new_racer_lane] = $displaced;

            $this->inject_new_racer_at_lane($new_racer_id, 1 + $new_racer_lane);

            $this->race_chart[$dheat][$new_racer_lane] = null;
            $this->displacement_heats[$new_racer_lane] = null;
          }
          else if ($this->trace) {
              $this->trace[] = "Can't displace racer $displaced to heat $dheat for lane $new_racer_lane: "
                             .implode(" ", array_filter($this->injection_heats));
          }
        }
      }
      $this->injection_heats[$new_racer_lane] = null;
    }
  }

  private function consider_proposal($new_racer_id) {
    $s0 = time();
    $score = $this->score_proposal($new_racer_id)['stats']['variance'];
    if (time() - $s0 > 1) {
      $this->times["scoring"] = time() - $s0;
    }
    if ($this->trace) {
      $this->trace[] = array('proposal-score' => $score);
    }
    if ($this->best_proposal === null || $this->best_proposal['score'] > $score) {
      $this->best_proposal = array('score' => $score,
                                   'injection_heats' => array_slice($this->injection_heats, 0),
                                   'displacement_heats' => array_slice($this->displacement_heats, 0));
      if ($this->trace) {
        $this->trace[] = 'selected';
      }
      if ($score == 0) {
        $this->keep_going = false;
      }
    }
    ++$this->nproposals;
    if (time() > $this->deadline) {
      $this->keep_going = false;
    }
  }

  private function make_new_injection_race_chart($injection_heats, $displacement_heats,
                                                 $new_racer_id) {
    $chart = array();
    foreach ($this->race_chart as $heat) {
      $chart[] = $heat;
    }
    for ($lane = 0; $lane < $this->nlanes; ++$lane) {
      if ($injection_heats[$lane] === null) {
        continue;
      }
      if ($displacement_heats[$lane] !== null) {
        $chart[$displacement_heats[$lane]][$lane] = $chart[$injection_heats[$lane]][$lane];
      }
      $chart[$injection_heats[$lane]][$lane] = $new_racer_id;
    }
    return $chart;
  }

  private function make_replacement_heats($new_racer_id) {
    $replacements = array();
    for ($lane = 0; $lane < $this->nlanes; ++$lane) {
      $inj = $this->injection_heats[$lane];
      if ($inj === null) {
        continue;
      }
      $heat = $this->race_chart[$inj];
      $heat[$lane] = $new_racer_id;
      $replacements[strval($inj)] = $heat;
    }
    return $replacements;
  }

  private function score_proposal($new_racer_id) {
    $replacements = $this->make_replacement_heats($new_racer_id);
    $matchups = $this->compute_matchups($replacements);
    $stats = $this->compute_matchup_stats($matchups);
    return array('stats' => $stats, // nracers, mean, variance
    );
  }

  // =========================================================
  // Pull-Forward: Fill gaps from dropout by pulling racers from later heats
  // =========================================================

  private $pull_forward_moves = array();
  private $pull_forward_trailing_byes = array();
  private $pull_forward_warnings = array();

  public function get_pull_forward_moves() {
    return $this->pull_forward_moves;
  }

  public function get_pull_forward_trailing_byes() {
    return $this->pull_forward_trailing_byes;
  }

  public function get_pull_forward_warnings() {
    return $this->pull_forward_warnings;
  }

  // Main pull-forward entry point. Removes dropout from all unraced heats,
  // then fills each gap by pulling the nearest available racer from a later
  // heat, cascading until gaps reach the end of the schedule.
  public function pull_forward($dropout_racerid) {
    $this->pull_forward_moves = array();
    $this->pull_forward_trailing_byes = array();
    $this->pull_forward_warnings = array();

    // Phase 1: Find all gaps created by the dropout
    $gap_queue = array();
    for ($h = 0; $h < $this->nheats; ++$h) {
      if ($this->race_chart[$h] === null) continue; // Already raced, immutable
      for ($lane = 0; $lane < $this->nlanes; ++$lane) {
        if ($this->race_chart[$h][$lane] == $dropout_racerid &&
            $this->race_chart[$h][$lane] !== null) {
          $this->race_chart[$h][$lane] = null;
          $gap_queue[] = array($h, $lane);
          $this->chart_modified = true;
          if ($this->trace) {
            $this->trace[] = "Pull-forward: removed dropout racer $dropout_racerid "
                           . "from heat " . ($h + 1) . " lane " . ($lane + 1);
          }
        }
      }
    }

    // Sort by heat ascending (fill soonest gaps first)
    usort($gap_queue, function ($a, $b) { return $a[0] - $b[0]; });

    if ($this->trace) {
      $this->trace[] = "Pull-forward: " . count($gap_queue) . " gap(s) to fill";
    }

    // Phase 2 + 3: Fill gaps with cascade
    while (!empty($gap_queue)) {
      $gap = array_shift($gap_queue);
      $gap_heat = $gap[0];
      $gap_lane = $gap[1];

      $best = $this->find_best_pull_forward_candidate($gap_heat, $gap_lane);

      if ($best === null) {
        // No candidate available — leave as trailing bye
        $this->pull_forward_trailing_byes[] = array(
          'heat' => $gap_heat + 1,
          'lane' => $gap_lane + 1
        );
        if ($this->trace) {
          $this->trace[] = "Pull-forward: no candidate for heat "
                         . ($gap_heat + 1) . " lane " . ($gap_lane + 1) . " — leaving as bye";
        }
        continue;
      }

      // Execute the move
      $pulled_racerid = $best['racerid'];
      $source_heat = $best['source_heat'];
      $source_lane = $best['source_lane'];

      $this->race_chart[$gap_heat][$gap_lane] = $pulled_racerid;
      $this->race_chart[$source_heat][$source_lane] = null;
      $this->chart_modified = true;

      $move = array(
        'gap_heat' => $gap_heat + 1,
        'gap_lane' => $gap_lane + 1,
        'pulled_racerid' => $pulled_racerid,
        'source_heat' => $source_heat + 1,
        'source_lane' => $source_lane + 1,
        'score' => $best['score']
      );
      $this->pull_forward_moves[] = $move;

      if ($this->trace) {
        $this->trace[] = "Pull-forward: moved racer $pulled_racerid from heat "
                       . ($source_heat + 1) . " lane " . ($source_lane + 1)
                       . " to heat " . ($gap_heat + 1) . " lane " . ($gap_lane + 1)
                       . " (score: " . $best['score'] . ")";
      }

      // Check for fairness warnings
      $this->check_pull_forward_warnings($pulled_racerid, $gap_heat);

      // Cascade: the source slot is now a gap
      $gap_queue[] = array($source_heat, $source_lane);
      usort($gap_queue, function ($a, $b) { return $a[0] - $b[0]; });
    }

    // Phase 4: Compression handled by caller via squeeze_out_byes()
    $this->look_for_byes();
  }

  // Find the best racer to pull from a later heat into the gap.
  // Returns null if no candidate is available.
  private function find_best_pull_forward_candidate($gap_heat, $gap_lane) {
    $best = null;
    $best_score = PHP_INT_MAX;

    for ($h = $gap_heat + 1; $h < $this->nheats; ++$h) {
      if ($this->race_chart[$h] === null) continue; // Already raced

      for ($lane = 0; $lane < $this->nlanes; ++$lane) {
        if (($this->lane_mask & (1 << $lane)) != 0) continue; // Masked lane

        $candidate = $this->race_chart[$h][$lane];
        if ($candidate === null) continue; // Bye slot

        // Hard constraint: candidate must not already be in the gap heat
        if (in_array($candidate, $this->race_chart[$gap_heat], true)) continue;

        // Score: lower is better
        $score = $this->score_pull_forward_candidate($candidate, $gap_heat, $gap_lane, $h);

        if ($score < $best_score) {
          $best_score = $score;
          $best = array(
            'racerid' => $candidate,
            'source_heat' => $h,
            'source_lane' => $lane,
            'score' => $score
          );
        }
      }

      // If we found a candidate in this heat with no consecutive penalty,
      // no need to search further heats (proximity only gets worse)
      if ($best !== null && $best['source_heat'] == $h && $best_score < 5000) {
        break;
      }
    }

    return $best;
  }

  // Score a candidate for pull-forward. Lower is better.
  private function score_pull_forward_candidate($candidate_racerid, $gap_heat, $gap_lane, $source_heat) {
    // Proximity: prefer closest heat
    $proximity = ($source_heat - $gap_heat) * 100;

    // Consecutive penalty: would this racer race back-to-back?
    $consecutive_penalty = 0;
    if ($gap_heat > 0 && $this->race_chart[$gap_heat - 1] !== null) {
      if (in_array($candidate_racerid, $this->race_chart[$gap_heat - 1], true)) {
        $consecutive_penalty += 5000;
      }
    }
    if ($gap_heat + 1 < $this->nheats && $this->race_chart[$gap_heat + 1] !== null) {
      if (in_array($candidate_racerid, $this->race_chart[$gap_heat + 1], true)) {
        $consecutive_penalty += 5000;
      }
    }

    // Lane penalty: candidate already used this lane in another heat
    $lane_penalty = 0;
    for ($h = 0; $h < $this->nheats; ++$h) {
      if ($h == $gap_heat || $h == $source_heat) continue;
      if ($this->race_chart[$h] === null) continue;
      if ($this->race_chart[$h][$gap_lane] == $candidate_racerid) {
        $lane_penalty += 200;
      }
    }

    return $proximity + $consecutive_penalty + $lane_penalty;
  }

  // Check and record fairness warnings for a pull-forward move.
  private function check_pull_forward_warnings($racerid, $placed_heat) {
    if ($placed_heat > 0 && $this->race_chart[$placed_heat - 1] !== null) {
      if (in_array($racerid, $this->race_chart[$placed_heat - 1], true)) {
        $this->pull_forward_warnings[] = array(
          'type' => 'consecutive',
          'racerid' => $racerid,
          'heats' => array($placed_heat, $placed_heat + 1)
        );
      }
    }
    if ($placed_heat + 1 < $this->nheats && $this->race_chart[$placed_heat + 1] !== null) {
      if (in_array($racerid, $this->race_chart[$placed_heat + 1], true)) {
        $this->pull_forward_warnings[] = array(
          'type' => 'consecutive',
          'racerid' => $racerid,
          'heats' => array($placed_heat + 1, $placed_heat + 2)
        );
      }
    }
  }

  // Get a snapshot of the current unraced chart entries for undo purposes.
  public function snapshot_unraced_chart() {
    $snapshot = array();
    for ($h = 0; $h < $this->nheats; ++$h) {
      if ($this->race_chart[$h] === null) continue;
      for ($lane = 0; $lane < $this->nlanes; ++$lane) {
        $snapshot[] = array(
          'heat' => $h + 1,
          'lane' => $lane + 1,
          'racerid' => $this->race_chart[$h][$lane]
        );
      }
    }
    return $snapshot;
  }
}

// Writes the modified race chart back to the database, handling heat renumbering.
function update_race_chart($roundid, &$race_chart, &$renumbering_map) {
  global $db;
  // Tear down the unraced heats before re-inserting
  $stmt = $db->prepare('DELETE FROM RaceChart'
                       .' WHERE roundid = :roundid'
                       .'  AND finishtime IS NULL'
                       .'  AND finishplace IS NULL');
  $stmt->execute(array(':roundid' => $roundid));

  $stmt = $db->prepare('UPDATE RaceChart SET heat = :toheat'
                       .' WHERE roundid = :roundid AND heat = :fromheat');
  $more_renumbering = true;
  while ($more_renumbering) {
    $more_renumbering = false;
    for ($h = 1; $h < count($renumbering_map); ++$h) {
      if ($renumbering_map[$h] === null) {
        continue;
      } else if ($renumbering_map[$h] < count($renumbering_map) &&
                 $renumbering_map[$renumbering_map[$h]] !== null) {
        $more_renumbering = true;
      } else {
        $stmt->execute(array(':roundid' => $roundid,
                             ':fromheat' => $renumbering_map[$h],
                             ':toheat' => $h));
        $renumbering_map[$h] = null;
      }
    }
  }

  $classid = read_single_value('SELECT classid FROM Rounds WHERE roundid = :roundid',
                               array(':roundid' => $roundid));
  $stmt = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid)'
                       .' VALUES(:roundid, :heat, :lane, :racerid, :classid)');
  for ($h = 0; $h < count($race_chart); ++$h) {
    if ($race_chart[$h] !== null) {
      $heat = &$race_chart[$h];
      for ($lane = 0; $lane < count($heat); ++$lane) {
        if ($heat[$lane] !== null) {
          $stmt->execute(array(':roundid' => $roundid,
                               ':heat' => $h + 1,
                               ':lane' => $lane + 1,
                               ':racerid' => $heat[$lane],
                               ':classid' => $classid));
        }
      }
    }
  }
}
