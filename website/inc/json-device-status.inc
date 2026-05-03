<?php
function json_device_status() {
    global $db;

    // Browser virtual hardware uses hwids prefixed with B_ (cloud-only).
    // On race-day the local Pi must never surface them in the coordinator's
    // device list — this is a defense-in-depth check in case a cloud-built
    // image were ever booted on the Pi.
    if (function_exists('is_cloud_mode') && !is_cloud_mode()) {
        $stmt = $db->query("SELECT * FROM DeviceStatus "
                         . "WHERE serial NOT LIKE 'B\\_%' ESCAPE '\\' "
                         . "ORDER BY last_updated DESC");
    } else {
        $stmt = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC');
    }
    $devices = array();
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        if (function_exists('is_cloud_mode') && is_cloud_mode()
            && strncmp($row['serial'] ?? '', 'B_', 2) === 0) {
            $row['is_virtual'] = true;
        }
        $devices[] = $row;
    }
    return $devices;
}
?>