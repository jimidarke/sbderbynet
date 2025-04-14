<?php
require_once('inc/data.inc');      // Include database connection
require_once('inc/authorize.inc'); // Include authorization

header('Content-Type: application/json');
// Uncomment below if you're calling this from JavaScript in the browser
// header("Access-Control-Allow-Origin: *");
// header("Access-Control-Allow-Methods: GET, POST");
// header("Access-Control-Allow-Headers: Content-Type");

// Check authentication via session
if (!isset($_COOKIE['PHPSESSID'])) {
    http_response_code(401); // Unauthorized
    echo json_encode(['error' => 'Unauthorized. Please log in.']);
    exit;
}

try {
    // Handle GET: Retrieve device statuses
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $stmt = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC');
        $devices = $stmt->fetchAll(PDO::FETCH_ASSOC);
        echo json_encode(['devices' => $devices]);
        exit;
    }

    // Handle POST: Insert/update device statuses
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $input = json_decode(file_get_contents('php://input'), true);

        if (!isset($input['devices']) || !is_array($input['devices'])) {
            http_response_code(400); // Bad Request
            echo json_encode(['error' => 'Invalid input format. Expecting a devices array.']);
            exit;
        }

        $required_fields = ['device_name', 'serial', 'uptime', 'ip_address', 'mac_address', 'wifi_signal', 'battery', 'temperature', 'memory', 'disk', 'cpu'];
        $results = [];

        foreach ($input['devices'] as $device) {
            // Validate all required fields
            foreach ($required_fields as $field) {
                if (!isset($device[$field])) {
                    $results[] = [
                        'device' => $device['serial'] ?? 'unknown',
                        'status' => 'error',
                        'message' => "Missing required field: $field"
                    ];
                    continue 2; // Skip to next device
                }
            }

            try {
                $stmt = $db->prepare('REPLACE INTO DeviceStatus (
                    device_name, serial, uptime, ip_address, mac_address, wifi_signal, 
                    battery, temperature, memory, disk, cpu, last_updated
                ) VALUES (
                    :device_name, :serial, :uptime, :ip_address, :mac_address, :wifi_signal, 
                    :battery, :temperature, :memory, :disk, :cpu, :last_updated
                )');

                $success = $stmt->execute([
                    ':device_name' => $device['device_name'],
                    ':serial' => $device['serial'],
                    ':uptime' => $device['uptime'],
                    ':ip_address' => $device['ip_address'],
                    ':mac_address' => $device['mac_address'],
                    ':wifi_signal' => $device['wifi_signal'],
                    ':battery' => $device['battery'],
                    ':temperature' => $device['temperature'],
                    ':memory' => $device['memory'],
                    ':disk' => $device['disk'],
                    ':cpu' => $device['cpu'],
                    ':last_updated' => time(),
                ]);

                $results[] = [
                    'device' => $device['serial'],
                    'status' => $success ? 'success' : 'failed'
                ];
            } catch (PDOException $e) {
                $results[] = [
                    'device' => $device['serial'],
                    'status' => 'error',
                    'message' => $e->getMessage()
                ];
            }
        }

        // Respond with all results
        echo json_encode(['results' => $results]);
        exit;
    }

    // Unsupported request method
    http_response_code(405);
    echo json_encode(['error' => 'Invalid request method. Use GET or POST.']);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error.', 'details' => $e->getMessage()]);
}
