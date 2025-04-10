<?php

return array(

    "CREATE TABLE IF NOT EXISTS DeviceStatus (
        device_name VARCHAR(255) NOT NULL,
        serial VARCHAR(255) NOT NULL PRIMARY KEY,
        uptime BIGINT NOT NULL,
        ip_address VARCHAR(45) NOT NULL,
        mac_address VARCHAR(17) NOT NULL,
        wifi_signal INT NOT NULL,
        battery INT NOT NULL,
        temperature FLOAT NOT NULL,
        memory INT NOT NULL,
        disk INT NOT NULL,
        cpu FLOAT NOT NULL,
        last_updated INT NOT NULL
    )"

);
?>
