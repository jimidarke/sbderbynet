<?php
/**
 * Debug script to check TimerStatus table and timer heartbeat data
 * Access via: http://localhost/derbynet/debug_timer_status.php
 */

require_once('inc/data.inc');
header('Content-Type: text/plain');

echo "=== DerbyNet Timer Status Debug ===\n";
echo "Timestamp: " . date('Y-m-d H:i:s') . "\n\n";

try {
    // Check if TimerStatus table exists
    echo "1. Checking TimerStatus table structure...\n";
    $stmt = $db->query("PRAGMA table_info(TimerStatus)");
    $columns = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    if (empty($columns)) {
        echo "ERROR: TimerStatus table does not exist!\n";
        exit(1);
    }
    
    echo "Table structure:\n";
    foreach ($columns as $col) {
        echo "  - {$col['name']} ({$col['type']}) " . 
             ($col['notnull'] ? "NOT NULL " : "") . 
             ($col['pk'] ? "PRIMARY KEY" : "") . "\n";
    }
    echo "\n";
    
    // Check current timer status data
    echo "2. Current timer status data...\n";
    $stmt = $db->query('SELECT * FROM TimerStatus ORDER BY last_heartbeat DESC');
    $timers = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    if (empty($timers)) {
        echo "No timer status data found.\n";
    } else {
        echo "Found " . count($timers) . " timer entries:\n";
        echo str_pad("Lane", 6) . str_pad("TimerID", 12) . str_pad("Ready", 7) . 
             str_pad("Starter", 9) . str_pad("Last Heartbeat", 20) . "Age (seconds)\n";
        echo str_repeat("-", 70) . "\n";
        
        $current_time = time();
        foreach ($timers as $timer) {
            $age = $current_time - $timer['last_heartbeat'];
            $heartbeat_time = date('H:i:s', $timer['last_heartbeat']);
            
            echo str_pad($timer['lane'], 6) . 
                 str_pad($timer['timerID'], 12) . 
                 str_pad($timer['ready'] ? 'Yes' : 'No', 7) . 
                 str_pad($timer['is_starter'] ? 'Yes' : 'No', 9) . 
                 str_pad($heartbeat_time, 20) . 
                 $age . "\n";
        }
    }
    echo "\n";
    
    // Check device status data
    echo "3. Device status data...\n";
    $stmt = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC LIMIT 5');
    $devices = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    if (empty($devices)) {
        echo "No device status data found.\n";
    } else {
        echo "Found " . count($devices) . " recent device entries:\n";
        foreach ($devices as $device) {
            $age = time() - $device['last_updated'];
            echo "  - {$device['device_name']} ({$device['serial']}) - " .
                 "Updated {$age}s ago\n";
        }
    }
    echo "\n";
    
    // Check timer state
    echo "4. Timer state information...\n";
    if (function_exists('json_timer_state')) {
        $timer_state = json_timer_state();
        echo "Timer state: {$timer_state['state']}\n";
        echo "Message: {$timer_state['message']}\n";
        echo "Lanes: {$timer_state['lanes']}\n";
        echo "Last contact: {$timer_state['last-contact']}\n";
        echo "Remote start: " . ($timer_state['remote-start'] ? 'Yes' : 'No') . "\n";
        
        if (isset($timer_state['timers']) && !empty($timer_state['timers'])) {
            echo "Active timers from JSON:\n";
            foreach ($timer_state['timers'] as $timer) {
                echo "  - Lane {$timer['lane']}: {$timer['timerID']} " .
                     ($timer['ready'] ? '(Ready)' : '(Not Ready)') . "\n";
            }
        } else {
            echo "No active timers in JSON state.\n";
        }
    } else {
        echo "Timer state function not available.\n";
    }
    echo "\n";
    
    // Check recent log entries if accessible
    echo "5. Recent error log entries...\n";
    $error_log_path = ini_get('error_log');
    if ($error_log_path && file_exists($error_log_path)) {
        $lines = file($error_log_path);
        $recent_lines = array_slice($lines, -10);
        
        foreach ($recent_lines as $line) {
            if (stripos($line, 'timer') !== false || stripos($line, 'heartbeat') !== false) {
                echo "  " . trim($line) . "\n";
            }
        }
    } else {
        echo "Error log not accessible or not configured.\n";
    }
    
} catch (PDOException $e) {
    echo "Database error: " . $e->getMessage() . "\n";
} catch (Exception $e) {
    echo "General error: " . $e->getMessage() . "\n";
}

echo "\n=== Debug Complete ===\n";
?>