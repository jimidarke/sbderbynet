<?php

function json_current_heat(&$now_running) {
    // Get use_points setting from RaceInfo table
    $use_points = read_raceinfo_boolean('use-points', false);
    
    $current_heat = array(
        'now_racing' => $now_running['now_racing'] ? true : false,
        'use_master_sched' => isset($now_running['use_master_sched']) ? (bool)$now_running['use_master_sched'] : false,
        'use_points' => $use_points, // Add use_points setting here
        'classid' => isset($now_running['classid']) ? $now_running['classid'] : null,
        'roundid' => isset($now_running['roundid']) ? $now_running['roundid'] : null,
        'round' => isset($now_running['round']) ? $now_running['round'] : null,
        'tbodyid' => isset($now_running['use_master_sched']) && $now_running['use_master_sched'] ? 
                     @$now_running['round'] : @$now_running['roundid'],
        'heat' => isset($now_running['heat']) ? $now_running['heat'] : null,
        'number-of-heats' => read_single_value(
            'SELECT MAX(heat) FROM RaceChart WHERE roundid = :roundid',
            array(':roundid' => @$now_running['roundid']), 
            0
        )
    );

    if (use_groups()) {
        $current_heat['class'] = isset($now_running['class']) ? $now_running['class'] : null;
    }

    if (@$now_running['use_master_sched']) {
        $current_heat['masterheat'] = read_single_value(
            'SELECT masterheat FROM RaceChart 
             WHERE roundid = :roundid AND heat = :heat',
            array(
                ':roundid' => $now_running['roundid'],
                ':heat' => $now_running['heat']
            )
        );
        
        $current_heat['max_masterheat'] = read_single_value(
            'SELECT MAX(masterheat) FROM RaceChart'
        );
    }

    return $current_heat;
}

?>
