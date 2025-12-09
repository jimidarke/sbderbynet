<?php

require_once('inc/data.inc');
require_once('inc/elimination-config.inc');
require_once('inc/name-mangler.inc');
require_once('inc/ordinals.inc');
require_once('inc/schema_version.inc');

/**
 * Elimination Tournament Standings Oracle
 * Provides standings data specifically for elimination tournaments,
 * focusing on current round only with tournament-specific scoring
 */
class EliminationStandingsOracle {
    private $tournament_state;
    private $current_round_config;
    private $use_points;
    private $current_standings;
    
    public function __construct($classid) {
        $this->use_points = read_raceinfo_boolean('use-points');
        
        // Get tournament state
        $this->tournament_state = get_elimination_tournament_state($classid);
        if (!$this->tournament_state) {
            throw new Exception("No active elimination tournament found for class $classid");
        }
        
        // Get current round configuration
        $current_round = $this->tournament_state['current_round'];
        $this->current_round_config = $this->tournament_state['age_group']['rounds'][$current_round - 1];
        
        // Calculate current standings
        $this->current_standings = $this->calculate_current_standings();
    }
    
    /**
     * Calculate standings for current tournament round
     */
    private function calculate_current_standings() {
        global $db;
        
        $classid = $this->tournament_state['tournament']['classid'];
        $current_round = $this->tournament_state['current_round'];
        $scoring_method = $this->current_round_config['scoring_method'];
        
        // Build scoring expression based on tournament configuration
        switch ($scoring_method) {
            case 'total_time':
                $score_expr = 'SUM(rc.finishtime)';
                $order_clause = 'score DESC';  // Reverse order: slowest times first for dramatic reveal
                break;
            case 'best_time':
                $score_expr = 'MIN(rc.finishtime)';
                $order_clause = 'score DESC';  // Reverse order: slowest times first for dramatic reveal
                break;
            case 'average_time':
                $score_expr = 'AVG(rc.finishtime)';
                $order_clause = 'score DESC';  // Reverse order: slowest times first for dramatic reveal
                break;
            case 'placement':
                $score_expr = 'MIN(rc.finishplace)';  // Best placement (1st place = 1, 2nd place = 2, etc.)
                $order_clause = 'score ASC';  // Normal order: 1st place first, 2nd place second, etc.
                break;
            default:
                throw new Exception("Unsupported scoring method: " . $scoring_method);
        }
        
        // Get the round name from the tournament configuration
        $round_name = $this->current_round_config['round_name'];
        
        // Query for current round standings - using round name instead of number
        $sql = "SELECT 
                    ri.racerid,
                    ri.firstname,
                    ri.lastname, 
                    ri.carnumber,
                    ri.carname,
                    c.class,
                    r.rank,
                    COUNT(*) as heats_run,
                    {$score_expr} as score,
                    MIN(rc.finishtime) as best_time,
                    MAX(rc.finishtime) as worst_time
                FROM RaceChart rc
                INNER JOIN RegistrationInfo ri ON rc.racerid = ri.racerid
                INNER JOIN Classes c ON ri.classid = c.classid
                LEFT JOIN Ranks r ON ri.rankid = r.rankid
                WHERE rc.classid = :classid 
                  AND rc.roundid = (
                      SELECT roundid FROM Rounds 
                      WHERE classid = :classid AND round = :round_name 
                      LIMIT 1
                  )
                  AND (
                      (rc.finishtime IS NOT NULL AND rc.finishtime > 0 AND rc.finishtime < 999.0) OR
                      (rc.finishplace IS NOT NULL AND rc.finishplace > 0)
                  )
                GROUP BY ri.racerid, ri.firstname, ri.lastname, ri.carnumber, 
                         ri.carname, c.class, r.rank
                ORDER BY {$order_clause}, ri.lastname, ri.firstname";
        
        $stmt = $db->prepare($sql);
        $stmt->execute([
            ':classid' => $classid,
            ':round_name' => $round_name
        ]);
        
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    /**
     * Get tournament round display name
     */
    public function get_round_display_name() {
        return $this->current_round_config['round_name'];
    }
    
    /**
     * Get class name
     */
    public function get_class_name() {
        global $db;
        return read_single_value(
            'SELECT class FROM Classes WHERE classid = :classid',
            [':classid' => $this->tournament_state['tournament']['classid']]
        );
    }
    
    /**
     * Check if racers are advancing from this round
     */
    public function has_advancement() {
        return isset($this->current_round_config['advance_count']) && 
               $this->current_round_config['advance_count'] > 0;
    }
    
    /**
     * Get number of racers advancing
     */
    public function get_advance_count() {
        return $this->current_round_config['advance_count'] ?? 0;
    }
    
    /**
     * Write standings table headers
     */
    public function write_standings_headers() {
        echo "<tr class='headers'>";
        echo "<th>Place</th>";
        echo "<th>Pinny</th>";
        echo "<th>Name</th>";
        if ($this->has_advancement()) {
            echo "<th>Status</th>";
        }
        echo "<th>Heats</th>";
        echo "<th>Score</th>";
        echo "<th>Best</th>";
        echo "<th>Worst</th>";
        echo "</tr>\n";
    }
    
    /**
     * Write standings table rows
     */
    public function write_standings_rows() {
        $name_style = read_name_style();
        $time_format = get_finishtime_formatting_string();
        $advance_count = $this->get_advance_count();
        $total_racers = count($this->current_standings);
        
        foreach ($this->current_standings as $i => $racer) {
            // For placement scoring, display in normal order; for time scoring, reverse order (slowest first for drama)
            if ($this->current_round_config['scoring_method'] == 'placement') {
                $actual_place = $i + 1; // Normal order: 1st, 2nd, 3rd
            } else {
                $actual_place = $total_racers - $i; // Reverse order: slowest first
            }
            
            // Handle ties - adjust logic based on scoring method
            if ($this->current_round_config['scoring_method'] == 'placement') {
                // For placement, ties are unlikely but check adjacent scores
                if ($i > 0 && $racer['score'] == $this->current_standings[$i-1]['score']) {
                    $display_place = "T$actual_place";
                } else {
                    $display_place = $actual_place;
                }
            } else {
                // For time scoring, check next racer (since we're reversed)
                if ($i < $total_racers - 1 && $racer['score'] == $this->current_standings[$i+1]['score']) {
                    $display_place = "T$actual_place";
                } else {
                    $display_place = $actual_place;
                }
            }
            
            echo "<tr data-racerid='".$racer['racerid']."' class='d".($i & 1)."'>";
            
            // Place
            echo "<td class='place'>$display_place</td>";
            
            // Car Number (zero-padded to 4 digits)
            echo "<td class='carnumber'>".str_pad($racer['carnumber'], 4, '0', STR_PAD_LEFT)."</td>";
            
            // Name
            echo "<td class='name'>".htmlspecialchars(mangled_name($racer, $name_style), ENT_QUOTES, 'UTF-8')."</td>";
            
            // Advancement Status - use actual_place for advancement determination
            if ($this->has_advancement()) {
                $status = '';
                if ($actual_place <= $advance_count) {
                    $status = '<span class="advancing">ADVANCING</span>';
                } else {
                    $status = '<span class="eliminated">Good Try</span>';
                }
                echo "<td class='status'>$status</td>";
            }
            
            // Heats Run
            echo "<td class='heats'>".$racer['heats_run']."</td>";
            
            // Score
            if ($this->current_round_config['scoring_method'] == 'placement') {
                echo "<td class='score'>".ordinal($racer['score'])."</td>";
            } else if ($this->use_points) {
                echo "<td class='score'>".sprintf("%.1f", $racer['score'])."</td>";
            } else {
                echo "<td class='score'>".sprintf($time_format, $racer['score'])."</td>";
            }
            
            // Best Time
            if ($this->use_points) {
                echo "<td class='best'>".ordinal($racer['best_time'])."</td>";
            } else {
                echo "<td class='best'>".sprintf($time_format, $racer['best_time'])."</td>";
            }
            
            // Worst Time  
            if ($this->use_points) {
                echo "<td class='worst'>".ordinal($racer['worst_time'])."</td>";
            } else {
                echo "<td class='worst'>".sprintf($time_format, $racer['worst_time'])."</td>";
            }
            
            echo "</tr>\n";
        }
    }
    
    /**
     * Write complete standings table
     */
    public function write_standings_table() {
        echo "<thead>";
        $this->write_standings_headers();
        echo "</thead>";
        echo "<tbody>";
        $this->write_standings_rows();
        echo "</tbody>";
    }
    
    /**
     * Get tournament info for display
     */
    public function get_tournament_info() {
        return [
            'class_name' => $this->get_class_name(),
            'round_name' => $this->get_round_display_name(),
            'current_round' => $this->tournament_state['current_round'],
            'total_rounds' => $this->tournament_state['total_rounds'],
            'advance_count' => $this->get_advance_count(),
            'scoring_method' => $this->current_round_config['scoring_method']
        ];
    }
}

?>