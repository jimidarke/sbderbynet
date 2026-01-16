-- DerbyNet SQLite Schema for Python Testing
-- This schema mirrors the PHP-defined schema in website/sql/sqlite/
-- Keep in sync with schema.inc when making schema changes

-- Core Tables

CREATE TABLE IF NOT EXISTS Classes (
    classid INTEGER PRIMARY KEY,
    class VARCHAR(75) NOT NULL UNIQUE COLLATE NOCASE,
    constituents VARCHAR(100) DEFAULT '',
    rankids VARCHAR(100) DEFAULT '',
    durable INTEGER,
    ntrophies INTEGER DEFAULT -1,
    sortorder INTEGER
);

CREATE TABLE IF NOT EXISTS Ranks (
    rankid INTEGER PRIMARY KEY,
    rank VARCHAR(75) NOT NULL COLLATE NOCASE,
    classid INTEGER NOT NULL,
    ntrophies INTEGER DEFAULT -1,
    sortorder INTEGER,
    FOREIGN KEY (classid) REFERENCES Classes(classid)
);
CREATE INDEX IF NOT EXISTS Ranks_classid ON Ranks(classid);
CREATE INDEX IF NOT EXISTS Ranks_rank ON Ranks(rank);

CREATE TABLE IF NOT EXISTS RegistrationInfo (
    racerid INTEGER PRIMARY KEY,
    carnumber INTEGER NOT NULL,
    carname VARCHAR(30),
    lastname VARCHAR(30) NOT NULL COLLATE NOCASE,
    firstname VARCHAR(30) NOT NULL COLLATE NOCASE,
    classid INTEGER NOT NULL,
    rankid INTEGER NOT NULL,
    partitionid INTEGER NOT NULL DEFAULT 1,
    passedinspection TINYINT(1) DEFAULT 0,
    imagefile VARCHAR(255),
    carphoto VARCHAR(255),
    carweight VARCHAR(255),
    checkin_time INTEGER,
    note VARCHAR(255),
    exclude TINYINT(1) DEFAULT 0,
    registered BOOLEAN DEFAULT 0,
    FOREIGN KEY (classid) REFERENCES Classes(classid),
    FOREIGN KEY (rankid) REFERENCES Ranks(rankid)
);
CREATE INDEX IF NOT EXISTS RegistrationInfo_carnumber ON RegistrationInfo(carnumber);
CREATE INDEX IF NOT EXISTS RegistrationInfo_classid ON RegistrationInfo(classid);
CREATE INDEX IF NOT EXISTS RegistrationInfo_exclude ON RegistrationInfo(exclude);
CREATE INDEX IF NOT EXISTS RegistrationInfo_lastname ON RegistrationInfo(lastname);
CREATE INDEX IF NOT EXISTS RegistrationInfo_passedinspection ON RegistrationInfo(passedinspection);
CREATE INDEX IF NOT EXISTS RegistrationInfo_rankid ON RegistrationInfo(rankid);

CREATE TABLE IF NOT EXISTS Rounds (
    roundid INTEGER PRIMARY KEY,
    round INTEGER NOT NULL,
    roundname VARCHAR NULL,
    classid INTEGER NOT NULL,
    charttype INTEGER,
    phase INTEGER,
    is_triple_elim BOOLEAN DEFAULT 0,
    elim_type VARCHAR(20),
    FOREIGN KEY (classid) REFERENCES Classes(classid)
);
CREATE INDEX IF NOT EXISTS Rounds_classid ON Rounds(classid);
CREATE INDEX IF NOT EXISTS Rounds_round ON Rounds(round);

CREATE TABLE IF NOT EXISTS Roster (
    rosterid INTEGER PRIMARY KEY,
    roundid INTEGER NOT NULL,
    classid INTEGER NOT NULL DEFAULT 0,
    racerid INTEGER NOT NULL,
    finalist TINYINT(1) DEFAULT 0,
    grandfinalist TINYINT(1) DEFAULT 0,
    FOREIGN KEY (roundid) REFERENCES Rounds(roundid),
    FOREIGN KEY (racerid) REFERENCES RegistrationInfo(racerid)
);
CREATE INDEX IF NOT EXISTS Roster_classid ON Roster(classid);
CREATE INDEX IF NOT EXISTS Roster_racerid ON Roster(racerid);
CREATE INDEX IF NOT EXISTS Roster_roundid ON Roster(roundid);

