<?php
require_once('../inc/data.inc'); // Include database connection
require_once('../inc/authorize.inc'); // Include authorization
require_once('../inc/error-logging.inc');

header('Content-Type: application/json');

// Handle GET method: Fetch device statuses
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    // Fetch device statuses from the database
    $stmt = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC');
    $devices = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode(['devices' => $devices]);
    exit;
}

// Handle POST method: Update device statuses
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Get JSON input
    $input = json_decode(file_get_contents('php://input'), true);

    // Validate input
    $required_fields = ['device_name', 'serial', 'uptime', 'ip_address', 'mac_address', 'wifi_signal', 'battery', 'temperature', 'memory', 'disk', 'cpu'];
    foreach ($required_fields as $field) {
        if (!isset($input[$field])) {
            http_response_code(400); // Bad Request
            derby_log_warning("Device status update missing field: $field");
            echo json_encode(['error' => "Missing required field: $field"]);
            exit;
        }
    }

    $device_name = $input['device_name'];
    $ip = $input['ip_address'];

    // Insert or update device status in the database
    $stmt = $db->prepare('REPLACE INTO DeviceStatus (device_name, serial, uptime, ip_address, mac_address, wifi_signal, battery, temperature, memory, disk, cpu, last_updated)
                          VALUES (:device_name, :serial, :uptime, :ip_address, :mac_address, :wifi_signal, :battery, :temperature, :memory, :disk, :cpu, :last_updated)');
    $success = $stmt->execute([
        ':device_name' => $device_name,
        ':serial' => $input['serial'],
        ':uptime' => $input['uptime'],
        ':ip_address' => $ip,
        ':mac_address' => $input['mac_address'],
        ':wifi_signal' => $input['wifi_signal'],
        ':battery' => $input['battery'],
        ':temperature' => $input['temperature'],
        ':memory' => $input['memory'],
        ':disk' => $input['disk'],
        ':cpu' => $input['cpu'],
        ':last_updated' => time(),
    ]);

    if ($success) {
        derby_log_debug("Device status update: $device_name ($ip)");
        echo json_encode(['success' => 'Device status updated successfully.']);
    } else {
        derby_log_error("Failed to update device status for $device_name");
        http_response_code(500); // Internal Server Error
        echo json_encode(['error' => 'Failed to update device status.']);
    }
    exit;
}

// Handle unsupported methods
http_response_code(405); // Method Not Allowed
echo json_encode(['error' => 'Invalid request method. Use GET or POST.']);