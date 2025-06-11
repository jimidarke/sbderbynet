<?php
// Simple test script to verify elimination tournament system

require_once('inc/data.inc');
require_once('inc/elimination-config.inc');

echo "<h1>Elimination Tournament System Test</h1>\n";

// Test 1: Load configuration list
echo "<h2>Test 1: Loading Configuration List</h2>\n";
$configs = load_elimination_config_list();
if (empty($configs)) {
    echo "<p style='color: red;'>❌ Failed to load configuration list</p>\n";
} else {
    echo "<p style='color: green;'>✅ Loaded " . count($configs) . " configuration(s)</p>\n";
    foreach ($configs as $config) {
        echo "<p>- {$config['name']} (v{$config['version']}): {$config['description']}</p>\n";
    }
}

// Test 2: Load specific configuration
echo "<h2>Test 2: Loading Soapbox Derby Configuration</h2>\n";
$config = load_elimination_config('soapbox-derby-elimination.json');
if (!$config) {
    echo "<p style='color: red;'>❌ Failed to load soapbox derby configuration</p>\n";
} else {
    echo "<p style='color: green;'>✅ Successfully loaded configuration</p>\n";
    echo "<p>Format: {$config['format_name']}</p>\n";
    echo "<p>Age Groups: " . count($config['age_groups']) . "</p>\n";
    
    foreach ($config['age_groups'] as $key => $group) {
        echo "<p>- {$group['name']}: {$group['expected_racers']} racers, " . count($group['rounds']) . " rounds</p>\n";
    }
}

// Test 3: Validate configuration
echo "<h2>Test 3: Configuration Validation</h2>\n";
if ($config && validate_elimination_config($config)) {
    echo "<p style='color: green;'>✅ Configuration validation passed</p>\n";
} else {
    echo "<p style='color: red;'>❌ Configuration validation failed</p>\n";
}

// Test 4: Check for existing classes that might match
echo "<h2>Test 4: Class Pattern Matching</h2>\n";
if (isset($db)) {
    $stmt = $db->query('SELECT classid, class FROM Classes ORDER BY class');
    $classes = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    if (empty($classes)) {
        echo "<p style='color: orange;'>⚠️ No classes found in database. Create some fake classes to test pattern matching.</p>\n";
    } else {
        echo "<p>Found " . count($classes) . " classes in database:</p>\n";
        
        foreach ($classes as $class) {
            echo "<p>- Class ID {$class['classid']}: {$class['class']}</p>\n";
            
            if ($config) {
                $matched_group = find_age_group_for_class($config, $class['classid']);
                if ($matched_group) {
                    echo "<p style='color: green; margin-left: 20px;'>✅ Matches age group: {$matched_group['name']}</p>\n";
                } else {
                    echo "<p style='color: orange; margin-left: 20px;'>⚠️ No pattern match found</p>\n";
                }
            }
        }
    }
} else {
    echo "<p style='color: red;'>❌ Database connection not available</p>\n";
}

// Test 5: Check database schema
echo "<h2>Test 5: Database Schema Check</h2>\n";
if (isset($db)) {
    try {
        // Check if elimination tables exist
        $tables_to_check = ['EliminationTournaments', 'EliminationRoundState', 'EliminationAdvancement'];
        $missing_tables = [];
        
        foreach ($tables_to_check as $table) {
            $result = $db->query("SELECT name FROM sqlite_master WHERE type='table' AND name='$table'");
            if (!$result->fetch()) {
                $missing_tables[] = $table;
            }
        }
        
        if (empty($missing_tables)) {
            echo "<p style='color: green;'>✅ All elimination tournament tables exist</p>\n";
        } else {
            echo "<p style='color: red;'>❌ Missing tables: " . implode(', ', $missing_tables) . "</p>\n";
            echo "<p>Run database schema update to create missing tables.</p>\n";
        }
        
    } catch (Exception $e) {
        echo "<p style='color: red;'>❌ Database schema check failed: " . $e->getMessage() . "</p>\n";
    }
} else {
    echo "<p style='color: red;'>❌ Database connection not available</p>\n";
}

echo "<h2>Test Summary</h2>\n";
echo "<p>Review the results above to ensure the elimination tournament system is properly configured.</p>\n";
echo "<p>Next steps:</p>\n";
echo "<ul>\n";
echo "<li>Create fake roster with age-based classes (e.g., 'Ages 6-8', 'Ages 9-11', 'Ages 12-14')</li>\n";
echo "<li>Initialize elimination tournaments for each class via racing-groups.php</li>\n";
echo "<li>Use coordinator.php to schedule rounds - modal should be bypassed for elimination tournaments</li>\n";
echo "<li>Verify preliminary rounds get 3 races per racer, semifinal/final get 1 race per racer</li>\n";
echo "<li>Test tournament advancement workflow</li>\n";
echo "</ul>\n";

?>