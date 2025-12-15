import 'package:freezed_annotation/freezed_annotation.dart';
import 'racer_model.dart';
import 'heat_result_model.dart';

part 'heat_detail_model.freezed.dart';
part 'heat_detail_model.g.dart';

/// Complete information about a specific heat including racers and results
/// Combines data from poll.coordinator endpoint
@freezed
class HeatDetailModel with _$HeatDetailModel {
  const HeatDetailModel._();

  const factory HeatDetailModel({
    required int roundId,
    required int heat,
    required String roundName,
    required String className,
    required List<RacerModel> racers,
    required List<HeatResultModel> results,
    required bool isComplete,
    DateTime? completedAt,
  }) = _HeatDetailModel;

  factory HeatDetailModel.fromJson(Map<String, dynamic> json) =>
      _$HeatDetailModelFromJson(json);

  /// Merges racer info with their results, sorted by finish place
  List<RacerWithResult> get racersWithResults {
    return racers.map((racer) {
      final result = results.firstWhere(
        (r) => r.lane == racer.lane,
        orElse: () => const HeatResultModel(lane: 0, time: 0, place: 0, speed: 0),
      );
      return RacerWithResult(racer: racer, result: result);
    }).toList()
      ..sort((a, b) => a.result.place.compareTo(b.result.place));
  }
}

/// Helper class to combine racer and result data
class RacerWithResult {
  final RacerModel racer;
  final HeatResultModel result;

  RacerWithResult({required this.racer, required this.result});
}
