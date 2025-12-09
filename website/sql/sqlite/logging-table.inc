<?php
// DerbyNet Logging Tables Schema
// ===============================
//
// Tables for unified log storage and archival tracking.
// Used by log_importer.py to store log entries and by
// log-viewer.php to query and display logs.
//
// Version: 1.0.0
// Date: 2025-12-08

return array(

    // Log entries table (main storage)
    "CREATE TABLE IF NOT EXISTS LogEntries (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_us BIGINT NOT NULL,
        level VARCHAR(10) NOT NULL,
        level_num INTEGER NOT NULL,
        source_device VARCHAR(50) NOT NULL,
        component VARCHAR(50) NOT NULL,
        file_line VARCHAR(100),
        message TEXT NOT NULL,
        context_json TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )",

    // Indexes for efficient querying
    "CREATE INDEX IF NOT EXISTS idx_log_timestamp ON LogEntries(timestamp_us DESC)",
    "CREATE INDEX IF NOT EXISTS idx_log_level ON LogEntries(level_num)",
    "CREATE INDEX IF NOT EXISTS idx_log_source ON LogEntries(source_device)",
    "CREATE INDEX IF NOT EXISTS idx_log_created ON LogEntries(created_at)",

    // Archive tracking table
    "CREATE TABLE IF NOT EXISTS LogArchive (
        archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
        archive_date DATE NOT NULL,
        archive_file VARCHAR(255) NOT NULL,
        entry_count INTEGER NOT NULL,
        file_size INTEGER,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )",

    "CREATE INDEX IF NOT EXISTS idx_archive_date ON LogArchive(archive_date DESC)"

);
?>
