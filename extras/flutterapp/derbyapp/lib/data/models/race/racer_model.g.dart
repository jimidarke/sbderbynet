// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'racer_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RacerModelImpl _$$RacerModelImplFromJson(
  Map<String, dynamic> json,
) => _$RacerModelImpl(
  lane: (json['lane'] as num).toInt(),
  racerid: (json['racerid'] as num).toInt(),
  name: json['name'] as String? ?? '',
  carname: json['carname'] as String? ?? '',
  carnumber: (json['carnumber'] as num?)?.toInt(),
  note: json['note'] as String? ?? '',
  photo: json['photo'] as String? ?? '',
  finishtime: const EmptyStringToDoubleConverter().fromJson(json['finishtime']),
  finishplace: const EmptyStringToIntConverter().fromJson(json['finishplace']),
  subgroup: json['subgroup'] as String?,
);

Map<String, dynamic> _$$RacerModelImplToJson(
  _$RacerModelImpl instance,
) => <String, dynamic>{
  'lane': instance.lane,
  'racerid': instance.racerid,
  'name': instance.name,
  'carname': instance.carname,
  'carnumber': instance.carnumber,
  'note': instance.note,
  'photo': instance.photo,
  'finishtime': const EmptyStringToDoubleConverter().toJson(
    instance.finishtime,
  ),
  'finishplace': const EmptyStringToIntConverter().toJson(instance.finishplace),
  'subgroup': instance.subgroup,
};
