// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'heat_detail_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$HeatDetailModelImpl _$$HeatDetailModelImplFromJson(
  Map<String, dynamic> json,
) => _$HeatDetailModelImpl(
  roundId: (json['roundId'] as num).toInt(),
  heat: (json['heat'] as num).toInt(),
  roundName: json['roundName'] as String,
  className: json['className'] as String,
  racers: (json['racers'] as List<dynamic>)
      .map((e) => RacerModel.fromJson(e as Map<String, dynamic>))
      .toList(),
  results: (json['results'] as List<dynamic>)
      .map((e) => HeatResultModel.fromJson(e as Map<String, dynamic>))
      .toList(),
  isComplete: json['isComplete'] as bool,
  completedAt: json['completedAt'] == null
      ? null
      : DateTime.parse(json['completedAt'] as String),
);

Map<String, dynamic> _$$HeatDetailModelImplToJson(
  _$HeatDetailModelImpl instance,
) => <String, dynamic>{
  'roundId': instance.roundId,
  'heat': instance.heat,
  'roundName': instance.roundName,
  'className': instance.className,
  'racers': instance.racers,
  'results': instance.results,
  'isComplete': instance.isComplete,
  'completedAt': instance.completedAt?.toIso8601String(),
};
