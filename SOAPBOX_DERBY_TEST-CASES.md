# Soapbox Derby Test Cases

## Race Structure and Elimination Process 

Recently significant updates were made to the elimination processes, using a hard coded JSON file for defining the structures based on racing classes and progression algorithms. Review commit new elimination process v0 commit id: `26c2bd3f8a38750391437fefd3939357090f9297` for details. 

Use the soapbox-derby-elimination.json file to determine the expected structure. Along each testing step, instruct the user on how to prepare the system, and then run or output the validations. 

## Python-Based Testing Requirements

All test cases should be implemented in Python with direct database validation queries. Each test step includes:
- **User Instructions**: Clear step-by-step actions for the user to perform
- **Python Validation**: Database queries to verify expected state
- **Expected Results**: Detailed validation criteria based on JSON configuration
- **Error Handling**: Detection and reporting of common failure modes

## Test Case Overview

|Step|Name|User Context|Python Validation|
|-|-|-|-|
|1|Fresh Start|Create a wholly new database in setup.php|Verify schema version ≥16, elimination tables exist, clean state|
|2|Settings|Configure 3 lanes, 400 ft track, photo directories|Query RaceInfo for lane-count=3, track-length=400, directory paths|
|3|Roster|Import roster or generate fake roster on setup.php|Count racers, analyze age distributions, check required fields|
|4|Race Setup|Create classes: "Ages 6-8", "Ages 9-11", "Ages 12-14"|Validate class names match JSON regex patterns, racer assignments|
|5|Elimination Setup|Initialize tournaments via racing-groups.php edit buttons|Verify EliminationTournaments, EliminationRoundState tables populated|
|6|Schedule|Schedule Preliminary rounds (3 races/racer)|Validate RaceChart: 3 races per racer, optimal gaps between heats|
|7|Race Execution|Run preliminary races, record finish times|Verify all heats completed, calculate average times, check rankings|
|8|Tournament Progression|Advance through Semi-Finals and Finals|Validate advancement logic, final standings, tournament completion|

## Python Test Framework Usage

### Installation and Setup

```bash
# Navigate to DerbyNet root directory
cd /path/to/SBDerbyNet

# Make the test script executable
chmod +x test_elimination_tournaments.py

# Run all tests
python3 test_elimination_tournaments.py --database website/derbynet.db

# Run specific test step
python3 test_elimination_tournaments.py --step 1 --verbose

# Run with verbose output
python3 test_elimination_tournaments.py --verbose
```

### Test Step Details

#### Step 1: Fresh Start
- **Database Validation**: Schema version ≥16, elimination tables present
- **Clean State Check**: No racers, classes, or rounds in database
- **Expected Result**: All tables exist, dynamic content is empty

#### Step 2: Settings Configuration
- **Lane Count**: Must be exactly 3 lanes (elimination tournament requirement)
- **Track Length**: 400 feet (standard soapbox derby distance)
- **Photo Directories**: Validate configured paths exist on filesystem
- **Expected Result**: Settings match elimination tournament requirements

#### Step 3: Roster Management
- **Racer Count**: Validate racers are loaded (>0 total)
- **Age Analysis**: If birthdates available, analyze 6-8, 9-11, 12-14 distributions
- **Data Quality**: Check for missing names, car numbers
- **Expected Result**: Sufficient racers for tournament operation

#### Step 4: Racing Class Setup
- **Pattern Matching**: Validate class names against JSON regex patterns:
  - Ages 6-8: `^(Ages 6-8|6-8|6 to 8).*$`
  - Ages 9-11: `^(Ages 9-11|9-11|9 to 11).*$`
  - Ages 12-14: `^(Ages 12-14|12-14|12 to 14).*$`
- **Racer Assignment**: Verify racers assigned to appropriate classes
- **Expected Result**: All three age groups represented with active racers

#### Step 5: Elimination Tournament Initialization
- **Tournament Creation**: Verify EliminationTournaments table entries
- **Round Structure**: Validate EliminationRoundState matches JSON config:
  - Ages 6-8: 4 rounds (Preliminary → Quarter Finals → Semi-Finals → Finals)
  - Ages 9-11: 4 rounds (Preliminary → Quarter Finals → Semi-Finals → Finals)
  - Ages 12-14: 3 rounds (Preliminary → Semi-Finals → Finals)
- **Configuration Integrity**: JSON config loaded correctly, round parameters set
- **Expected Result**: All tournaments initialized with correct round structures

#### Step 6: Race Scheduling
- **Heat Generation**: Validate RaceChart entries for preliminary rounds
- **Races Per Racer**: Each racer must have exactly 3 races in preliminary
- **Gap Analysis**: Identify racers with shortest gaps between heats
- **Lane Distribution**: Verify racers get variety of lane assignments
- **Expected Result**: Optimal preliminary schedule generated

