import 'package:freezed_annotation/freezed_annotation.dart';

part 'heat_result_model.freezed.dart';
part 'heat_result_model.g.dart';

/// Represents a single lane result from a completed heat
/// Based on DerbyNet API: heat-results array in poll response
@freezed
class HeatResultModel with _$HeatResultModel {
  const factory HeatResultModel({
    required int lane,
    required double time,
    required int place,
    @Default(0.0) double speed, // Speed in km/h (optional in API)
  }) = _HeatResultModel;

  factory HeatResultModel.fromJson(Map<String, dynamic> json) =>
      _$HeatResultModelFromJson(json);
}
