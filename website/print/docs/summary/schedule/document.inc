<?php

require_once('inc/data.inc');
require_once('inc/name-mangler.inc');
require_once('inc/schema_version.inc');
require_once('inc/rounds.inc');

class ScheduleDocument extends PrintableSummaryDocument {
  function name() { return "Schedule"; }

  function get_available_options() {
    return array();
  }

  // array with keys:
  //  'left_header_width' in inches
  //  'cell_width' in inches
  //  'racer_font' in points
  protected $sizes;
  
  function StartDocument() {
    $this->initialize_pdf('P', 'in', 'Letter');
  }
 
  function Byes($n) {
    while ($n > 0) {
      $nlanes = get_lane_count_from_results();
      $cell_height = ($nlanes <= 3) ? 0.75 : 0.5;
      $bye_font = ($nlanes <= 3) ? 14 : 10;
      
      $this->pdf->SetFont('Times', '', $bye_font);
      $this->pdf->Cell($this->sizes['cell_width'], $cell_height, 'Bye', 1, 0, "C");
      --$n;
    }
  }

  function Newline() {
    $this->pdf->Ln();
    $nlanes = get_lane_count_from_results();
    // Adjust page break threshold based on cell height to prevent pagination issues
    $page_break_threshold = ($nlanes <= 3) ? 9.25 : 10.0;
    
    if ($this->pdf->GetY() > $page_break_threshold) {
      $this->pdf->AddPage();
    }
  }

  function Draw() {
    global $db;
    $this->pdf->AddPage();

    $nlanes = get_lane_count_from_results();
    // Optimized layout based on number of lanes
    // For 3 lanes, we can use much larger dimensions to take advantage of whitespace
    if ($nlanes <= 3) {
      $this->sizes = array(
        'left_header_width' => 1.5,
        'cell_width' => 1.8,
        'racer_font' => 12);
    } else if ($nlanes <= 6) {
      $this->sizes = array(
        'left_header_width' => 1.25,
        'cell_width' => 1.00,
        'racer_font' => 8);
    } else {
      $this->sizes = array(
        'left_header_width' => 0.75,
        'cell_width' => 0.84,
        'racer_font' => 7);
    }
    $use_master_sched = use_master_sched();
    $name_style = read_name_style();

    // array of {round, groupid, roundname},
    $groups = all_schedule_groups();

    $sql = 'SELECT'
    .' Classes.class, round, heat, lane, finishtime, resultid, completed,'
    .' RegistrationInfo.racerid,'
    .($use_master_sched ? 'round' : 'Rounds.roundid').' as racinggroup,'
    .($use_master_sched ? 'masterheat' : 'heat').' as seq,'
    .' RegistrationInfo.carnumber, RegistrationInfo.firstname, RegistrationInfo.lastname,'
    .' Classes.classid, Rounds.roundid, RaceChart.racerid'
    .' FROM '.inner_join('RaceChart', 'RegistrationInfo', 
                         'RegistrationInfo.racerid = RaceChart.racerid',
                         'Roster', 'Roster.racerid = RegistrationInfo.Racerid',
                         'Rounds', 'Rounds.roundid = Roster.roundid',
                         'Classes', 'Rounds.classid = Classes.classid')
    .' WHERE Rounds.roundid = RaceChart.roundid'
    .' ORDER BY '
    .($use_master_sched
      ? 'round, masterheat, lane'
      : ((schema_version() >= 2 ? 'Classes.sortorder, ' : '')
         .'class, round, heat, lane'));

    $stmt = $db->query($sql);
    
    // Each time through the "groups" loop (which is really rounds), $rs is
    // expected to be populated already.
    $rs = $stmt->fetch(PDO::FETCH_ASSOC);

    $lane = $nlanes;
    foreach ($groups as $group) {
      $roundid = $group['groupid'];
      $round_name = $group['roundname'];
      $this->Newline();
      $this->pdf->SetFont('Arial', 'B', 15);
      $this->pdf->Cell(7.0, 0.5, convert($round_name), /* border */ 0, /* ln */0, "C");

      $seq = -1;
      while ($rs and $rs['racinggroup'] == $roundid) {
        if ($seq <> $rs['seq']) {
          $this->Byes($nlanes - $lane);
          $seq = $rs['seq'];
          $lane = 0;
          $this->Newline();
          
          // Add heat number as first cell in the row with border to match lane cells
          $cell_height = ($nlanes <= 3) ? 0.75 : 0.5;
          $heat_font = ($nlanes <= 3) ? 18 : 15;
          
          $this->pdf->SetFont('Times', '', $heat_font);
          $this->pdf->Cell($this->sizes['left_header_width'], $cell_height,
                           'Heat '.$seq, /* border */ 1, /* ln */ 0, "C");
        }
        $new_lane = $rs['lane'];
        $this->Byes($new_lane - $lane - 1);

        $x = $this->pdf->GetX();
        $y = $this->pdf->GetY();

        // Adjust positioning based on lane count for better readability
        $name_offset = ($nlanes <= 3) ? 0.25 : 0.165;
        $cell_height = ($nlanes <= 3) ? 0.75 : 0.5;
        $carnumber_font = ($nlanes <= 3) ? 18 : 15;
        
        $this->pdf->SetXY($x, $y + $name_offset);
        $this->pdf->SetFont('Times', '', $this->sizes['racer_font']);
        $this->pdf->Cell($this->sizes['cell_width'], $cell_height, convert($rs['firstname'].' '.$rs['lastname']), 0, 0, "C");
        
        $this->pdf->SetXY($x, $y);        
        $this->pdf->SetFont('Times', '', $carnumber_font);
        $this->pdf->Cell($this->sizes['cell_width'], $cell_height, $rs['carnumber'],
                         /* border */ 1, /* ln */ 0, "C");

        $lane = $new_lane;
        $rs = $stmt->fetch(PDO::FETCH_ASSOC);
      }
      $this->Byes($nlanes - $lane);
      $lane = $nlanes;
    }
  }
}
?>