<?php

return array(

    "CREATE TABLE IF NOT EXISTS TimerStatus (
        lane INT NOT NULL,
        timerID VARCHAR(11) NOT NULL,
        last_heartbeat INT NOT NULL,
        ready TINYINT(1) NOT NULL,
        PRIMARY KEY (lane, timerID)
    )"

);
?>
