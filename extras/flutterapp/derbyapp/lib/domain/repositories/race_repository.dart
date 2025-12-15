import 'package:dartz/dartz.dart';
import '../../core/errors/failures.dart';
import '../../data/models/race/coordinator_poll_response.dart';
import '../../data/models/race/ondeck_entry_model.dart';
import '../../data/models/race/heat_detail_model.dart';

/// Race repository interface
/// Defines contract for race data operations
abstract class RaceRepository {
  /// Poll coordinator endpoint for race status
  /// Returns real-time race information
  Future<Either<Failure, CoordinatorPollResponse>> pollCoordinator({
    int? roundId,
    int? heat,
  });

  /// Stream of coordinator poll responses (for continuous polling)
  Stream<Either<Failure, CoordinatorPollResponse>> watchRaceStatus({
    Duration pollInterval = const Duration(seconds: 1),
    int? roundId,
    int? heat,
  });

  /// Get ondeck chart with completed heats
  /// Returns list of heats with results for heat history view
  Future<Either<Failure, OnDeckResponse>> getOnDeckChart();

  /// Get specific heat details with racers and results
  /// Combines poll.coordinator data for a specific roundid+heat
  Future<Either<Failure, HeatDetailModel>> getHeatDetail({
    required int roundId,
    required int heat,
  });

  /// Stream of recent results (watches last completed heat)
  /// Polls for the most recent completed heat and its results
  Stream<Either<Failure, HeatDetailModel?>> watchRecentResults({
    Duration pollInterval = const Duration(seconds: 2),
  });
}
