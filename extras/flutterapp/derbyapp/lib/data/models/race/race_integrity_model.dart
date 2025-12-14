import 'package:freezed_annotation/freezed_annotation.dart';

part 'race_integrity_model.freezed.dart';
part 'race_integrity_model.g.dart';

@freezed
class RaceIntegrityModel with _$RaceIntegrityModel {
  const factory RaceIntegrityModel({
    @Default('ok') String status,
    @Default('ok') String code,
    @Default('') String message,
  }) = _RaceIntegrityModel;

  factory RaceIntegrityModel.fromJson(Map<String, dynamic> json) =>
      _$RaceIntegrityModelFromJson(json);
}
