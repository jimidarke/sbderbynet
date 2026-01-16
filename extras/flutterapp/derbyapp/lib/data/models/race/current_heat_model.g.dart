// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'current_heat_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CurrentHeatModelImpl _$$CurrentHeatModelImplFromJson(
  Map<String, dynamic> json,
) => _$CurrentHeatModelImpl(
  nowRacing: json['now_racing'] as bool,
  useMasterSched: json['use_master_sched'] as bool? ?? false,
  usePoints: json['use_points'] as bool? ?? false,
  classid: (json['classid'] as num?)?.toInt(),
  roundid: (json['roundid'] as num?)?.toInt(),
  round: (json['round'] as num?)?.toInt(),
  tbodyId: (json['tbodyid'] as num?)?.toInt(),
  heat: (json['heat'] as num?)?.toInt(),
  numberOfHeats: (json['number-of-heats'] as num?)?.toInt() ?? 0,
  className: json['class'] as String?,
  masterheat: (json['masterheat'] as num?)?.toInt(),
  maxMasterheat: (json['max_masterheat'] as num?)?.toInt(),
);

Map<String, dynamic> _$$CurrentHeatModelImplToJson(
  _$CurrentHeatModelImpl instance,
) => <String, dynamic>{
  'now_racing': instance.nowRacing,
  'use_master_sched': instance.useMasterSched,
  'use_points': instance.usePoints,
  'classid': instance.classid,
  'roundid': instance.roundid,
  'round': instance.round,
  'tbodyid': instance.tbodyId,
  'heat': instance.heat,
  'number-of-heats': instance.numberOfHeats,
  'class': instance.className,
  'masterheat': instance.masterheat,
  'max_masterheat': instance.maxMasterheat,
};
