<?php
// Elimination Tournament Database Schema for SQLite

return array(

"DROP TABLE IF EXISTS `EliminationTournaments`",

"CREATE TABLE `EliminationTournaments` ("
."  `tournament_id` INTEGER PRIMARY KEY, "
."  `classid` INTEGER NOT NULL, "
."  `config_file` VARCHAR(100) NOT NULL, "
."  `age_group_key` VARCHAR(50) NOT NULL, "
."  `current_round` INTEGER NOT NULL DEFAULT 1, "
."  `total_rounds` INTEGER NOT NULL, "
."  `active` BOOLEAN NOT NULL DEFAULT 1, "
."  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
."  `completed_at` TIMESTAMP NULL, "
."  FOREIGN KEY (classid) REFERENCES Classes(classid)"
.")",

"CREATE INDEX IF NOT EXISTS EliminationTournaments_classid ON EliminationTournaments(classid)",
"CREATE INDEX IF NOT EXISTS EliminationTournaments_active ON EliminationTournaments(active)",

"DROP TABLE IF EXISTS `EliminationRoundState`",

"CREATE TABLE `EliminationRoundState` ("
."  `state_id` INTEGER PRIMARY KEY, "
."  `tournament_id` INTEGER NOT NULL, "
."  `roundid` INTEGER NOT NULL, "
."  `round_sequence` INTEGER NOT NULL, "
."  `status` VARCHAR(20) NOT NULL DEFAULT 'pending', " // pending, active, completed
."  `races_per_racer` INTEGER NOT NULL, "
."  `advancement_rule` VARCHAR(20) NOT NULL, "
."  `advance_count` INTEGER DEFAULT 0, "
."  `scoring_method` VARCHAR(20) NOT NULL, "
."  `started_at` TIMESTAMP NULL, "
."  `completed_at` TIMESTAMP NULL, "
."  FOREIGN KEY (tournament_id) REFERENCES EliminationTournaments(tournament_id), "
."  FOREIGN KEY (roundid) REFERENCES Rounds(roundid)"
.")",

"CREATE INDEX IF NOT EXISTS EliminationRoundState_tournament_id ON EliminationRoundState(tournament_id)",
"CREATE INDEX IF NOT EXISTS EliminationRoundState_roundid ON EliminationRoundState(roundid)",
"CREATE INDEX IF NOT EXISTS EliminationRoundState_sequence ON EliminationRoundState(round_sequence)",

"DROP TABLE IF EXISTS `EliminationAdvancement`",

"CREATE TABLE `EliminationAdvancement` ("
."  `advancement_id` INTEGER PRIMARY KEY, "
."  `tournament_id` INTEGER NOT NULL, "
."  `from_round` INTEGER NOT NULL, "
."  `to_round` INTEGER NOT NULL, "
."  `racerid` INTEGER NOT NULL, "
."  `rank_in_round` INTEGER NOT NULL, "
."  `score` DOUBLE NULL, " // time or points depending on scoring method
."  `advanced` BOOLEAN NOT NULL DEFAULT 0, "
."  `advanced_at` TIMESTAMP NULL, "
."  FOREIGN KEY (tournament_id) REFERENCES EliminationTournaments(tournament_id), "
."  FOREIGN KEY (from_round) REFERENCES Rounds(roundid), "
."  FOREIGN KEY (to_round) REFERENCES Rounds(roundid), "
."  FOREIGN KEY (racerid) REFERENCES RegistrationInfo(racerid)"
.")",

"CREATE INDEX IF NOT EXISTS EliminationAdvancement_tournament_id ON EliminationAdvancement(tournament_id)",
"CREATE INDEX IF NOT EXISTS EliminationAdvancement_from_round ON EliminationAdvancement(from_round)",
"CREATE INDEX IF NOT EXISTS EliminationAdvancement_to_round ON EliminationAdvancement(to_round)",
"CREATE INDEX IF NOT EXISTS EliminationAdvancement_racerid ON EliminationAdvancement(racerid)",

);
?>