CREATE TABLE IF NOT EXISTS RaceChart (
    resultid INTEGER PRIMARY KEY,
    classid INTEGER,
    roundid INTEGER NOT NULL,
    heat INTEGER NOT NULL,
    lane INTEGER NOT NULL,
    racerid INTEGER,
    chartnumber INTEGER,
    finishtime DOUBLE NULL,
    finishplace INTEGER,
    points INTEGER,
    completed TIMESTAMP,
    ignoretime TINYINT(1) DEFAULT 0,
    masterheat INTEGER DEFAULT 0,
    FOREIGN KEY (roundid) REFERENCES Rounds(roundid),
    FOREIGN KEY (racerid) REFERENCES RegistrationInfo(racerid)
);
CREATE INDEX IF NOT EXISTS RaceChart_chartnumber ON RaceChart(chartnumber);
CREATE INDEX IF NOT EXISTS RaceChart_classid ON RaceChart(classid);
CREATE INDEX IF NOT EXISTS RaceChart_finishtime ON RaceChart(finishtime);
CREATE INDEX IF NOT EXISTS RaceChart_heat ON RaceChart(heat);
CREATE INDEX IF NOT EXISTS RaceChart_lane ON RaceChart(lane);
CREATE INDEX IF NOT EXISTS RaceChart_masterheat ON RaceChart(masterheat);
CREATE INDEX IF NOT EXISTS RaceChart_points ON RaceChart(points);
CREATE INDEX IF NOT EXISTS RaceChart_racerid ON RaceChart(racerid);
CREATE INDEX IF NOT EXISTS RaceChart_roundid ON RaceChart(roundid);

CREATE TABLE IF NOT EXISTS RaceInfo (
    raceinfoid INTEGER PRIMARY KEY,
    itemkey VARCHAR(20) NOT NULL,
    itemvalue VARCHAR(200)
);
CREATE INDEX IF NOT EXISTS RaceInfo_itemkey ON RaceInfo(itemkey);

-- Action History (for audit logging)
CREATE TABLE IF NOT EXISTS ActionHistory (
    historyid INTEGER PRIMARY KEY,
    received TIMESTAMP,
    request TEXT
);