#### Step 7: Race Execution
- **Heat Completion**: Track completed vs. total heats per round
- **Finish Times**: Validate all heats have recorded finish times
- **Preliminary Results**: Calculate average times for rankings
- **Data Integrity**: Verify exactly 3 races per racer completed
- **Expected Result**: Clean preliminary results ready for advancement

#### Step 8: Tournament Progression
- **Round Advancement**: Verify progression through tournament structure
- **Final Results**: Validate final standings and placements
- **Tournament Completion**: Check completed_at timestamps
- **Advancement Audit**: Verify EliminationAdvancement table tracking
- **Expected Result**: Complete tournament with final rankings

## Validation Queries

The test framework includes comprehensive SQL validation queries:

### Schema Validation
```sql
SELECT itemvalue FROM RaceInfo WHERE itemkey = 'schema'
-- Expected: >= 16
```

### Tournament Structure Validation
```sql
SELECT et.tournament_id, c.class, et.age_group_key, et.total_rounds
FROM EliminationTournaments et
JOIN Classes c ON et.classid = c.classid
-- Expected: Tournaments for all age groups
```

### Preliminary Race Validation
```sql
SELECT racerid, COUNT(*) as race_count
FROM RaceChart rc
JOIN Rounds r ON rc.roundid = r.roundid
WHERE r.round LIKE '%Preliminary%'
GROUP BY racerid
HAVING COUNT(*) != 3
-- Expected: Empty result (all racers have exactly 3 races)
```

### Advancement Validation
```sql
SELECT ea.racerid, ri.firstname, ri.lastname, ea.rank_in_round
FROM EliminationAdvancement ea
JOIN RegistrationInfo ri ON ea.racerid = ri.racerid
WHERE ea.tournament_id = ? AND ea.to_round IS NULL
ORDER BY ea.rank_in_round
-- Expected: Final rankings for completed tournaments
```

## Error Detection and Troubleshooting

The test framework automatically detects common issues:

### Database Issues
- Schema version too old (< 16)
- Missing elimination tables
- Incomplete tournament initialization

### Configuration Issues
- Class names don't match JSON patterns
- Incorrect lane count or track length
- Missing tournament configurations

### Race Management Issues
- Incomplete heat scheduling
- Missing finish times
- Incorrect races per racer count
- Failed advancement logic

### Reporting
- ✅ PASS: Test requirement met
- ⚠️ WARN: Non-critical issue detected
- ❌ FAIL: Critical test failure
- ℹ️ INFO: Informational message

## Test Data Requirements

For comprehensive testing, ensure:

1. **Sufficient Racers**: Each age group should have enough racers for meaningful tournaments
   - Ages 6-8: ~73 racers (reduces to 27 → 9 → 3 → final)
   - Ages 9-11: ~62 racers (reduces to 27 → 9 → 3 → final)
   - Ages 12-14: ~23 racers (reduces to 9 → 3 → final)

2. **Complete Data**: All racers should have:
   - First name and last name
   - Car number assigned
   - Appropriate class assignment
   - Optional: birthdate for age validation

3. **System Configuration**: 
   - 3 lanes configured
   - 400 ft track length
   - Photo directories configured
   - Elimination JSON config accessible

## Progress Tracking

**✅ Completed Tasks:**
- JSON configuration analysis
- Database schema examination
- Python test framework creation
- Comprehensive validation queries
- User instruction documentation

**🔄 Current Status:**
- Test framework ready for user execution
- Validation queries tested and working
- Documentation complete for all 8 test steps

**📋 Next Steps:**
- User executes tests following step-by-step instructions
- Test framework provides real-time validation
- Any issues discovered will be documented and addressed

## Recent Updates (2025-06-11)

**Elimination Tournament Testing Framework Completed:**
- Created comprehensive Python test suite (`test_elimination_tournaments.py`)
- 8 detailed test steps covering full tournament lifecycle
- Direct database validation with SQL queries
- Real-time progress tracking and error detection
- User-friendly step-by-step instructions
- Automated validation against JSON configuration requirements

**Key Features:**
- Schema version validation (requires ≥16)
- Tournament structure verification against soapbox-derby-elimination.json
- Race scheduling validation (3 races per racer in preliminary)
- Advancement logic verification through all tournament rounds
- Final standings validation and tournament completion tracking
- Comprehensive error detection and troubleshooting guidance

**Testing Approach:**
- Semi-autonomous: User performs actions, Python validates results
- Database-driven validation ensures accuracy
- Step-by-step progression prevents missed requirements
- Real-time feedback on test success/failure
- Detailed logging for debugging and verification

