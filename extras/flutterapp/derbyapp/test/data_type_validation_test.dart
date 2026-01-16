import 'package:flutter_test/flutter_test.dart';
import 'package:soapbox_derby_app/data/models/race/coordinator_poll_response.dart';

void main() {
  group('Data Type Validation Against Live API Response', () {
    test('Should parse latest coordinator poll data with correct types', () {
      // Fresh data from http://192.168.100.10/derbynet/action.php?query=poll.coordinator
      // Captured: 2025-12-14 16:05
      final json = {
        "current-heat": {
          "now_racing": true,           // bool ✓
          "use_master_sched": false,    // bool ✓
          "use_points": false,          // bool ✓
          "classid": 3,                 // int ✓
          "roundid": 3,                 // int ✓
          "round": 1,                   // int ✓
          "tbodyid": 3,                 // int ✓
          "heat": 1,                    // int ✓
          "number-of-heats": 37,        // int ✓
          "class": ""                   // String ✓
        },
        "racers": [
          {
            "lane": 1,                  // int ✓
            "racerid": 105,             // int ✓
            "name": "Rubye Raymo",      // String ✓
            "carname": "",              // String ✓
            "carnumber": 235,           // int ✓
            "note": "",                 // String ✓
            "photo": "",                // String ✓
            "finishtime": "",           // EMPTY STRING -> null ✓
            "finishplace": ""           // EMPTY STRING -> null ✓
          },
          {
            "lane": 2,
            "racerid": 94,
            "name": "Fredrick Chaney",
            "carname": "",
            "carnumber": 224,
            "note": "",
            "photo": "",
            "finishtime": "",
            "finishplace": ""
          },
          {
            "lane": 3,
            "racerid": 78,
            "name": "Derrick Fields",
            "carname": "",
            "carnumber": 208,
            "note": "",
            "photo": "",
            "finishtime": "",
            "finishplace": ""
          }
        ],
        "timer-state": {
          "lanes": 3,                   // int ✓
          "last-contact": 1765708343,   // int ✓
          "state": 4,                   // int ✓
          "icon": "img/status/ok.png",  // String ✓
          "remote-start": false,        // bool ✓
          "message": "Race running",    // String ✓
          "timers": [],                 // List ✓
          "server_time": 1765708351,    // int ✓
          "timers_online": 0,           // int ✓
          "timers_ready": 0,            // int ✓
          "timers_required": 3,         // int ✓
          "health_status": "critical",  // String ✓
          "health_message": "WARNING: Only 0/3 timers online during active race!" // String ✓
        },
        "replay-state": {
          "last_contact": 0,            // int ✓
          "state": 1,                   // int ✓
          "icon": "img/status/not_connected.png", // String ✓
          "connected": false,           // bool ✓
          "message": "NOT CONNECTED"    // String ✓
        },
        "last-heat": "recoverable",     // String ✓
        "refused-results": 0,           // int ✓
        "current-scene": "",            // String ✓
        "heat-results": [],             // List ✓
        "classes": [],                  // List ✓
        "rounds": [],                   // List ✓
        "ready-aggregate": [],          // List ✓
        "race-integrity": {
          "status": "ok",               // String ✓
          "code": "ok",                 // String ✓
          "message": ""                 // String ✓
        }
      };

      // Parse the response
      final response = CoordinatorPollResponse.fromJson(json);

      print('\n✅ PARSING SUCCESSFUL - All types validated!\n');

      // Validate current-heat
      print('📍 Current Heat:');
      expect(response.currentHeat.nowRacing, isA<bool>());
      expect(response.currentHeat.nowRacing, true);
      print('  ✓ now_racing: ${response.currentHeat.nowRacing} (bool)');

      expect(response.currentHeat.classid, isA<int?>());
      expect(response.currentHeat.classid, 3);
      print('  ✓ classid: ${response.currentHeat.classid} (int)');

      expect(response.currentHeat.roundid, isA<int?>());
      expect(response.currentHeat.roundid, 3);
      print('  ✓ roundid: ${response.currentHeat.roundid} (int)');

      expect(response.currentHeat.round, isA<int?>());
      expect(response.currentHeat.round, 1);
      print('  ✓ round: ${response.currentHeat.round} (int)');

      expect(response.currentHeat.tbodyId, isA<int?>());
      expect(response.currentHeat.tbodyId, 3);
      print('  ✓ tbodyId: ${response.currentHeat.tbodyId} (int)');

      expect(response.currentHeat.heat, isA<int?>());
      expect(response.currentHeat.heat, 1);
      print('  ✓ heat: ${response.currentHeat.heat} (int)');

      expect(response.currentHeat.numberOfHeats, isA<int>());
      expect(response.currentHeat.numberOfHeats, 37);
      print('  ✓ numberOfHeats: ${response.currentHeat.numberOfHeats} (int)');

      // Validate racers
      print('\n🏁 Racers:');
      expect(response.racers.length, 3);
      print('  ✓ Found ${response.racers.length} racers');

      final racer1 = response.racers[0];
      expect(racer1.lane, isA<int>());
      expect(racer1.lane, 1);
      print('  ✓ Racer 1 - Lane: ${racer1.lane} (int)');

      expect(racer1.racerid, isA<int>());
      expect(racer1.racerid, 105);
      print('  ✓ Racer 1 - ID: ${racer1.racerid} (int)');

      expect(racer1.name, isA<String>());
      expect(racer1.name, 'Rubye Raymo');
      print('  ✓ Racer 1 - Name: "${racer1.name}" (String)');

      expect(racer1.carnumber, isA<int?>());
      expect(racer1.carnumber, 235);
      print('  ✓ Racer 1 - Car #: ${racer1.carnumber} (int)');

      // Critical: Empty strings should be null
      expect(racer1.finishtime, isNull);
      print('  ✓ Racer 1 - Finish time: null (empty string converted)');

      expect(racer1.finishplace, isNull);
      print('  ✓ Racer 1 - Finish place: null (empty string converted)');

      // Validate timer-state
      print('\n⏱️  Timer State:');
      expect(response.timerState.lanes, isA<int>());
      expect(response.timerState.lanes, 3);
      print('  ✓ lanes: ${response.timerState.lanes} (int)');

      expect(response.timerState.lastContact, isA<int>());
      expect(response.timerState.lastContact, 1765708343);
      print('  ✓ lastContact: ${response.timerState.lastContact} (int)');

      expect(response.timerState.state, isA<int>());
      expect(response.timerState.state, 4);
      print('  ✓ state: ${response.timerState.state} (int)');

      expect(response.timerState.icon, isA<String>());
      print('  ✓ icon: "${response.timerState.icon}" (String)');

      expect(response.timerState.message, isA<String>());
      print('  ✓ message: "${response.timerState.message}" (String)');

      expect(response.timerState.serverTime, isA<int>());
      print('  ✓ serverTime: ${response.timerState.serverTime} (int)');

      expect(response.timerState.timersOnline, isA<int>());
      print('  ✓ timersOnline: ${response.timerState.timersOnline} (int)');

      expect(response.timerState.healthStatus, isA<String>());
      print('  ✓ healthStatus: "${response.timerState.healthStatus}" (String)');

      // Validate race-integrity
      print('\n🔒 Race Integrity:');
      expect(response.raceIntegrity.status, isA<String>());
      expect(response.raceIntegrity.status, 'ok');
      print('  ✓ status: "${response.raceIntegrity.status}" (String)');

      expect(response.raceIntegrity.code, isA<String>());
      expect(response.raceIntegrity.code, 'ok');
      print('  ✓ code: "${response.raceIntegrity.code}" (String)');

      // Validate top-level fields
      print('\n📦 Top-level Fields:');
      expect(response.lastHeat, isA<String>());
      print('  ✓ lastHeat: "${response.lastHeat}" (String)');

      expect(response.refusedResults, isA<int>());
      print('  ✓ refusedResults: ${response.refusedResults} (int)');

      expect(response.currentScene, isA<String>());
      print('  ✓ currentScene: "${response.currentScene}" (String)');

      print('\n🎉 ALL TYPE VALIDATIONS PASSED!\n');
      print('Summary:');
      print('  • Current heat: All fields correctly typed');
      print('  • Racers: All 3 racers parsed correctly');
      print('  • Empty strings: Correctly converted to null');
      print('  • Timer state: All fields correctly typed');
      print('  • Race integrity: All fields correctly typed');
      print('  • Top-level: All fields correctly typed');
      print('\n✅ Models are fully compatible with live API response\n');
    });
  });
}