-- Awards Tables
CREATE TABLE IF NOT EXISTS AwardTypes (
    awardtypeid INTEGER PRIMARY KEY,
    awardtype VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS Awards (
    awardid INTEGER PRIMARY KEY,
    awardname VARCHAR(100) NOT NULL,
    awardtypeid INTEGER NOT NULL DEFAULT 1,
    classid INTEGER,
    rankid INTEGER,
    racerid INTEGER DEFAULT 0,
    sort INTEGER DEFAULT 0,
    FOREIGN KEY (awardtypeid) REFERENCES AwardTypes(awardtypeid)
);
CREATE INDEX IF NOT EXISTS Awards_awardtypeid ON Awards(awardtypeid);
CREATE INDEX IF NOT EXISTS Awards_awardname ON Awards(awardname);
CREATE INDEX IF NOT EXISTS Awards_classid ON Awards(classid);
CREATE INDEX IF NOT EXISTS Awards_rankid ON Awards(rankid);
CREATE INDEX IF NOT EXISTS Awards_sort ON Awards(sort);

-- Elimination Tournament Tables
CREATE TABLE IF NOT EXISTS EliminationTournaments (
    tournament_id INTEGER PRIMARY KEY,
    classid INTEGER NOT NULL,
    config_file VARCHAR(100) NOT NULL,
    age_group_key VARCHAR(50) NOT NULL,
    current_round INTEGER NOT NULL DEFAULT 1,
    total_rounds INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (classid) REFERENCES Classes(classid)
);
CREATE INDEX IF NOT EXISTS EliminationTournaments_classid ON EliminationTournaments(classid);
CREATE INDEX IF NOT EXISTS EliminationTournaments_active ON EliminationTournaments(active);

CREATE TABLE IF NOT EXISTS EliminationRoundState (
    state_id INTEGER PRIMARY KEY,
    tournament_id INTEGER NOT NULL,
    roundid INTEGER NOT NULL,
    round_sequence INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    races_per_racer INTEGER NOT NULL,
    advancement_rule VARCHAR(20) NOT NULL,
    advance_count INTEGER DEFAULT 0,
    scoring_method VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (tournament_id) REFERENCES EliminationTournaments(tournament_id),
    FOREIGN KEY (roundid) REFERENCES Rounds(roundid)
);
CREATE INDEX IF NOT EXISTS EliminationRoundState_tournament_id ON EliminationRoundState(tournament_id);
CREATE INDEX IF NOT EXISTS EliminationRoundState_roundid ON EliminationRoundState(roundid);
CREATE INDEX IF NOT EXISTS EliminationRoundState_sequence ON EliminationRoundState(round_sequence);

CREATE TABLE IF NOT EXISTS EliminationAdvancement (
    advancement_id INTEGER PRIMARY KEY,
    tournament_id INTEGER NOT NULL,
    from_round INTEGER NOT NULL,
    to_round INTEGER NOT NULL,
    racerid INTEGER NOT NULL,
    rank_in_round INTEGER NOT NULL,
    score DOUBLE NULL,
    advanced BOOLEAN NOT NULL DEFAULT 0,
    advanced_at TIMESTAMP NULL,
    FOREIGN KEY (tournament_id) REFERENCES EliminationTournaments(tournament_id),
    FOREIGN KEY (from_round) REFERENCES Rounds(roundid),
    FOREIGN KEY (to_round) REFERENCES Rounds(roundid),
    FOREIGN KEY (racerid) REFERENCES RegistrationInfo(racerid)
);
CREATE INDEX IF NOT EXISTS EliminationAdvancement_tournament_id ON EliminationAdvancement(tournament_id);
CREATE INDEX IF NOT EXISTS EliminationAdvancement_from_round ON EliminationAdvancement(from_round);
CREATE INDEX IF NOT EXISTS EliminationAdvancement_to_round ON EliminationAdvancement(to_round);
CREATE INDEX IF NOT EXISTS EliminationAdvancement_racerid ON EliminationAdvancement(racerid);

-- Partitions Table
CREATE TABLE IF NOT EXISTS Partitions (
    partitionid INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sortorder INTEGER DEFAULT 0
);

-- Default partition for unassigned racers
INSERT OR IGNORE INTO Partitions (partitionid, name, sortorder) VALUES (1, 'Default', 0);

-- Device Status Table (for timer/display health tracking)
CREATE TABLE IF NOT EXISTS DeviceStatus (
    device_id VARCHAR(50) PRIMARY KEY,
    device_type VARCHAR(20) NOT NULL,
    lane INTEGER,
    last_seen TIMESTAMP,
    status VARCHAR(20) DEFAULT 'unknown',
    firmware_version VARCHAR(20),
    ip_address VARCHAR(45)
);

-- Timer Status Table
CREATE TABLE IF NOT EXISTS TimerStatus (
    statusid INTEGER PRIMARY KEY,
    timer_id VARCHAR(50),
    last_contact TIMESTAMP,
    state VARCHAR(20),
    lane_mask INTEGER
);

-- Default RaceInfo values for a new database
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('schema', '11');
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('photos-on-now-racing', 'head');
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('show-cars-on-deck', '1');
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('show-racer-photos-rr', '1');
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('show-car-photos-rr', '1');
INSERT OR IGNORE INTO RaceInfo (itemkey, itemvalue) VALUES ('upload-videos', '1');

-- Default Award Types
INSERT OR IGNORE INTO AwardTypes (awardtypeid, awardtype) VALUES (1, 'Design');
INSERT OR IGNORE INTO AwardTypes (awardtypeid, awardtype) VALUES (2, 'Speed');
INSERT OR IGNORE INTO AwardTypes (awardtypeid, awardtype) VALUES (3, 'Other');
