<?php
// LED Sign management functions
// Mirrors the kiosks.inc pattern for HTTP-based device discovery

require_once('inc/sql-script.inc');
require_once('inc/ledsign-zones.inc');

// Create the LedSigns table if it doesn't exist
function create_ledsign_table() {
  run_sql_script('ledsign-table');
}

// Normalize MAC address to uppercase with colons
function normalize_mac($mac) {
  // Remove any existing separators and convert to uppercase
  $clean = strtoupper(preg_replace('/[^A-Fa-f0-9]/', '', $mac));
  // Insert colons every 2 characters
  if (strlen($clean) == 12) {
    return implode(':', str_split($clean, 2));
  }
  return $mac; // Return as-is if not valid format
}

// Register or update a LED sign in the database
// Called when ESP32 makes initial contact or polls
function ledsign_register($mac, $ip_address = null, $firmware_version = null) {
  global $db;
  $mac = normalize_mac($mac);

  do {
    $retry = false;
    try {
      // Check if sign already exists
      $stmt = $db->prepare('SELECT mac, zone FROM LedSigns WHERE mac = :mac');
      $stmt->execute(array(':mac' => $mac));
      $row = $stmt->fetch(PDO::FETCH_ASSOC);
      $stmt->closeCursor();

      if ($row) {
        // Update existing sign
        $stmt = $db->prepare('UPDATE LedSigns SET '
                             .' ip_address = :ip,'
                             .' firmware_version = :version,'
                             .' last_contact = :time'
                             .' WHERE mac = :mac');
        $stmt->execute(array(
          ':mac' => $mac,
          ':ip' => $ip_address,
          ':version' => $firmware_version,
          ':time' => time()
        ));
        return $row['zone']; // Return current zone assignment
      } else {
        // Insert new sign
        $stmt = $db->prepare('INSERT INTO LedSigns(mac, zone, ip_address, firmware_version, last_contact)'
                             .' VALUES(:mac, NULL, :ip, :version, :time)');
        $stmt->execute(array(
          ':mac' => $mac,
          ':ip' => $ip_address,
          ':version' => $firmware_version,
          ':time' => time()
        ));
        return null; // New sign, no zone assigned
      }
    } catch (PDOException $p) {
      if (is_no_such_table_exception($p)) {
        create_ledsign_table();
        $retry = true;
      } else {
        error_log("LED Sign registration error: " . $p->getMessage());
        return false;
      }
    }
  } while ($retry);

  return null;
}

// Get LED sign configuration by MAC address
// Returns array with zone, status, and MQTT topics
function ledsign_config($mac) {
  global $db;
  $mac = normalize_mac($mac);

  try {
    $stmt = $db->prepare('SELECT mac, zone, ip_address, firmware_version, last_contact'
                         .' FROM LedSigns WHERE mac = :mac');
    $stmt->execute(array(':mac' => $mac));
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $stmt->closeCursor();

    if ($row) {
      // Update last_contact
      $stmt = $db->prepare('UPDATE LedSigns SET last_contact = :time WHERE mac = :mac');
      $stmt->execute(array(':mac' => $mac, ':time' => time()));

      $config = array(
        'mac' => $row['mac'],
        'zone' => $row['zone'],
        'status' => $row['zone'] ? 'configured' : 'identify',
      );

      if ($row['zone']) {
        $config['mqtt_topics'] = ledsign_mqtt_topics($row['zone']);
      }

      return $config;
    }
  } catch (PDOException $p) {
    // Table may not exist yet
  }

  return array(
    'mac' => $mac,
    'zone' => null,
    'status' => 'unknown'
  );
}

// Assign a zone to a LED sign
function ledsign_assign_zone($mac, $zone) {
  global $db;
  $mac = normalize_mac($mac);

  // Validate zone (allow null/empty to unassign)
  if ($zone && !ledsign_zone_valid($zone)) {
    return array('success' => false, 'error' => 'Invalid zone: ' . $zone);
  }

  // If assigning a zone, first unassign it from any other sign
  if ($zone) {
    try {
      $stmt = $db->prepare('UPDATE LedSigns SET zone = NULL WHERE zone = :zone AND mac != :mac');
      $stmt->execute(array(':zone' => $zone, ':mac' => $mac));
    } catch (PDOException $p) {
      // Ignore errors here
    }
  }

  try {
    $stmt = $db->prepare('UPDATE LedSigns SET zone = :zone WHERE mac = :mac');
    $stmt->execute(array(':mac' => $mac, ':zone' => $zone ? $zone : null));

    if ($stmt->rowCount() > 0) {
      return array('success' => true, 'mac' => $mac, 'zone' => $zone);
    } else {
      return array('success' => false, 'error' => 'Sign not found: ' . $mac);
    }
  } catch (PDOException $p) {
    return array('success' => false, 'error' => 'Database error: ' . $p->getMessage());
  }
}

// Get all LED signs (for admin dashboard)
// Returns array of signs with their status
function all_ledsigns() {
  global $db;
  $signs = array();

  try {
    drop_old_ledsigns();

    // Get signs that have contacted within last 60 seconds
    $stmt = $db->query('SELECT mac, zone, ip_address, firmware_version, last_contact'
                       .' FROM LedSigns'
                       .' WHERE ' . time() . ' - last_contact < 60'
                       .' ORDER BY zone IS NULL, zone, mac');

    foreach ($stmt as $row) {
      $signs[] = array(
        'mac' => $row['mac'],
        'zone' => $row['zone'],
        'zone_name' => $row['zone'] ? ledsign_zone_name($row['zone']) : null,
        'ip_address' => $row['ip_address'],
        'firmware_version' => $row['firmware_version'],
        'last_contact' => $row['last_contact'],
        'age_seconds' => time() - $row['last_contact'],
        'status' => 'online'
      );
    }
  } catch (PDOException $p) {
    // Table may not exist yet
  }

  return $signs;
}

// Get zone assignment summary
// Returns all zones with their assigned MAC (or null if unassigned)
function ledsign_zone_assignments() {
  global $db;
  $assignments = array();

  // Start with all zones unassigned
  foreach (ledsign_zones() as $zone) {
    $assignments[$zone['id']] = array(
      'id' => $zone['id'],
      'name' => $zone['name'],
      'description' => $zone['description'],
      'assigned_mac' => null,
      'status' => null
    );
  }

  // Fill in assignments from database
  try {
    $stmt = $db->query('SELECT mac, zone, last_contact FROM LedSigns WHERE zone IS NOT NULL');
    foreach ($stmt as $row) {
      if (isset($assignments[$row['zone']])) {
        $age = time() - $row['last_contact'];
        $assignments[$row['zone']]['assigned_mac'] = $row['mac'];
        $assignments[$row['zone']]['status'] = ($age < 60) ? 'online' : 'offline';
      }
    }
  } catch (PDOException $p) {
    // Table may not exist yet
  }

  return array_values($assignments);
}

// Delete LED signs that haven't been seen for over an hour
function drop_old_ledsigns() {
  global $db;
  try {
    $stmt = $db->query('DELETE FROM LedSigns WHERE ' . time() . ' - last_contact > 3600');
  } catch (PDOException $p) {
    // Ignore errors
  }
}

// Get MQTT broker configuration from environment or defaults
function ledsign_mqtt_config() {
  return array(
    'broker' => isset($_SERVER['MQTT_BROKER']) ? $_SERVER['MQTT_BROKER'] : '192.168.100.10',
    'port' => isset($_SERVER['MQTT_PORT']) ? intval($_SERVER['MQTT_PORT']) : 1883,
  );
}
?>
