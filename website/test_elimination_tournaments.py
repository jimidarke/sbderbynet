#!/usr/bin/env python3
"""
Soapbox Derby Elimination Tournament Test Suite

This module provides comprehensive testing for the elimination tournament system
implemented in DerbyNet. It validates database state, tournament progression,
and race scheduling according to the soapbox-derby-elimination.json configuration.

Test Execution:
    python3 test_elimination_tournaments.py --database /full/path/to/database.db
    python3 test_elimination_tournaments.py --database /path/to/db.db --website-root /path/to/website
    python3 test_elimination_tournaments.py --database /path/to/db.db --step 1  # Run specific test step
    python3 test_elimination_tournaments.py --database /path/to/db.db --verbose  # Detailed output

Requirements:
    - Python 3.6+
    - sqlite3 (built-in)
    - DerbyNet database with elimination tournament schema (version >= 16)
"""

import sqlite3
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

class EliminationTournamentTester:
    """Main test class for elimination tournament validation."""
    
    def __init__(self, database_path: str, website_root: str = None, verbose: bool = False):
        """Initialize tester with database connection."""
        self.database_path = database_path
        self.website_root = website_root or os.path.dirname(os.path.abspath(__file__))
        self.verbose = verbose
        self.conn = None
        self.config = None
        
        # Load elimination configuration using website root
        config_path = os.path.join(self.website_root, "inc/elimination-configs/soapbox-derby-elimination.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    def connect_database(self) -> bool:
        """Establish database connection and verify schema."""
        try:
            self.conn = sqlite3.connect(self.database_path)
            self.conn.row_factory = sqlite3.Row
            
            # Verify schema version
            cursor = self.conn.cursor()
            cursor.execute("SELECT itemvalue FROM RaceInfo WHERE itemkey = 'schema'")
            result = cursor.fetchone()
            
            if not result:
                print("❌ Schema version not found in database")
                return False
                
            schema_version = int(result[0])
            if schema_version < 16:
                print(f"❌ Schema version {schema_version} too old (need >= 16 for elimination tournaments)")
                return False
                
            if self.verbose:
                print(f"✅ Database connected, schema version: {schema_version}")
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def log_step(self, step: str, message: str, status: str = "INFO"):
        """Log test step with formatting."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
        print(f"[{timestamp}] {status_icon.get(status, '•')} {step}: {message}")
    
    def wait_for_user(self, message: str = "Press Enter to continue..."):
        """Pause execution and wait for user input."""
        print(f"\n🛑 {message}")
        input()
    
    def print_user_instructions(self, step_num: int, instructions: List[str]):
        """Display formatted user instructions."""
        print(f"\n📋 USER INSTRUCTIONS - STEP {step_num}:")
        print("="*50)
        for i, instruction in enumerate(instructions, 1):
            print(f"{i}. {instruction}")
        print("="*50)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute SQL query and return results."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            self.log_step("Database", f"Query failed: {e}", "FAIL")
            return []
    
    def test_step_1_fresh_start(self) -> bool:
        """
        Step 1: Fresh Start - Verify clean database state
        """
        instructions = [
            "Navigate to setup.php in your browser",
            "Create a new database (or reset existing one)",
            "Complete the initial setup process",
            "Return to this test and press Enter"
        ]
        
        self.print_user_instructions(1, instructions)
        self.wait_for_user("Complete the setup process, then press Enter to validate...")
        
        self.log_step("Step 1", "Testing fresh database start...")
        
        # Check schema version
        schema_result = self.execute_query("SELECT itemvalue FROM RaceInfo WHERE itemkey = 'schema'")
        if not schema_result:
            self.log_step("Step 1", "Schema version not set", "FAIL")
            return False
        
        schema_version = int(schema_result[0][0])
        self.log_step("Step 1", f"Schema version: {schema_version}", "PASS" if schema_version >= 16 else "FAIL")
        
        # Check that essential tables exist
        tables_to_check = [
            'RegistrationInfo', 'Classes', 'Rounds', 'RaceChart', 
            'EliminationTournaments', 'EliminationRoundState', 'EliminationAdvancement'
        ]
        
        for table in tables_to_check:
            result = self.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if result:
                self.log_step("Step 1", f"Table {table} exists", "PASS")
            else:
                self.log_step("Step 1", f"Table {table} missing", "FAIL")
                return False
        
        # Check that dynamic content is empty
        racer_count = self.execute_query("SELECT COUNT(*) as count FROM RegistrationInfo")[0][0]
        class_count = self.execute_query("SELECT COUNT(*) as count FROM Classes")[0][0]
        round_count = self.execute_query("SELECT COUNT(*) as count FROM Rounds")[0][0]
        
        self.log_step("Step 1", f"Racers: {racer_count}, Classes: {class_count}, Rounds: {round_count}", 
                     "PASS" if racer_count == 0 and round_count == 0 else "INFO")
        
        return True
    
    def test_step_2_settings(self) -> bool:
        """
        Step 2: Settings Configuration
        """
        instructions = [
            "Go to settings.php or the Settings page",
            "Set 'Number of lanes' to 3",
            "Set 'Track length' to 400",
            "Configure photo directories (racers, cars, videos, slides)",
            "Save settings and return to this test"
        ]
        
        self.print_user_instructions(2, instructions)
        self.wait_for_user("Complete the settings configuration, then press Enter to validate...")
        
        self.log_step("Step 2", "Testing settings configuration...")
        
        # Check lane count
        lane_result = self.execute_query("SELECT itemvalue FROM RaceInfo WHERE itemkey = 'lane_count'")
        if lane_result:
            lane_count = int(lane_result[0][0])
            self.log_step("Step 2", f"Lane count: {lane_count}", "PASS" if lane_count == 3 else "FAIL")
            if lane_count != 3:
                return False
        else:
            self.log_step("Step 2", "Lane count not configured", "FAIL")
            return False
        
        # Check track length
        length_result = self.execute_query("SELECT itemvalue FROM RaceInfo WHERE itemkey = 'track-length'")
        if length_result:
            track_length = float(length_result[0][0])
            self.log_step("Step 2", f"Track length: {track_length} ft", "PASS" if track_length == 400.0 else "WARN")
        else:
            self.log_step("Step 2", "Track length not configured", "WARN")
        
        # Check photo directories (optional validation)
        photo_dirs = ['photo-dir', 'car-photo-dir', 'video-dir', 'slideshow-directory']
        for dir_key in photo_dirs:
            dir_result = self.execute_query("SELECT itemvalue FROM RaceInfo WHERE itemkey = ?", (dir_key,))
            if dir_result:
                dir_path = dir_result[0][0]
                exists = os.path.exists(dir_path) if dir_path else False
                status = "PASS" if exists else "WARN"
                self.log_step("Step 2", f"Directory {dir_key}: {dir_path} ({'exists' if exists else 'missing'})", status)
            else:
                self.log_step("Step 2", f"Directory {dir_key} not configured", "WARN")
        
        return True
    
    def test_step_3_roster(self) -> bool:
        """
        Step 3: Roster Import/Generation
        """
        instructions = [
            "Go to setup.php",
            "Either import a CSV roster OR generate a fake roster",
            "Ensure you have racers in the age groups: 6-8, 9-11, 12-14",
            "For fake roster: recommend generating at least 150+ racers",
            "Return to this test"
        ]
        
        self.print_user_instructions(3, instructions)
        self.wait_for_user("Complete the roster setup, then press Enter to validate...")
        
        self.log_step("Step 3", "Testing roster data...")
        
        # Count total racers
        total_racers = self.execute_query("SELECT COUNT(*) as count FROM RegistrationInfo")[0][0]
        if total_racers == 0:
            self.log_step("Step 3", "No racers found - import or generate roster first", "FAIL")
            return False
        
        self.log_step("Step 3", f"Total racers: {total_racers}", "PASS")
        
        # Analyze age distribution (if birthdate available)
        age_query = """
        SELECT 
            CASE 
                WHEN (julianday('now') - julianday(birthdate)) / 365.25 BETWEEN 6 AND 8 THEN '6-8'
                WHEN (julianday('now') - julianday(birthdate)) / 365.25 BETWEEN 9 AND 11 THEN '9-11'
                WHEN (julianday('now') - julianday(birthdate)) / 365.25 BETWEEN 12 AND 14 THEN '12-14'
                ELSE 'Other'
            END as age_group,
            COUNT(*) as count
        FROM RegistrationInfo 
        WHERE birthdate IS NOT NULL AND birthdate != ''
        GROUP BY age_group
        """
        
        age_results = self.execute_query(age_query)
        if age_results:
            for row in age_results:
                self.log_step("Step 3", f"Age group {row[0]}: {row[1]} racers", "INFO")
        else:
            self.log_step("Step 3", "No birthdate data available for age analysis", "WARN")
        
        # Check for required fields
        fields_query = """
        SELECT 
            SUM(CASE WHEN firstname IS NULL OR firstname = '' THEN 1 ELSE 0 END) as missing_firstname,
            SUM(CASE WHEN lastname IS NULL OR lastname = '' THEN 1 ELSE 0 END) as missing_lastname,
            SUM(CASE WHEN carnumber IS NULL OR carnumber = 0 THEN 1 ELSE 0 END) as missing_carnumber
        FROM RegistrationInfo
        """
        
        field_results = self.execute_query(fields_query)[0]
        for field, count in zip(['firstname', 'lastname', 'carnumber'], field_results):
            if count > 0:
                self.log_step("Step 3", f"{count} racers missing {field}", "WARN")
            else:
                self.log_step("Step 3", f"All racers have {field}", "PASS")
        
        return True
    
    def test_step_4_race_setup(self) -> bool:
        """
        Step 4: Racing Class Setup
        """
        instructions = [
            "Go to racing-groups.php",
            "Create or edit racing classes to match these names:",
            "  - 'Ages 6-8' (or similar: '6-8', '6 to 8')",
            "  - 'Ages 9-11' (or similar: '9-11', '9 to 11')",
            "  - 'Ages 12-14' (or similar: '12-14', '12 to 14')",
            "Assign racers to appropriate classes (manually or by rule)",
            "Return to this test"
        ]
        
        self.print_user_instructions(4, instructions)
        self.wait_for_user("Complete the racing class setup, then press Enter to validate...")
        
        self.log_step("Step 4", "Testing racing class setup...")
        
        # Get all classes
        classes_query = "SELECT classid, class FROM Classes ORDER BY sortorder"
        classes = self.execute_query(classes_query)
        
        if not classes:
            self.log_step("Step 4", "No racing classes found", "FAIL")
            return False
        
        # Check class names against JSON patterns
        matched_groups = {}
        for class_row in classes:
            class_name = class_row[1]
            self.log_step("Step 4", f"Found class: '{class_name}'", "INFO")
            
            # Check against each age group pattern
            for group_key, group_config in self.config['age_groups'].items():
                import re
                pattern = group_config['class_name_pattern']
                if re.match(pattern, class_name, re.IGNORECASE):
                    matched_groups[group_key] = {
                        'classid': class_row[0],
                        'class_name': class_name,
                        'expected_racers': group_config['expected_racers']
                    }
                    self.log_step("Step 4", f"Class '{class_name}' matches {group_config['name']}", "PASS")
                    break
        
        # Validate we have all required age groups
        required_groups = list(self.config['age_groups'].keys())
        missing_groups = set(required_groups) - set(matched_groups.keys())
        
        if missing_groups:
            for group in missing_groups:
                group_name = self.config['age_groups'][group]['name']
                pattern = self.config['age_groups'][group]['class_name_pattern']
                self.log_step("Step 4", f"Missing class for {group_name} (pattern: {pattern})", "FAIL")
            return False
        
        # Check racer distribution across classes
        for group_key, group_info in matched_groups.items():
            racer_query = "SELECT COUNT(*) as count FROM RegistrationInfo WHERE classid = ?"
            racer_count = self.execute_query(racer_query, (group_info['classid'],))[0][0]
            expected = group_info['expected_racers']
            
            status = "PASS" if racer_count > 0 else "WARN"
            self.log_step("Step 4", f"Class '{group_info['class_name']}': {racer_count} racers (expected ~{expected})", status)
        
        return True
    
    def test_step_5_elimination_setup(self) -> bool:
        """
        Step 5: Elimination Tournament Initialization
        """
        instructions = [
            "Go to racing-groups.php",
            "For each age group class, click the 'Edit' button",
            "Select 'soapbox-derby-elimination.json' as the elimination configuration",
            "Click 'Initialize Elimination Tournament'",
            "Repeat for all age groups (Ages 6-8, 9-11, 12-14)",
            "Return to this test"
        ]
        
        self.print_user_instructions(5, instructions)
        self.wait_for_user("Complete the elimination tournament setup, then press Enter to validate...")
        
        self.log_step("Step 5", "Testing elimination tournament setup...")
        
        # Get all classes and check for tournaments
        classes_query = "SELECT classid, class FROM Classes ORDER BY sortorder"
        classes = self.execute_query(classes_query)
        
        tournament_count = 0
        for class_row in classes:
            classid, class_name = class_row[0], class_row[1]
            
            # Check if elimination tournament exists for this class
            tournament_query = """
            SELECT tournament_id, config_file, age_group_key, current_round, total_rounds, active
            FROM EliminationTournaments 
            WHERE classid = ?
            """
            tournament = self.execute_query(tournament_query, (classid,))
            
            if tournament:
                tournament_count += 1
                t = tournament[0]
                self.log_step("Step 5", f"Tournament for '{class_name}': {t[2]} ({t[4]} rounds, currently on round {t[3]})", "PASS")
                
                # Validate tournament configuration
                age_group_key = t[2]
                if age_group_key in self.config['age_groups']:
                    expected_rounds = len(self.config['age_groups'][age_group_key]['rounds'])
                    actual_rounds = t[4]
                    
                    if expected_rounds == actual_rounds:
                        self.log_step("Step 5", f"Round count matches config: {actual_rounds}", "PASS")
                    else:
                        self.log_step("Step 5", f"Round count mismatch: expected {expected_rounds}, got {actual_rounds}", "FAIL")
                        return False
                
                # Check round state entries
                round_state_query = """
                SELECT ers.round_sequence, r.round, ers.races_per_racer, ers.advance_count, ers.status
                FROM EliminationRoundState ers
                JOIN Rounds r ON ers.roundid = r.roundid
                WHERE ers.tournament_id = ?
                ORDER BY ers.round_sequence
                """
                round_states = self.execute_query(round_state_query, (t[0],))
                
                for rs in round_states:
                    seq, name, races_per_racer, advance_count, status = rs
                    self.log_step("Step 5", f"  Round {seq}: {name} ({races_per_racer} races/racer, {advance_count} advance, {status})", "INFO")
                
            else:
                self.log_step("Step 5", f"No tournament found for class '{class_name}'", "WARN")
        
        if tournament_count == 0:
            self.log_step("Step 5", "No elimination tournaments initialized", "FAIL")
            return False
        
        self.log_step("Step 5", f"Found {tournament_count} elimination tournaments", "PASS")
        return True
    
    def test_step_6_schedule(self) -> bool:
        """
        Step 6: Race Scheduling
        """
        instructions = [
            "Go to coordinator.php",
            "Select the first class's 'Preliminary' round",
            "Click 'Schedule + Race' (modal should detect elimination tournament)",
            "The modal should show orange styling and disable dropdown for elimination",
            "Schedule the preliminary round (3 races per racer)",
            "Repeat for other classes if desired",
            "Return to this test"
        ]
        
        self.print_user_instructions(6, instructions)
        self.wait_for_user("Complete the race scheduling, then press Enter to validate...")
        
        self.log_step("Step 6", "Testing race scheduling...")
        
        # Find preliminary rounds (Round 1 for elimination tournaments) with race charts
        preliminary_query = """
        SELECT r.roundid, r.round, c.class, COUNT(rc.resultid) as heat_count,
               COUNT(DISTINCT rc.racerid) as unique_racers,
               COUNT(rc.resultid) / COUNT(DISTINCT rc.racerid) as avg_races_per_racer
        FROM Rounds r
        JOIN Classes c ON r.classid = c.classid
        LEFT JOIN RaceChart rc ON r.roundid = rc.roundid
        WHERE r.round = '1' AND EXISTS (
            SELECT 1 FROM EliminationTournaments et WHERE et.classid = r.classid
        )
        GROUP BY r.roundid, r.round, c.class
        HAVING COUNT(rc.resultid) > 0
        """
        
        preliminary_rounds = self.execute_query(preliminary_query)
        
        if not preliminary_rounds:
            self.log_step("Step 6", "No scheduled preliminary rounds found (first round of elimination tournaments)", "FAIL")
            return False
        
        for round_row in preliminary_rounds:
            roundid, round_name, class_name, heat_count, unique_racers, avg_races = round_row
            self.log_step("Step 6", f"Round '{round_name}' ({class_name}): {heat_count} heats, {unique_racers} racers", "INFO")
            
            # For elimination tournaments, preliminary should have 3 races per racer
            if avg_races < 2.9 or avg_races > 3.1:  # Allow slight variance due to integer division
                self.log_step("Step 6", f"Unexpected races per racer: {avg_races:.2f} (expected ~3.0)", "WARN")
            else:
                self.log_step("Step 6", f"Races per racer: {avg_races:.2f}", "PASS")
            
            # Analyze race gaps (time between races for same racer)
            gap_query = """
            SELECT racerid, 
                   GROUP_CONCAT(heat ORDER BY heat) as heats,
                   MAX(heat) - MIN(heat) as heat_span
            FROM RaceChart 
            WHERE roundid = ?
            GROUP BY racerid
            ORDER BY heat_span
            LIMIT 5
            """
            
            gap_results = self.execute_query(gap_query, (roundid,))
            if gap_results:
                self.log_step("Step 6", "Racers with shortest gaps between heats:", "INFO")
                for gap_row in gap_results:
                    racerid, heats, span = gap_row
                    racer_query = "SELECT firstname, lastname FROM RegistrationInfo WHERE racerid = ?"
                    racer_info = self.execute_query(racer_query, (racerid,))
                    if racer_info:
                        name = f"{racer_info[0][0]} {racer_info[0][1]}"
                        self.log_step("Step 6", f"  {name}: heats {heats} (span: {span})", "INFO")
        
        return True
    
    def test_step_7_race_execution(self) -> bool:
        """
        Step 7: Race Execution and Results
        """
        instructions = [
            "Go to coordinator.php",
            "Start racing the preliminary rounds",
            "For each heat, manually enter finish times or simulate results",
            "Continue until all preliminary rounds are complete",
            "Note: Each racer should complete exactly 3 races",
            "Return to this test"
        ]
        
        self.print_user_instructions(7, instructions)
        self.wait_for_user("Complete the preliminary race execution, then press Enter to validate...")
        
        self.log_step("Step 7", "Testing race execution and results...")
        
        # Find completed preliminary rounds (Round 1 for elimination tournaments)
        completed_query = """
        SELECT r.roundid, r.round, c.class,
               COUNT(rc.resultid) as total_heats,
               COUNT(CASE WHEN rc.finishtime IS NOT NULL AND rc.finishtime > 0 THEN 1 END) as completed_heats,
               COUNT(DISTINCT rc.racerid) as total_racers
        FROM Rounds r
        JOIN Classes c ON r.classid = c.classid
        JOIN RaceChart rc ON r.roundid = rc.roundid
        WHERE r.round = '1' AND EXISTS (
            SELECT 1 FROM EliminationTournaments et WHERE et.classid = r.classid
        )
        GROUP BY r.roundid, r.round, c.class
        """
        
        completed_rounds = self.execute_query(completed_query)
        
        for round_row in completed_rounds:
            roundid, round_name, class_name, total_heats, completed_heats, total_racers = round_row
            completion_pct = (completed_heats / total_heats * 100) if total_heats > 0 else 0
            
            self.log_step("Step 7", f"Round '{round_name}' ({class_name}): {completed_heats}/{total_heats} heats complete ({completion_pct:.1f}%)", 
                         "PASS" if completion_pct == 100 else "INFO")
            
            if completion_pct == 100:
                # Calculate preliminary results (average times)
                results_query = """
                SELECT ri.racerid, ri.firstname, ri.lastname,
                       COUNT(rc.finishtime) as race_count,
                       AVG(rc.finishtime) as avg_time,
                       MIN(rc.finishtime) as best_time
                FROM RegistrationInfo ri
                JOIN RaceChart rc ON ri.racerid = rc.racerid
                WHERE rc.roundid = ? AND rc.finishtime IS NOT NULL AND rc.finishtime > 0
                GROUP BY ri.racerid, ri.firstname, ri.lastname
                HAVING COUNT(rc.finishtime) = 3
                ORDER BY avg_time
                LIMIT 10
                """
                
                results = self.execute_query(results_query, (roundid,))
                if results:
                    self.log_step("Step 7", f"Top 10 preliminary results for {class_name}:", "INFO")
                    for i, result_row in enumerate(results, 1):
                        racerid, firstname, lastname, race_count, avg_time, best_time = result_row
                        self.log_step("Step 7", f"  {i:2d}. {firstname} {lastname}: {avg_time:.3f}s avg ({race_count} races)", "INFO")
                
                # Check for advancement readiness
                tournament_query = "SELECT tournament_id FROM EliminationTournaments WHERE classid = (SELECT classid FROM Rounds WHERE roundid = ?)"
                tournament_result = self.execute_query(tournament_query, (roundid,))
                
                if tournament_result:
                    tournament_id = tournament_result[0][0]
                    advancement_query = "SELECT COUNT(*) FROM EliminationAdvancement WHERE tournament_id = ? AND from_round = ?"
                    advancement_count = self.execute_query(advancement_query, (tournament_id, roundid))[0][0]
                    
                    if advancement_count > 0:
                        self.log_step("Step 7", f"Advancement already processed: {advancement_count} racers", "PASS")
                    else:
                        self.log_step("Step 7", "Round complete but advancement not processed", "WARN")
        
        return True
    
    def test_step_8_tournament_progression(self) -> bool:
        """
        Step 8: Tournament Progression (Semi-Finals and Finals)
        """
        instructions = [
            "Use coordinator.php to advance tournaments to next rounds",
            "After preliminary completion, advancement should be available",
            "Schedule and race Semi-Finals and Finals as they become available",
            "Complete all tournament rounds for at least one age group",
            "Note final standings and placements",
            "Return to this test"
        ]
        
        self.print_user_instructions(8, instructions)
        self.wait_for_user("Complete the tournament progression, then press Enter to validate...")
        
        self.log_step("Step 8", "Testing tournament progression...")
        
        # Check tournament completion status
        tournament_status_query = """
        SELECT et.tournament_id, c.class, et.current_round, et.total_rounds,
               et.active, et.completed_at
        FROM EliminationTournaments et
        JOIN Classes c ON et.classid = c.classid
        ORDER BY c.class
        """
        
        tournaments = self.execute_query(tournament_status_query)
        
        for tournament_row in tournaments:
            tournament_id, class_name, current_round, total_rounds, active, completed_at = tournament_row
            
            status = "COMPLETED" if completed_at else f"Round {current_round}/{total_rounds}"
            self.log_step("Step 8", f"Tournament '{class_name}': {status}", 
                         "PASS" if completed_at else "INFO")
            
            # Check final results if tournament is complete
            if completed_at:
                final_results_query = """
                SELECT ea.racerid, ri.firstname, ri.lastname, ea.rank_in_round, ea.score
                FROM EliminationAdvancement ea
                JOIN RegistrationInfo ri ON ea.racerid = ri.racerid
                WHERE ea.tournament_id = ? AND ea.to_round IS NULL
                ORDER BY ea.rank_in_round
                """
                
                final_results = self.execute_query(final_results_query, (tournament_id,))
                if final_results:
                    self.log_step("Step 8", f"Final standings for {class_name}:", "INFO")
                    for result_row in final_results:
                        racerid, firstname, lastname, rank, score = result_row
                        place_suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank, "th")
                        self.log_step("Step 8", f"  {rank}{place_suffix} place: {firstname} {lastname} ({score:.3f}s)", "INFO")
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all test steps in sequence with user interaction."""
        print("🎯 SOAPBOX DERBY ELIMINATION TOURNAMENT TEST SUITE")
        print("="*60)
        print("This is an interactive testing framework that will guide you")
        print("through setting up and validating the elimination tournament system.")
        print("You'll be prompted to perform actions, then the system will validate.")
        print("="*60)
        
        if not self.connect_database():
            return False
        
        test_methods = [
            self.test_step_1_fresh_start,
            self.test_step_2_settings,
            self.test_step_3_roster,
            self.test_step_4_race_setup,
            self.test_step_5_elimination_setup,
            self.test_step_6_schedule,
            self.test_step_7_race_execution,
            self.test_step_8_tournament_progression,
        ]
        
        passed = 0
        for i, test_method in enumerate(test_methods, 1):
            print(f"\n{'='*60}")
            print(f"🏁 TEST STEP {i} OF {len(test_methods)}")
            print(f"{'='*60}")
            
            try:
                if test_method():
                    passed += 1
                    self.log_step(f"Step {i}", "PASSED ✅", "PASS")
                else:
                    self.log_step(f"Step {i}", "FAILED ❌", "FAIL")
                    print(f"\n⚠️  Step {i} failed. You may:")
                    print("1. Fix the issue and re-run this specific step")
                    print("2. Continue to next step (not recommended)")
                    print("3. Exit and restart testing")
                    
                    choice = input("\nContinue to next step anyway? (y/N): ").lower()
                    if choice != 'y':
                        print("🛑 Testing stopped. Fix issues and restart.")
                        return False
                        
            except Exception as e:
                self.log_step(f"Step {i}", f"ERROR: {e}", "FAIL")
                print(f"\n💥 Unexpected error in Step {i}")
                print("This usually indicates a database connection or configuration issue.")
                return False
        
        print(f"\n{'='*60}")
        print(f"🏆 TEST SUMMARY: {passed}/{len(test_methods)} steps passed")
        if passed == len(test_methods):
            print("🎉 ALL TESTS PASSED! Elimination tournament system is ready.")
        else:
            print("⚠️  Some tests failed. Review the issues above.")
        print(f"{'='*60}")
        
        return passed == len(test_methods)
    
    def run_specific_step(self, step_number: int) -> bool:
        """Run a specific test step with user interaction."""
        if not self.connect_database():
            return False
        
        test_methods = {
            1: self.test_step_1_fresh_start,
            2: self.test_step_2_settings,
            3: self.test_step_3_roster,
            4: self.test_step_4_race_setup,
            5: self.test_step_5_elimination_setup,
            6: self.test_step_6_schedule,
            7: self.test_step_7_race_execution,
            8: self.test_step_8_tournament_progression,
        }
        
        if step_number not in test_methods:
            print(f"❌ Invalid step number: {step_number}")
            print("Valid steps: 1-8")
            return False
        
        print(f"🎯 RUNNING SPECIFIC TEST STEP {step_number}")
        print("="*40)
        
        try:
            result = test_methods[step_number]()
            status = "PASSED ✅" if result else "FAILED ❌"
            self.log_step(f"Step {step_number}", status, "PASS" if result else "FAIL")
            
            if result:
                print(f"\n🎉 Step {step_number} completed successfully!")
            else:
                print(f"\n⚠️  Step {step_number} failed. Check the validation messages above.")
                
            return result
        except Exception as e:
            self.log_step(f"Step {step_number}", f"ERROR: {e}", "FAIL")
            print(f"\n💥 Unexpected error in Step {step_number}: {e}")
            return False


def main():
    """Main entry point for test execution."""
    parser = argparse.ArgumentParser(description="Soapbox Derby Elimination Tournament Test Suite")
    parser.add_argument("--database", "-d", required=True,
                       help="Full path to DerbyNet database file")
    parser.add_argument("--website-root", "-w", 
                       help="Full path to website root directory (defaults to script directory)")
    parser.add_argument("--step", "-s", type=int, 
                       help="Run specific test step (1-8)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.database):
        print(f"❌ Database file not found: {args.database}")
        return False
    
    # Validate website root if provided
    if args.website_root and not os.path.exists(args.website_root):
        print(f"❌ Website root directory not found: {args.website_root}")
        return False
    
    tester = EliminationTournamentTester(args.database, args.website_root, args.verbose)
    
    if args.step:
        return tester.run_specific_step(args.step)
    else:
        return tester.run_all_tests()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)