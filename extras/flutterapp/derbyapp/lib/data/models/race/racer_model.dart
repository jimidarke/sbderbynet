import 'package:freezed_annotation/freezed_annotation.dart';

part 'racer_model.freezed.dart';
part 'racer_model.g.dart';

/// Converter to handle empty string as null for double
class EmptyStringToDoubleConverter implements JsonConverter<double?, Object?> {
  const EmptyStringToDoubleConverter();

  @override
  double? fromJson(Object? json) {
    if (json == null || json == '') return null;
    if (json is num) return json.toDouble();
    if (json is String) {
      final parsed = double.tryParse(json);
      return parsed;
    }
    return null;
  }

  @override
  Object? toJson(double? object) => object;
}

/// Converter to handle empty string as null for int
class EmptyStringToIntConverter implements JsonConverter<int?, Object?> {
  const EmptyStringToIntConverter();

  @override
  int? fromJson(Object? json) {
    if (json == null || json == '') return null;
    if (json is num) return json.toInt();
    if (json is String) {
      final parsed = int.tryParse(json);
      return parsed;
    }
    return null;
  }

  @override
  Object? toJson(int? object) => object;
}

@freezed
class RacerModel with _$RacerModel {
  const factory RacerModel({
    required int lane,
    required int racerid,
    @Default('') String name,
    @Default('') String carname,
    int? carnumber,
    @Default('') String note,
    @Default('') String photo,
    @EmptyStringToDoubleConverter() double? finishtime,
    @EmptyStringToIntConverter() int? finishplace,
    String? subgroup,
  }) = _RacerModel;

  factory RacerModel.fromJson(Map<String, dynamic> json) =>
      _$RacerModelFromJson(json);
}
