'use strict';

// Function to fetch device status data from the server
function fetchDeviceStatus() {
    $.ajax('action.php',{
        type: 'GET',
        data: {
            action: 'device-status-api',
            dataType: 'json',
            success: function (response) {

                const dummyDevices = [
                    {
                        "device_name": "Finish Timer 1",
                        "serial": "FT12345678",
                        "uptime": 7200,
                        "ip_address": "192.168.1.101",
                        "mac_address": "00:1A:2B:3C:4D:5E",
                        "wifi_signal": 80,
                        "battery": 95,
                        "temperature": 40.2,
                        "memory": 2048,
                        "disk": 128,
                        "cpu": 12.5,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Display Kiosk 1",
                        "serial": "DK98765432",
                        "uptime": 14400,
                        "ip_address": "192.168.1.102",
                        "mac_address": "00:1A:2B:3C:4D:5F",
                        "wifi_signal": 70,
                        "battery": 85,
                        "temperature": 50.1,
                        "memory": 1024,
                        "disk": 64,
                        "cpu": 25.8,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Backup Timer",
                        "serial": "BT11223344",
                        "uptime": 3600,
                        "ip_address": "192.168.1.103",
                        "mac_address": "00:1A:2B:3C:4D:60",
                        "wifi_signal": 90,
                        "battery": 100,
                        "temperature": 35.0,
                        "memory": 4096,
                        "disk": 256,
                        "cpu": 8.3,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Track Sensor A",
                        "serial": "TS99887766",
                        "uptime": 1800,
                        "ip_address": "192.168.1.104",
                        "mac_address": "00:1A:2B:3C:4D:61",
                        "wifi_signal": 75,
                        "battery": 88,
                        "temperature": 38.5,
                        "memory": 512,
                        "disk": 32,
                        "cpu": 15.0,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Start Gate Controller",
                        "serial": "SG55667788",
                        "uptime": 20000,
                        "ip_address": "192.168.1.105",
                        "mac_address": "00:1A:2B:3C:4D:62",
                        "wifi_signal": 85,
                        "battery": 92,
                        "temperature": 42.1,
                        "memory": 1024,
                        "disk": 128,
                        "cpu": 10.2,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Finish Camera",
                        "serial": "FC44556677",
                        "uptime": 5000,
                        "ip_address": "192.168.1.106",
                        "mac_address": "00:1A:2B:3C:4D:63",
                        "wifi_signal": 78,
                        "battery": 76,
                        "temperature": 48.0,
                        "memory": 2048,
                        "disk": 512,
                        "cpu": 20.0,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Announcer Display",
                        "serial": "AD33445566",
                        "uptime": 8400,
                        "ip_address": "192.168.1.107",
                        "mac_address": "00:1A:2B:3C:4D:64",
                        "wifi_signal": 82,
                        "battery": 80,
                        "temperature": 41.3,
                        "memory": 2048,
                        "disk": 256,
                        "cpu": 14.4,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Control Server",
                        "serial": "CS22334455",
                        "uptime": 32400,
                        "ip_address": "192.168.1.108",
                        "mac_address": "00:1A:2B:3C:4D:65",
                        "wifi_signal": 95,
                        "battery": 100,
                        "temperature": 39.9,
                        "memory": 8192,
                        "disk": 1024,
                        "cpu": 5.5,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Leaderboard Display",
                        "serial": "LD11223344",
                        "uptime": 12900,
                        "ip_address": "192.168.1.109",
                        "mac_address": "00:1A:2B:3C:4D:66",
                        "wifi_signal": 68,
                        "battery": 70,
                        "temperature": 43.7,
                        "memory": 4096,
                        "disk": 512,
                        "cpu": 18.2,
                        "last_updated": 1744296000
                    },
                    {
                        "device_name": "Mobile Tablet",
                        "serial": "MT00112233",
                        "uptime": 2400,
                        "ip_address": "192.168.1.110",
                        "mac_address": "00:1A:2B:3C:4D:67",
                        "wifi_signal": 60,
                        "battery": 65,
                        "temperature": 36.5,
                        "memory": 2048,
                        "disk": 128,
                        "cpu": 22.1,
                        "last_updated": 1744296000
                    }
                ];
                
                
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
        }
    });
}

// Function to update the device status table dynamically
function updateDeviceStatusTable(devices) {
    const tbody = document.getElementById("device-statuses");
    tbody.innerHTML = ""; // Clear existing rows

    devices.forEach(device => {
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