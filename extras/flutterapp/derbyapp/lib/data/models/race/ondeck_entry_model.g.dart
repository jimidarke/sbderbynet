// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ondeck_entry_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$OnDeckEntryModelImpl _$$OnDeckEntryModelImplFromJson(
  Map<String, dynamic> json,
) => _$OnDeckEntryModelImpl(
  resultid: (json['resultid'] as num).toInt(),
  roundid: (json['roundid'] as num).toInt(),
  heat: (json['heat'] as num).toInt(),
  lane: (json['lane'] as num).toInt(),
  racerid: (json['racerid'] as num).toInt(),
  name: json['name'] as String? ?? '',
  carnumber: (json['carnumber'] as num?)?.toInt() ?? 0,
  result: const OnDeckResultConverter().fromJson(json['result'] as String?),
  carPhoto: json['carphoto'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$$OnDeckEntryModelImplToJson(
  _$OnDeckEntryModelImpl instance,
) => <String, dynamic>{
  'resultid': instance.resultid,
  'roundid': instance.roundid,
  'heat': instance.heat,
  'lane': instance.lane,
  'racerid': instance.racerid,
  'name': instance.name,
  'carnumber': instance.carnumber,
  'result': const OnDeckResultConverter().toJson(instance.result),
  'carphoto': instance.carPhoto,
};
