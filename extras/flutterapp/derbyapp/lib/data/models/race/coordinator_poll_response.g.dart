// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'coordinator_poll_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CoordinatorPollResponseImpl _$$CoordinatorPollResponseImplFromJson(
  Map<String, dynamic> json,
) => _$CoordinatorPollResponseImpl(
  currentHeat: CurrentHeatModel.fromJson(
    json['current-heat'] as Map<String, dynamic>,
  ),
  racers:
      (json['racers'] as List<dynamic>?)
          ?.map((e) => RacerModel.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  timerState: TimerStateModel.fromJson(
    json['timer-state'] as Map<String, dynamic>,
  ),
  raceIntegrity: RaceIntegrityModel.fromJson(
    json['race-integrity'] as Map<String, dynamic>,
  ),
  rounds:
      (json['rounds'] as List<dynamic>?)
          ?.map((e) => RoundModel.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  heatResults:
      (json['heat-results'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList() ??
      const [],
  lastHeat: json['last-heat'] as String? ?? 'none',
  refusedResults: (json['refused-results'] as num?)?.toInt() ?? 0,
  currentScene: (json['current-scene'] as num?)?.toInt() ?? 0,
);

Map<String, dynamic> _$$CoordinatorPollResponseImplToJson(
  _$CoordinatorPollResponseImpl instance,
) => <String, dynamic>{
  'current-heat': instance.currentHeat,
  'racers': instance.racers,
  'timer-state': instance.timerState,
  'race-integrity': instance.raceIntegrity,
  'rounds': instance.rounds,
  'heat-results': instance.heatResults,
  'last-heat': instance.lastHeat,
  'refused-results': instance.refusedResults,
  'current-scene': instance.currentScene,
};
