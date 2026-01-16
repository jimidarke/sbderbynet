// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'round_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RoundModelImpl _$$RoundModelImplFromJson(Map<String, dynamic> json) =>
    _$RoundModelImpl(
      roundid: (json['roundid'] as num).toInt(),
      classid: (json['classid'] as num).toInt(),
      class_: json['class_'] as String? ?? '',
      round: json['round'] as String? ?? '',
      name: json['name'] as String? ?? '',
      roundname: json['roundname'] as String? ?? '',
      aggregate: json['aggregate'] as bool? ?? false,
      rosterSize: (json['roster_size'] as num?)?.toInt() ?? 0,
      passed: (json['passed'] as num?)?.toInt() ?? 0,
      registered: (json['registered'] as num?)?.toInt() ?? 0,
      unscheduled: (json['unscheduled'] as num?)?.toInt() ?? 0,
      heatsScheduled: (json['heats_scheduled'] as num?)?.toInt() ?? 0,
      heatsRun: (json['heats_run'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$$RoundModelImplToJson(_$RoundModelImpl instance) =>
    <String, dynamic>{
      'roundid': instance.roundid,
      'classid': instance.classid,
      'class_': instance.class_,
      'round': instance.round,
      'name': instance.name,
      'roundname': instance.roundname,
      'aggregate': instance.aggregate,
      'roster_size': instance.rosterSize,
      'passed': instance.passed,
      'registered': instance.registered,
      'unscheduled': instance.unscheduled,
      'heats_scheduled': instance.heatsScheduled,
      'heats_run': instance.heatsRun,
    };
