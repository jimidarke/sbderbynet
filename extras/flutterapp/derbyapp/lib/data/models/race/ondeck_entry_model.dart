import 'package:freezed_annotation/freezed_annotation.dart';

part 'ondeck_entry_model.freezed.dart';
part 'ondeck_entry_model.g.dart';

/// Result parser for ondeck result field
/// Format: "z7.082" for completed heat (z-prefix means finished)
class OnDeckResultConverter implements JsonConverter<double?, String?> {
  const OnDeckResultConverter();

  @override
  double? fromJson(String? json) {
    if (json == null || json.isEmpty || json == '--') return null;
    // Remove 'z' prefix if present (indicates completed)
    final cleaned = json.startsWith('z') ? json.substring(1) : json;
    return double.tryParse(cleaned);
  }

  @override
  String? toJson(double? object) => object != null ? 'z$object' : null;
}

/// Represents a single entry in the ondeck chart
/// Used for heat history view
@freezed
class OnDeckEntryModel with _$OnDeckEntryModel {
  const factory OnDeckEntryModel({
    required int resultid,
    required int roundid,
    required int heat,
    required int lane,
    required int racerid,
    @Default('') String name,
    @Default(0) int carnumber,
    @OnDeckResultConverter() double? result, // z-prefix removed, null if not finished
    @JsonKey(name: 'carphoto') Map<String, dynamic>? carPhoto,
  }) = _OnDeckEntryModel;

  factory OnDeckEntryModel.fromJson(Map<String, dynamic> json) =>
      _$OnDeckEntryModelFromJson(json);
}

/// Response wrapper for ondeck endpoint
@freezed
class OnDeckResponse with _$OnDeckResponse {
  const factory OnDeckResponse({
    @Default([]) List<OnDeckEntryModel> chart,
  }) = _OnDeckResponse;

  factory OnDeckResponse.fromJson(Map<String, dynamic> json) {
    // Extract the 'ondeck' -> 'chart' array from the API response
    final chartData = json['ondeck'];
    if (chartData == null) {
      return const OnDeckResponse(chart: []);
    }

    final chart = chartData['chart'];
    if (chart == null || chart is! List) {
      return const OnDeckResponse(chart: []);
    }

    return OnDeckResponse(
      chart: chart
          .map((e) => OnDeckEntryModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
