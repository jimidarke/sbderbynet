<?php
// LED Sign device registration table
// Mirrors the Kiosks table pattern for HTTP-based device discovery
return array(

"DROP TABLE IF EXISTS LedSigns",
"CREATE TABLE LedSigns ("
." mac VARCHAR(17) PRIMARY KEY,"      // 'AA:BB:CC:DD:EE:FF' format
." zone VARCHAR(50),"                  // Assigned zone (NULL = unassigned)
." ip_address VARCHAR(45),"            // Last known IP address
." firmware_version VARCHAR(20),"      // Reported firmware version
." last_contact INTEGER NOT NULL)",    // Unix timestamp of last poll

);
?>
