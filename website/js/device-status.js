'use strict';

// Function to fetch device status data from the server
function fetchDeviceStatus() {
    $.ajax({
        url: 'device-status-api.php',
        type: 'GET',
        dataType: 'json',
        success: function (response) {
            const dummyDevices = [ /* Dummy device data here */ ];

            if (response && Array.isArray(response.devices) && response.devices.length > 0) {
                updateDeviceStatusTable(response.devices);
            } else {
                console.warn("Using dummy data due to empty or invalid response:", response);
                updateDeviceStatusTable(dummyDevices);
            }
        },
        error: function (xhr, status, error) {
            console.error("Failed to fetch device status:", error);
        }
    });
}

// Function to update the device status table dynamically
function updateDeviceStatusTable(devices) {
    const now = Math.floor(Date.now() / 1000);
    const tbody = document.getElementById("device-statuses");

    // Update last seen map
    devices.forEach(device => {
        lastSeenTimestamps.set(device.serial, device.last_updated || now);
    });

    // Filter out stale devices
    const activeDevices = devices.filter(device => {
        const lastSeen = lastSeenTimestamps.get(device.serial);
        return lastSeen && now - lastSeen <= DEVICE_TIMEOUT_SECONDS;
    });

    // Mark devices as inactive on the backend if they are stale
    devices.forEach(device => {
        const lastSeen = lastSeenTimestamps.get(device.serial);
        if (now - lastSeen > DEVICE_TIMEOUT_SECONDS) {
            markDeviceInactive(device.serial); // Mark device as inactive on the backend
        }
    });

    tbody.innerHTML = ""; // Clear table
    activeDevices.forEach(device => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${device.device_name}</td>
            <td>${device.serial}</td>
            <td>${formatUptime(device.uptime)}</td>
            <td>${device.ip_address}</td>
            <td>${device.mac_address}</td>
            <td>${device.wifi_signal}%</td>
            <td>${device.battery}%</td>
            <td>${device.temperature}°C</td>
            <td>${device.memory}MB</td>
            <td>${device.disk}GB</td>
            <td>${device.cpu}%</td>
            <td>${formatTimestamp(device.last_updated)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Function to mark a device as inactive on the backend
function markDeviceInactive(serial) {
    $.ajax({
        url: 'device-status-api.php',
        type: 'POST',
        dataType: 'json',
        contentType: 'application/json',
        data: JSON.stringify({
            devices: [{
                serial: serial,
                status: 'inactive'
            }]
        }),
        success: function(response) {
            console.log(`Device ${serial} marked as inactive.`);
        },
        error: function(xhr, status, error) {
            console.error("Failed to mark device inactive:", error);
        }
    });
}

// Helper function to format uptime (seconds to human-readable format)
function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return `${hours}h ${minutes}m ${secs}s`;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

$(document).ready(function () {
    // Fetch device status data every 5 seconds
    setInterval(fetchDeviceStatus, 5000);

    // Initial fetch when the page loads
    fetchDeviceStatus();
});

const DEVICE_TIMEOUT_SECONDS = 30;
const lastSeenTimestamps = new Map();
