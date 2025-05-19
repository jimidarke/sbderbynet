<?php
require_once('inc/data.inc'); // Include database connection
require_once('inc/authorize.inc'); // Include authorization

$devices = $db->query('SELECT * FROM DeviceStatus ORDER BY last_updated DESC')->fetchAll(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html>

<head>
    <title>Devices Statuses</title>
    <link rel="stylesheet" type="text/css" href="css/device-status-style.css">
    <script src="js/jquery.js"></script>
    <script src="js/device-status.js"></script> <!-- Include the new JS file -->
</head>
<div class="page-container">
    <header class="page-header">
        <h1>Device Status</h1>
    </header>
    <main class="content">
        <table class="device-status-table">
            <thead>
                <tr>
                    <th data-sort="string" class="sort-header">Device Name</th>
                    <th>Serial</th>
                    <th>Uptime</th>
                    <th>IP Address</th>
                    <!-- <th>MAC Address</th> -->
                    <th>Wi-Fi Signal</th>
                    <th>Battery</th>
                    <th>Temperature</th>
                    <th>Memory</th>
                    <th>Disk</th>
                    <th>CPU</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody id="device-statuses">
                <!-- Dynamic rows will be added here -->
            </tbody>
        </table>
    </main>
</div>
</body>

</html>