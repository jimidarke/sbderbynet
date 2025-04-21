<?php

require_once('inc/data.inc');
require_once('inc/newracer.inc');
require_once('roster.inc');
require_once('error-logging.inc');

function form_groups_by_rule($rule) {
  error_log("Forming groups by rule: " . $rule);
  global $db;
  if ($rule == 'one-group') {
    $db->exec('DELETE FROM Roster');
    $db->exec('DELETE FROM Rounds');
    $db->exec('DELETE FROM ConstituentClasses');
    $db->exec('DELETE FROM Awards WHERE rankid IS NOT NULL OR classid IS NOT NULL');
    $db->exec('DELETE FROM Classes');
    $db->exec('DELETE FROM Ranks');
    delete_from_raceinfo('full-field-calc');
    // find_or_create_class will create a Rounds entry, if necessary.
    $classid = find_or_create_class('All Racers');
    // Trusting that partitions have unique names
    $stmt = $db->prepare('INSERT INTO Ranks(rank, classid, sortorder)'
                         .'     SELECT name, :classid, sortorder FROM Partitions');
    $stmt->execute(array(':classid' => $classid));

    $stmt = $db->prepare('UPDATE RegistrationInfo SET classid = :classid,'
                         .' rankid = (SELECT rankid FROM Ranks'
                         .'           WHERE rank = '
                         .'            (SELECT name FROM Partitions'
                         .'                 WHERE Partitions.partitionid = RegistrationInfo.partitionid))');
    $stmt->execute(array(':classid' => $classid));

    // Update Partitions table's rankid values to match new ranks
    $db->exec('UPDATE Partitions'
              .' SET rankid = (SELECT rankid FROM Ranks'
              .'               WHERE Ranks.rank = Partitions.name)');

    fill_in_missing_roster_entries();
  } else if ($rule == 'by-partition') {
    // $db->beginTransaction();
    try {
        // Clean up existing data
        $db->exec('DELETE FROM Roster');
        $db->exec('DELETE FROM Rounds');
        $db->exec('DELETE FROM ConstituentClasses');
        $db->exec('DELETE FROM Awards WHERE rankid IS NOT NULL OR classid IS NOT NULL');
        $db->exec('DELETE FROM Classes');
        $db->exec('DELETE FROM Ranks');
        delete_from_raceinfo('full-field-calc');

        // Create classes from partitions
        $db->exec('INSERT INTO Classes(class, sortorder) SELECT name, sortorder FROM Partitions');
        
        // Create triple elimination rounds for each class
        $stmt = $db->query('SELECT classid, class FROM Classes ORDER BY sortorder');
        while ($class = $stmt->fetch(PDO::FETCH_ASSOC)) {

            error_log("Creating triple elimination rounds for class: " . $class['class']);

            $rounds = create_triple_elimination_rounds($class['classid']);

            error_log("Created rounds: " . implode(", ", $rounds));
            
            // Verify rounds were created correctly
            if (!verify_triple_elimination_rounds($class['classid'])) {
                throw new Exception("Failed to verify triple elimination rounds for class: " . $class['class']);
            }
        }

        // Update registration info
        $db->exec('UPDATE RegistrationInfo
                  SET classid = (SELECT classid FROM Classes
                               WHERE class = (SELECT name FROM Partitions
                                            WHERE Partitions.partitionid = RegistrationInfo.partitionid))');

        // Create ranks
        $db->exec('INSERT INTO Ranks(rank, classid, sortorder)
                  SELECT class, classid, 1 FROM Classes');
        
        $db->exec('UPDATE RegistrationInfo
                  SET rankid = (SELECT rankid FROM Ranks
                              WHERE Ranks.classid = RegistrationInfo.classid)');

        fill_in_missing_roster_entries();
        
        // $db->commit();
        
    } catch (Exception $e) {
        // $db->rollBack();  
        error_log("Error in form_groups_by_rule: " . $e->getMessage());
        throw $e;
    }
  }
  // else ('custom') do nothing
}?>
