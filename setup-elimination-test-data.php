<?php
// Setup test data for elimination tournaments

require_once('inc/data.inc');
require_once('inc/authorize.inc');
session_start();

// Check permissions
if (!have_permission(SET_UP_PERMISSION)) {
    echo "<h1>Permission Denied</h1>\n";
    echo "<p>This script requires SET_UP_PERMISSION. Please log in as an administrator.</p>\n";
    exit;
}

echo "<h1>Setup Elimination Tournament Test Data</h1>\n";

try {
    $db->beginTransaction();
    
    // Create age-based classes
    $age_groups = [
        ['name' => 'Ages 6-8', 'expected_racers' => 25],
        ['name' => 'Ages 9-11', 'expected_racers' => 20], 
        ['name' => 'Ages 12-14', 'expected_racers' => 15]
    ];
    
    echo "<h2>Creating Age-Based Classes</h2>\n";
    
    $created_classes = [];
    
    foreach ($age_groups as $group) {
        // Check if class already exists
        $existing = $db->prepare('SELECT classid FROM Classes WHERE class = :name');
        $existing->execute([':name' => $group['name']]);
        
        if ($existing->fetch()) {
            echo "<p>Class '{$group['name']}' already exists, skipping...</p>\n";
            continue;
        }
        
        // Create class
        $stmt = $db->prepare('INSERT INTO Classes (class, ntrophies) VALUES (:name, 3)');
        $stmt->execute([':name' => $group['name']]);
        $classid = $db->lastInsertId();
        
        $created_classes[] = ['classid' => $classid, 'name' => $group['name'], 'expected_racers' => $group['expected_racers']];
        echo "<p style='color: green;'>✅ Created class '{$group['name']}' (ID: $classid)</p>\n";
    }
    
    echo "<h2>Creating Fake Racers</h2>\n";
    
    // Simple fake names for testing
    $fake_names = [
        ['firstname' => 'Alex', 'lastname' => 'Smith'],
        ['firstname' => 'Blake', 'lastname' => 'Johnson'],
        ['firstname' => 'Casey', 'lastname' => 'Williams'],
        ['firstname' => 'Dakota', 'lastname' => 'Brown'],
        ['firstname' => 'Emery', 'lastname' => 'Davis'],
        ['firstname' => 'Finley', 'lastname' => 'Miller'],
        ['firstname' => 'Grayson', 'lastname' => 'Wilson'],
        ['firstname' => 'Hayden', 'lastname' => 'Moore'],
        ['firstname' => 'Indigo', 'lastname' => 'Taylor'],
        ['firstname' => 'Jordan', 'lastname' => 'Anderson'],
        ['firstname' => 'Kendall', 'lastname' => 'Thomas'],
        ['firstname' => 'Logan', 'lastname' => 'Jackson'],
        ['firstname' => 'Morgan', 'lastname' => 'White'],
        ['firstname' => 'Noah', 'lastname' => 'Harris'],
        ['firstname' => 'Oakley', 'lastname' => 'Martin'],
        ['firstname' => 'Parker', 'lastname' => 'Garcia'],
        ['firstname' => 'Quinn', 'lastname' => 'Rodriguez'],
        ['firstname' => 'River', 'lastname' => 'Lewis'],
        ['firstname' => 'Sage', 'lastname' => 'Lee'],
        ['firstname' => 'Taylor', 'lastname' => 'Walker']
    ];
    
    $car_number = 1;
    $total_racers = 0;
    
    foreach ($created_classes as $class_info) {
        $classid = $class_info['classid'];
        $class_name = $class_info['name'];
        $num_racers = $class_info['expected_racers'];
        
        echo "<p>Adding $num_racers racers to '{$class_name}'...</p>\n";
        
        for ($i = 0; $i < $num_racers; $i++) {
            $name_index = ($total_racers + $i) % count($fake_names);
            $name = $fake_names[$name_index];
            
            // Generate random weight between 25kg and 50kg
            $weight = round(mt_rand(25000, 50000) / 1000.0, 2);
            $checkInTime = floor(microtime(true) * 1000);
            
            $stmt = $db->prepare('INSERT INTO RegistrationInfo 
                                 (firstname, lastname, carname, carnumber, classid, carweight, 
                                  passedinspection, registered, checkin_time)
                                 VALUES (:firstname, :lastname, :carname, :carnumber, :classid, 
                                        :carweight, 1, 1, :checkin_time)');
            
            $stmt->execute([
                ':firstname' => $name['firstname'],
                ':lastname' => $name['lastname'],
                ':carname' => $name['firstname'] . "'s Racer",
                ':carnumber' => $car_number++,
                ':classid' => $classid,
                ':carweight' => $weight,
                ':checkin_time' => $checkInTime
            ]);
        }
        
        $total_racers += $num_racers;
        echo "<p style='color: green;'>✅ Added $num_racers racers to '{$class_name}'</p>\n";
    }
    
    $db->commit();
    
    echo "<h2>Setup Complete</h2>\n";
    echo "<p style='color: green;'>✅ Successfully created test data:</p>\n";
    echo "<ul>\n";
    foreach ($created_classes as $class_info) {
        echo "<li>{$class_info['name']}: {$class_info['expected_racers']} racers</li>\n";
    }
    echo "</ul>\n";
    echo "<p><strong>Total racers created:</strong> $total_racers</p>\n";
    
    echo "<h2>Next Steps</h2>\n";
    echo "<ol>\n";
    echo "<li>Go to <a href='racing-groups.php'>Racing Groups</a> page</li>\n";
    echo "<li>Edit each age-based class</li>\n";
    echo "<li>Initialize elimination tournaments using the 'Soapbox Derby Triple Elimination' configuration</li>\n";
    echo "<li>Test tournament advancement workflow</li>\n";
    echo "</ol>\n";
    
} catch (Exception $e) {
    $db->rollBack();
    echo "<p style='color: red;'>❌ Error: " . $e->getMessage() . "</p>\n";
}

?>