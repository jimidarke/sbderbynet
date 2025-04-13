<?php
function json_device_status() {
    global $db;

    $stmt = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC');
    $devices = array();
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $devices[] = $row;
    }
    return $devices;
}
?>