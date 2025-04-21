<?php

require_once('inc/data.inc');
require_once('inc/newracer.inc');

function form_groups_by_rule($rule) {
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
    $db->exec('DELETE FROM Roster');
    $db->exec('DELETE FROM Rounds');
    $db->exec('DELETE FROM ConstituentClasses');
    $db->exec('DELETE FROM Awards WHERE rankid IS NOT NULL OR classid IS NOT NULL');
    $db->exec('DELETE FROM Classes');
    $db->exec('DELETE FROM Ranks');
    delete_from_raceinfo('full-field-calc');

    // Create classes from partitions
    $db->exec('INSERT INTO Classes(class, sortorder) SELECT name, sortorder FROM Partitions');
    
    // Get newly created classes and create triple elimination rounds
    $stmt = $db->query('SELECT classid FROM Classes');
    while ($class = $stmt->fetch(PDO::FETCH_ASSOC)) {
        create_triple_elimination_rounds($class['classid']);
    }

    // Update registration info
    $db->exec('UPDATE RegistrationInfo'
              .' SET classid ='
              .'   (SELECT classid FROM Classes'
              .'     WHERE class = (SELECT name FROM Partitions'
              .'                     WHERE Partitions.partitionid = RegistrationInfo.partitionid))');

    // Create ranks
    $db->exec('INSERT INTO Ranks(rank, classid, sortorder)'
              .' SELECT class, classid, 1 FROM Classes');
              
    $db->exec('UPDATE RegistrationInfo'
              .' SET rankid = (SELECT rankid FROM Ranks'
              .'                WHERE Ranks.classid = RegistrationInfo.classid)');

    // Update partition ranks
    $db->exec('UPDATE Partitions'
              .' SET rankid = (SELECT rankid FROM Ranks'
              .'               WHERE Ranks.rank = Partitions.name)');

    // Don't create default rounds - triple elimination rounds are already created
    // $db->exec('INSERT INTO Rounds(round, classid) SELECT 1, classid FROM Classes');
    fill_in_missing_roster_entries();
  }
  // else ('custom') do nothing
}

?>
