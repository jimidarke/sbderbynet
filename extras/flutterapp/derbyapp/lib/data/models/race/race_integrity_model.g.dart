// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'race_integrity_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RaceIntegrityModelImpl _$$RaceIntegrityModelImplFromJson(
  Map<String, dynamic> json,
) => _$RaceIntegrityModelImpl(
  status: json['status'] as String? ?? 'ok',
  code: json['code'] as String? ?? 'ok',
  message: json['message'] as String? ?? '',
);

Map<String, dynamic> _$$RaceIntegrityModelImplToJson(
  _$RaceIntegrityModelImpl instance,
) => <String, dynamic>{
  'status': instance.status,
  'code': instance.code,
  'message': instance.message,
};
