<?php
require_once('inc/schema_version.inc');

if (!function_exists('make_index')) {
  function make_index($table, $column) {
    return "CREATE INDEX IF NOT EXISTS ".$table."_".$column." ON ".$table."(".$column.")";
  }

  function table_exists($table_name) {
    return read_single_value("SELECT COUNT(*) FROM sqlite_master"
                             ." WHERE type='table' AND name='$table_name'") > 0;
  }
}

$updates = array();

if (schema_version() < 2) {

  // There's no ALTER COLUMN in sqlite
  $updates[] = "CREATE TABLE TempRaceInfo AS SELECT * FROM RaceInfo";
  $updates[] = "DROP TABLE RaceInfo";
  $updates[] = "CREATE TABLE `RaceInfo` ("
      ."  `raceinfoid` INTEGER PRIMARY KEY, "
      ."  `itemkey` VARCHAR(20) NOT NULL, "
      ."  `itemvalue` VARCHAR(200)"
      .")";
  $updates[] = make_index("RaceInfo", "itemkey");
  $updates[] = "INSERT INTO RaceInfo SELECT * FROM TempRaceInfo";
  $updates[] = "DROP TABLE TempRaceInfo";

  $updates[] = "ALTER TABLE Classes ADD COLUMN sortorder INTEGER";
  $updates[] = "ALTER TABLE Ranks ADD COLUMN sortorder INTEGER";

  $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN carphoto VARCHAR(255)";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '2')";
}

if (schema_version() < 3) {
  $updates[] = "ALTER TABLE Classes ADD COLUMN constituents VARCHAR(100) DEFAULT ''";
  $updates[] = "ALTER TABLE Classes ADD COLUMN durable INTEGER";
  $updates[] = "ALTER TABLE Classes ADD COLUMN ntrophies INTEGER DEFAULT -1";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '3')";
}

if (schema_version() < 4) {
  if (!table_exists('MessageQueue')) {
    $updates = array_merge($updates,
                           @include(sql_file_path('message-queue-table')));
  }
  if (!table_exists('Scenes')) {
    $updates = array_merge($updates,
                           @include(sql_file_path('scene-tables')));
  }
  if (!table_exists('Playlist')) {
    $updates = array_merge($updates,
                           @include(sql_file_path('playlist-table')));
  }

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '4')";
}

if (schema_version() < 5) {
  $updates[] = "ALTER TABLE Classes ADD COLUMN rankids VARCHAR(100) DEFAULT ''";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '5')";
}

if (schema_version() < 6) {
  $updates = array_merge($updates,
                         @include(sql_file_path('balloting')));

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '6')";
}

if (schema_version() < 7) {
  $updates = array_merge($updates,
                         @include(sql_file_path('timer-settings')));

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '7')";
}

if (schema_version() < 8) {
  $updates = array_merge($updates,
                         @include(sql_file_path('partitions')));
  $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN partitionid INTEGER";
  $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN note VARCHAR(255)";
  $updates[] = "CREATE TABLE ConstituentClasses ("
                  ."antecedent INTEGER, dependent INTEGER, UNIQUE (antecedent, dependent))";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '8')";
}

if (schema_version() < 9) {
  $updates = array_merge($updates,
                         @include(sql_file_path('event-lane-details')));
  // $updates[] = "ALTER TABLE Events DROP COLUMN lane";
  $updates[] = "ALTER TABLE Events ADD COLUMN finishid INTEGER";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '9')";
}

if (schema_version() < 10) {
  $updates = array_merge($updates,
                         @include(sql_file_path('action-history')));
  $updates[] = "ALTER TABLE Ranks ADD COLUMN ntrophies INTEGER DEFAULT -1";
  $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN checkin_time INTEGER";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '10')";
}

// debuggin schema version
error_log("Running schema update... Current schema version: " . schema_version());



if (schema_version() < 11) {
    error_log("Updating to schema version 11...");

    // Check if column already exists before adding
    $column_exists = read_single_value("SELECT COUNT(*) FROM pragma_table_info('RegistrationInfo') WHERE name='carweight'");
    if (!$column_exists) {
        $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN carweight VARCHAR(255)";
    }

    $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
    $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '11')";
}

if (schema_version() < 12) {
  $updates[] = "CREATE TABLE mutual_preferences ("
             . "id INTEGER PRIMARY KEY AUTOINCREMENT, "
             . "racerid INTEGER NOT NULL, "
             . "related_racerid INTEGER NOT NULL, "
             . "preference TEXT CHECK(preference IN ('include', 'exclude')) NOT NULL, "
             . "FOREIGN KEY (racerid) REFERENCES RegistrationInfo(racerid), "
             . "FOREIGN KEY (related_racerid) REFERENCES RegistrationInfo(racerid)"
             . ")";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '12')";
}

if (schema_version() < 13) {
  $updates[] = "CREATE TABLE TimerStatus ("
             . "lane INT NOT NULL, "
             . "timerID VARCHAR(11) NOT NULL, "
             . "last_heartbeat INT NOT NULL, "
             . "ready TINYINT(1) NOT NULL, "
            //  . "is_starter BOOLEAN DEFAULT 0, "
             . "PRIMARY KEY (lane, timerID)"
             . ")";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '13')";
}

if (schema_version() < 14) {
  $updates[] = "CREATE TABLE DeviceStatus ("
             . "device_name VARCHAR(255) NOT NULL, "
             . "serial VARCHAR(255) NOT NULL PRIMARY KEY, "
             . "uptime BIGINT NOT NULL, "
             . "ip_address VARCHAR(45) NOT NULL, "
             . "mac_address VARCHAR(17) NOT NULL, "
             . "wifi_signal INT NOT NULL, "
             . "battery INT NOT NULL, "
             . "temperature FLOAT NOT NULL, "
             . "memory INT NOT NULL, "
             . "disk INT NOT NULL, "
             . "cpu FLOAT NOT NULL, "
             . "last_updated INT NOT NULL"
             . ")";

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '14')";
}

if (schema_version() < 15) {
  error_log("Updating to schema version 15...");

  // Check if column already exists before adding
  $column_exists = read_single_value("SELECT COUNT(*) FROM pragma_table_info('RegistrationInfo') WHERE name='carweight'");
  if (!$column_exists) {
      $updates[] = "ALTER TABLE RegistrationInfo ADD COLUMN registered BOOLEAN DEFAULT 0";
  }

  $updates[] = "DELETE FROM RaceInfo WHERE itemkey = 'schema'";
  $updates[] = "INSERT INTO RaceInfo(itemkey, itemvalue) VALUES('schema', '15')";
}

// For each new schema version, copy the DELETE and INSERT for schema version

return $updates;
?>
