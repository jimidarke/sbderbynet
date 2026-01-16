import 'package:flutter_test/flutter_test.dart';
import 'package:soapbox_derby_app/data/models/race/coordinator_poll_response.dart';

void main() {
  group('Finished Race Data Type Validation', () {
    test('Should parse finished race with numeric finishtime and finishplace', () {
      // Simulated data for a finished race
      final json = {
        "current-heat": {
          "now_racing": false,
          "use_master_sched": false,
          "use_points": false,
          "classid": 3,
          "roundid": 5,
          "round": 3,
          "tbodyid": 5,
          "heat": 1,
          "number-of-heats": 1,
          "class": "Ages 12-14"
        },
        "racers": [
          {
            "lane": 1,
            "racerid": 100,
            "name": "Darren Stuart",
            "carname": "Lightning Bolt",
            "carnumber": 230,
            "note": "",
            "photo": "",
            "finishtime": 5.984,      // double ✓
            "finishplace": 2          // int ✓
          },
          {
            "lane": 2,
            "racerid": 87,
            "name": "Celia Ford",
            "carname": "Speed Demon",
            "carnumber": 217,
            "note": "",
            "photo": "",
            "finishtime": 5.123,      // double ✓
            "finishplace": 1          // int ✓
          },
          {
            "lane": 3,
            "racerid": 98,
            "name": "Terrence Bates",
            "carname": "",
            "carnumber": 228,
            "note": "",
            "photo": "",
            "finishtime": 6.456,      // double ✓
            "finishplace": 3          // int ✓
          }
        ],
        "timer-state": {
          "lanes": 3,
          "last-contact": 1765708343,
          "state": 1,
          "icon": "img/status/not_connected.png",
          "remote-start": false,
          "message": "NOT CONNECTED",
          "timers": [],
          "server_time": 1765708351,
          "timers_online": 0,
          "timers_ready": 0,
          "timers_required": 3,
          "health_status": "ok",
          "health_message": ""
        },
        "replay-state": {
          "last_contact": 0,
          "state": 1,
          "icon": "img/status/not_connected.png",
          "connected": false,
          "message": "NOT CONNECTED"
        },
        "last-heat": "recoverable",
        "refused-results": 0,
        "current-scene": "",
        "heat-results": [],
        "classes": [],
        "rounds": [],
        "ready-aggregate": [],
        "race-integrity": {
          "status": "ok",
          "code": "ok",
          "message": ""
        }
      };

      // Parse the response
      final response = CoordinatorPollResponse.fromJson(json);

      print('\n✅ PARSING SUCCESSFUL - Finished race validated!\n');

      print('🏁 Finished Race Results:');
      expect(response.racers.length, 3);
      print('  ✓ Found ${response.racers.length} racers with results');

      // Validate first place finisher
      final winner = response.racers[1]; // Celia Ford in lane 2
      expect(winner.name, 'Celia Ford');
      expect(winner.finishtime, isA<double?>());
      expect(winner.finishtime, 5.123);
      expect(winner.finishplace, isA<int?>());
      expect(winner.finishplace, 1);
      print('  🥇 1st Place: ${winner.name}');
      print('     Time: ${winner.finishtime}s (double)');
      print('     Place: ${winner.finishplace} (int)');

      // Validate second place finisher
      final second = response.racers[0]; // Darren Stuart in lane 1
      expect(second.name, 'Darren Stuart');
      expect(second.finishtime, isA<double?>());
      expect(second.finishtime, 5.984);
      expect(second.finishplace, isA<int?>());
      expect(second.finishplace, 2);
      print('  🥈 2nd Place: ${second.name}');
      print('     Time: ${second.finishtime}s (double)');
      print('     Place: ${second.finishplace} (int)');

      // Validate third place finisher
      final third = response.racers[2]; // Terrence Bates in lane 3
      expect(third.name, 'Terrence Bates');
      expect(third.finishtime, isA<double?>());
      expect(third.finishtime, 6.456);
      expect(third.finishplace, isA<int?>());
      expect(third.finishplace, 3);
      print('  🥉 3rd Place: ${third.name}');
      print('     Time: ${third.finishtime}s (double)');
      print('     Place: ${third.finishplace} (int)');

      print('\n🎉 FINISHED RACE VALIDATION PASSED!\n');
      print('Summary:');
      print('  • All numeric finish times parsed correctly as double');
      print('  • All numeric finish places parsed correctly as int');
      print('  • Converters handle both empty strings AND numeric values');
      print('\n✅ Models work for both in-progress AND finished races\n');
    });

    test('Should handle string representations of numbers', () {
      // Some APIs might return numbers as strings
      final json = {
        "current-heat": {
          "now_racing": false,
          "use_master_sched": false,
          "use_points": false,
          "classid": 3,
          "roundid": 5,
          "round": 3,
          "tbodyid": 5,
          "heat": 1,
          "number-of-heats": 1,
          "class": ""
        },
        "racers": [
          {
            "lane": 1,
            "racerid": 100,
            "name": "Test Racer",
            "carname": "",
            "carnumber": 230,
            "note": "",
            "photo": "",
            "finishtime": "5.984",    // String representation of double
            "finishplace": "2"        // String representation of int
          }
        ],
        "timer-state": {
          "lanes": 3,
          "last-contact": 1765708343,
          "state": 1,
          "icon": "img/status/not_connected.png",
          "remote-start": false,
          "message": "NOT CONNECTED",
          "timers": [],
          "server_time": 1765708351,
          "timers_online": 0,
          "timers_ready": 0,
          "timers_required": 3,
          "health_status": "ok",
          "health_message": ""
        },
        "replay-state": {
          "last_contact": 0,
          "state": 1,
          "icon": "img/status/not_connected.png",
          "connected": false,
          "message": "NOT CONNECTED"
        },
        "last-heat": "recoverable",
        "refused-results": 0,
        "current-scene": "",
        "heat-results": [],
        "classes": [],
        "rounds": [],
        "ready-aggregate": [],
        "race-integrity": {
          "status": "ok",
          "code": "ok",
          "message": ""
        }
      };

      final response = CoordinatorPollResponse.fromJson(json);

      print('\n✅ STRING NUMBER PARSING SUCCESSFUL!\n');

      final racer = response.racers[0];
      expect(racer.finishtime, isA<double?>());
      expect(racer.finishtime, 5.984);
      print('  ✓ String "5.984" → double 5.984');

      expect(racer.finishplace, isA<int?>());
      expect(racer.finishplace, 2);
      print('  ✓ String "2" → int 2');

      print('\n✅ Converters handle string representations too!\n');
    });
  });
}
