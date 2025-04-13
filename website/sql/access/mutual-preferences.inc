<?php

return array(

    "DROP TABLE IF EXISTS mutual_preferences",

    "CREATE TABLE mutual_preferences (
        racerid INT NOT NULL,
        related_racerid INT NOT NULL,
        preference_type VARCHAR(10) NOT NULL,  -- 'include' or 'exclude'
        PRIMARY KEY (racerid, related_racerid, preference_type),
        FOREIGN KEY (racerid) REFERENCES racers(id) ON DELETE CASCADE,
        FOREIGN KEY (related_racerid) REFERENCES racers(id) ON DELETE CASCADE
    )",

    // Create index for fast lookups
    "CREATE INDEX IF NOT EXISTS idx_mutual_preferences_racerid ON mutual_preferences(racerid)",
    "CREATE INDEX IF NOT EXISTS idx_mutual_preferences_related_racerid ON mutual_preferences(related_racerid)",
    "CREATE INDEX IF NOT EXISTS idx_mutual_preferences_preference_type ON mutual_preferences(preference_type)"

);
?>
