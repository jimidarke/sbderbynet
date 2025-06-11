<?php
// Elimination Tournament Database Schema for Microsoft Access

return array(

"DROP TABLE EliminationTournaments",

"CREATE TABLE EliminationTournaments ("
."  tournament_id AUTOINCREMENT PRIMARY KEY, "
."  classid INTEGER NOT NULL, "
."  config_file VARCHAR(100) NOT NULL, "
."  age_group_key VARCHAR(50) NOT NULL, "
."  current_round INTEGER NOT NULL DEFAULT 1, "
."  total_rounds INTEGER NOT NULL, "
."  active YESNO NOT NULL DEFAULT True, "
."  created_at DATETIME DEFAULT Now(), "
."  completed_at DATETIME"
.")",

"CREATE INDEX EliminationTournaments_classid ON EliminationTournaments(classid)",
"CREATE INDEX EliminationTournaments_active ON EliminationTournaments(active)",

"DROP TABLE EliminationRoundState",

"CREATE TABLE EliminationRoundState ("
."  state_id AUTOINCREMENT PRIMARY KEY, "
."  tournament_id INTEGER NOT NULL, "
."  roundid INTEGER NOT NULL, "
."  round_sequence INTEGER NOT NULL, "
."  status VARCHAR(20) NOT NULL DEFAULT 'pending', "
."  races_per_racer INTEGER NOT NULL, "
."  advancement_rule VARCHAR(20) NOT NULL, "
."  advance_count INTEGER DEFAULT 0, "
."  scoring_method VARCHAR(20) NOT NULL, "
."  started_at DATETIME, "
."  completed_at DATETIME"
.")",

"CREATE INDEX EliminationRoundState_tournament_id ON EliminationRoundState(tournament_id)",
"CREATE INDEX EliminationRoundState_roundid ON EliminationRoundState(roundid)",
"CREATE INDEX EliminationRoundState_sequence ON EliminationRoundState(round_sequence)",

"DROP TABLE EliminationAdvancement",

"CREATE TABLE EliminationAdvancement ("
."  advancement_id AUTOINCREMENT PRIMARY KEY, "
."  tournament_id INTEGER NOT NULL, "
."  from_round INTEGER NOT NULL, "
."  to_round INTEGER NOT NULL, "
."  racerid INTEGER NOT NULL, "
."  rank_in_round INTEGER NOT NULL, "
."  score DOUBLE, "
."  advanced YESNO NOT NULL DEFAULT False, "
."  advanced_at DATETIME"
.")",

"CREATE INDEX EliminationAdvancement_tournament_id ON EliminationAdvancement(tournament_id)",
"CREATE INDEX EliminationAdvancement_from_round ON EliminationAdvancement(from_round)",
"CREATE INDEX EliminationAdvancement_to_round ON EliminationAdvancement(to_round)",
"CREATE INDEX EliminationAdvancement_racerid ON EliminationAdvancement(racerid)",

);
?>