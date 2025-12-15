// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'heat_result_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$HeatResultModelImpl _$$HeatResultModelImplFromJson(
  Map<String, dynamic> json,
) => _$HeatResultModelImpl(
  lane: (json['lane'] as num).toInt(),
  time: (json['time'] as num).toDouble(),
  place: (json['place'] as num).toInt(),
  speed: (json['speed'] as num?)?.toDouble() ?? 0.0,
);

Map<String, dynamic> _$$HeatResultModelImplToJson(
  _$HeatResultModelImpl instance,
) => <String, dynamic>{
  'lane': instance.lane,
  'time': instance.time,
  'place': instance.place,
  'speed': instance.speed,
};
