import 'package:freezed_annotation/freezed_annotation.dart';
import 'current_heat_model.dart';
import 'racer_model.dart';
import 'timer_state_model.dart';
import 'race_integrity_model.dart';
import 'round_model.dart';

part 'coordinator_poll_response.freezed.dart';
part 'coordinator_poll_response.g.dart';

@freezed
class CoordinatorPollResponse with _$CoordinatorPollResponse {
  const factory CoordinatorPollResponse({
    @JsonKey(name: 'current-heat') required CurrentHeatModel currentHeat,
    @Default([]) List<RacerModel> racers,
    @JsonKey(name: 'timer-state') required TimerStateModel timerState,
    @JsonKey(name: 'race-integrity') required RaceIntegrityModel raceIntegrity,
    @Default([]) List<RoundModel> rounds,
    @JsonKey(name: 'heat-results') @Default([]) List<Map<String, dynamic>> heatResults,
    @JsonKey(name: 'last-heat') @Default('none') String lastHeat,
    @JsonKey(name: 'refused-results') @Default(0) int refusedResults,
    @JsonKey(name: 'current-scene') @Default(0) int currentScene,
    // Note: classes, ready-aggregate, replay-state can be added later if needed
  }) = _CoordinatorPollResponse;

  factory CoordinatorPollResponse.fromJson(Map<String, dynamic> json) =>
      _$CoordinatorPollResponseFromJson(json);
}
