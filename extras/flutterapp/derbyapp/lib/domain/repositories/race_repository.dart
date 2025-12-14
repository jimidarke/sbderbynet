import 'package:dartz/dartz.dart';
import '../../core/errors/failures.dart';
import '../../data/models/race/coordinator_poll_response.dart';

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
}
