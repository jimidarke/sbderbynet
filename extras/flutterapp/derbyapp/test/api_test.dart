import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:soapbox_derby_app/data/models/race/coordinator_poll_response.dart';

void main() {
  group('Coordinator Poll API Integration', () {
    final dio = Dio();
    const baseUrl = 'http://192.168.100.10/derbynet';

    test('Should successfully fetch and parse coordinator poll response', () async {
      try {
        final response = await dio.get('$baseUrl/action.php?query=poll.coordinator');

        expect(response.statusCode, 200);
        print('Response status: ${response.statusCode}');
        print('Response data type: ${response.data.runtimeType}');

        // Parse the response
        final pollResponse = CoordinatorPollResponse.fromJson(response.data);

        print('\n=== Parsed Coordinator Poll Response ===');
        print('Now Racing: ${pollResponse.currentHeat.nowRacing}');
        print('Round ID: ${pollResponse.currentHeat.roundid}');
        print('Heat: ${pollResponse.currentHeat.heat}');
        print('Class ID: ${pollResponse.currentHeat.classid}');
        print('Number of Heats: ${pollResponse.currentHeat.numberOfHeats}');

        print('\n=== Racers (${pollResponse.racers.length}) ===');
        for (final racer in pollResponse.racers) {
          print('Lane ${racer.lane}: ${racer.name} (#${racer.carnumber}) - ${racer.finishtime}s (Place: ${racer.finishplace})');
        }

        print('\n=== Timer State ===');
        print('Lanes: ${pollResponse.timerState.lanes}');
        print('State: ${pollResponse.timerState.state}');
        print('Message: ${pollResponse.timerState.message}');
        print('Health: ${pollResponse.timerState.healthStatus} - ${pollResponse.timerState.healthMessage}');
        print('Timers Online: ${pollResponse.timerState.timersOnline}/${pollResponse.timerState.timersRequired}');

        print('\n=== Race Integrity ===');
        print('Status: ${pollResponse.raceIntegrity.status}');
        print('Code: ${pollResponse.raceIntegrity.code}');

        // Assertions
        expect(pollResponse.currentHeat.nowRacing, isA<bool>());
        expect(pollResponse.timerState.lanes, greaterThan(0));
        expect(pollResponse.raceIntegrity.status, isNotEmpty);

        print('\n✅ All data parsed successfully!');
      } catch (e, stackTrace) {
        print('❌ Error: $e');
        print('Stack trace: $stackTrace');
        rethrow;
      }
    });
  });
}
