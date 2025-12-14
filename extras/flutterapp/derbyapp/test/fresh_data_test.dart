import 'package:flutter_test/flutter_test.dart';
import 'package:soapbox_derby_app/data/models/race/coordinator_poll_response.dart';

void main() {
  test('Should parse fresh data with empty strings for finishtime and finishplace', () {
    // Fresh data from coordinator poll with active race (no finish times yet)
    final json = {
      "current-heat": {
        "now_racing": true,
        "use_master_sched": false,
        "use_points": false,
        "classid": 3,
        "roundid": 5,
        "round": 1,
        "tbodyid": 5,
        "heat": 1,
        "number-of-heats": 1,
        "class": ""
      },
      "racers": [
        {
          "lane": 1,
          "racerid": 100,
          "name": "Darren Stuart",
          "carname": "",
          "carnumber": 230,
          "note": "",
          "photo": "",
          "finishtime": "",  // Empty string - should parse as null
          "finishplace": ""  // Empty string - should parse as null
        },
        {
          "lane": 2,
          "racerid": 87,
          "name": "Celia Ford",
          "carname": "",
          "carnumber": 217,
          "note": "",
          "photo": "",
          "finishtime": "",
          "finishplace": ""
        }
      ],
      "timer-state": {
        "lanes": 3,
        "last-contact": 1765708043,
        "state": 1,
        "icon": "img/status/not_connected.png",
        "remote-start": false,
        "message": "NOT CONNECTED",
        "timers": [],
        "server_time": 1765708088,
        "timers_online": 0,
        "timers_ready": 0,
        "timers_required": 3,
        "health_status": "critical",
        "health_message": "WARNING: Only 0/3 timers online during active race!"
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

    // Verify parsing succeeded
    expect(response.currentHeat.nowRacing, true);
    expect(response.racers.length, 2);

    // Verify first racer
    final racer1 = response.racers[0];
    expect(racer1.name, 'Darren Stuart');
    expect(racer1.carnumber, 230);
    expect(racer1.finishtime, isNull); // Empty string should be null
    expect(racer1.finishplace, isNull); // Empty string should be null

    print('✅ Test PASSED - Empty strings correctly parsed as null');
    print('Racer: ${racer1.name}, Car #${racer1.carnumber}');
    print('Finish time: ${racer1.finishtime} (null as expected)');
    print('Finish place: ${racer1.finishplace} (null as expected)');
  });
}
