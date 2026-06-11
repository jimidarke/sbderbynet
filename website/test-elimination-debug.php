<?php
require_once('inc/data.inc');
require_once('inc/elimination-config.inc');

echo "<h1>Elimination Tournament Debug</h1>\n";
echo "<p>PHP Version: " . phpversion() . "</p>\n";
echo "<p>Time: " . date('Y-m-d H:i:s') . "</p>\n";

try {
    // Test basic database connection
    echo "<h2>1. Database Test</h2>\n";
    global $db;
    $test = $db->query('SELECT COUNT(*) FROM EliminationTournaments WHERE classid = 1')->fetchColumn();
    echo "<p>Elimination tournaments for class 1: $test</p>\n";
    
    // Test elimination tournament state
    echo "<h2>2. Testing get_elimination_tournament_state(1)</h2>\n";
    $state = get_elimination_tournament_state(1);
    if ($state) {
        echo "<p>✅ Tournament state loaded successfully</p>\n";
        
        // Test current round config
        $current_round = $state['current_round'];
        echo "<p>Current round: $current_round</p>\n";
        
        $total_rounds = count($state['age_group']['rounds']);
        echo "<p>Total rounds in config: $total_rounds</p>\n";
        
        if ($current_round <= $total_rounds) {
            $round_config = $state['age_group']['rounds'][$current_round - 1];
            echo "<p>✅ Round config found: " . $round_config['round_name'] . "</p>\n";
            echo "<p>Scoring method: " . $round_config['scoring_method'] . "</p>\n";
        } else {
            echo "<p>❌ Current round ($current_round) exceeds available rounds ($total_rounds)</p>\n";
        }
    } else {
        echo "<p>❌ No tournament state found!</p>\n";
        return;
    }
    
    echo "<h2>3. Testing EliminationStandingsOracle constructor</h2>\n";
    require_once('inc/elimination-standings.inc');
    $standings = new EliminationStandingsOracle(1);
    echo "<p>✅ EliminationStandingsOracle created successfully</p>\n";
    
    $tournament_info = $standings->get_tournament_info();
    echo "<p>Tournament info: " . json_encode($tournament_info) . "</p>\n";
    
    echo "<h2>4. Testing raw standings data</h2>\n";
    // Test the query directly
    $classid = 1;
    $round_name = "4 Finals";
    $sql = "SELECT 
                ri.racerid,
                ri.firstname,
                ri.lastname, 
                ri.carnumber,
                COUNT(*) as heats_run,
                MIN(rc.finishplace) as score,
                MIN(rc.finishtime) as best_time,
                MAX(rc.finishtime) as worst_time
            FROM RaceChart rc
            INNER JOIN RegistrationInfo ri ON rc.racerid = ri.racerid
            INNER JOIN Classes c ON ri.classid = c.classid
            WHERE rc.classid = :classid 
              AND rc.roundid = (
                  SELECT roundid FROM Rounds 
                  WHERE classid = :classid AND round = :round_name 
                  LIMIT 1
              )
              AND (
                  (rc.finishtime IS NOT NULL AND rc.finishtime > 0 AND rc.finishtime < " . DNF_TIME . ") OR
                  (rc.finishplace IS NOT NULL AND rc.finishplace > 0)
              )
            GROUP BY ri.racerid, ri.firstname, ri.lastname, ri.carnumber
            ORDER BY score ASC";
    
    $stmt = $db->prepare($sql);
    $stmt->execute([':classid' => $classid, ':round_name' => $round_name]);
    $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "<p>Raw query results: " . count($results) . " racers</p>\n";
    if (count($results) > 0) {
        echo "<table border='1'>";
        echo "<tr><th>Place</th><th>Name</th><th>Car#</th><th>Score</th><th>Best Time</th></tr>";
        foreach ($results as $i => $racer) {
            $place = $i + 1;
            echo "<tr>";
            echo "<td>$place</td>";
            echo "<td>" . htmlspecialchars($racer['firstname'] . ' ' . $racer['lastname']) . "</td>";
            echo "<td>" . pinny_display($racer['carnumber']) . "</td>";
            echo "<td>" . $racer['score'] . "</td>";
            echo "<td>" . number_format($racer['best_time'], 3) . "</td>";
            echo "</tr>";
        }
        echo "</table>";
    }
    
} catch (Exception $e) {
    echo "<p style='color: red;'>❌ Error: " . htmlspecialchars($e->getMessage()) . "</p>\n";
    echo "<pre>Stack trace: " . htmlspecialchars($e->getTraceAsString()) . "</pre>\n";
}
?>