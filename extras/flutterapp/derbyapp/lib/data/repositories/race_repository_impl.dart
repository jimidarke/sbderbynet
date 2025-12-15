import 'package:dartz/dartz.dart';
import '../../core/errors/exceptions.dart';
import '../../core/errors/failures.dart';
import '../../core/utils/network_info.dart';
import '../../domain/repositories/race_repository.dart';
import '../datasources/remote/race_api_source.dart';
import '../models/race/coordinator_poll_response.dart';
import '../models/race/ondeck_entry_model.dart';
import '../models/race/heat_detail_model.dart';

/// Implementation of RaceRepository
class RaceRepositoryImpl implements RaceRepository {
  final RaceApiSource _raceApiSource;
  final NetworkInfo _networkInfo;

  RaceRepositoryImpl({
    required RaceApiSource raceApiSource,
    required NetworkInfo networkInfo,
  })  : _raceApiSource = raceApiSource,
        _networkInfo = networkInfo;

  @override
  Future<Either<Failure, CoordinatorPollResponse>> pollCoordinator({
    int? roundId,
    int? heat,
  }) async {
    // Check network connectivity
    if (!await _networkInfo.isConnected) {
      return const Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await _raceApiSource.pollCoordinator(
        roundId: roundId,
        heat: heat,
      );
      return Right(response);
    } on AuthException catch (e) {
      return Left(AuthFailure(e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    } on TimeoutException catch (e) {
      return Left(TimeoutFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Stream<Either<Failure, CoordinatorPollResponse>> watchRaceStatus({
    Duration pollInterval = const Duration(seconds: 1),
    int? roundId,
    int? heat,
  }) async* {
    while (true) {
      yield await pollCoordinator(roundId: roundId, heat: heat);
      await Future.delayed(pollInterval);
    }
  }

  @override
  Future<Either<Failure, OnDeckResponse>> getOnDeckChart() async {
    if (!await _networkInfo.isConnected) {
      return const Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await _raceApiSource.getOnDeckChart();
      return Right(response);
    } on NetworkException catch (e) {
      return Left(NetworkFailure(e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    } on TimeoutException catch (e) {
      return Left(TimeoutFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, HeatDetailModel>> getHeatDetail({
    required int roundId,
    required int heat,
  }) async {
    if (!await _networkInfo.isConnected) {
      return const Left(NetworkFailure('No internet connection'));
    }

    try {
      final response = await _raceApiSource.getHeatDetail(
        roundId: roundId,
        heat: heat,
      );
      return Right(response);
    } on NetworkException catch (e) {
      return Left(NetworkFailure(e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    } on TimeoutException catch (e) {
      return Left(TimeoutFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Stream<Either<Failure, HeatDetailModel?>> watchRecentResults({
    Duration pollInterval = const Duration(seconds: 2),
  }) async* {
    while (true) {
      // Poll coordinator to get last completed heat
      final pollResult = await pollCoordinator();

      yield* pollResult.fold(
        (failure) async* {
          yield Left(failure);
        },
        (pollResponse) async* {
          // Check if there's a last-heat value
          if (pollResponse.lastHeat != 'none' &&
              pollResponse.lastHeat.isNotEmpty &&
              pollResponse.lastHeat != 'available') {
            // Parse last heat (format: "roundid#heat")
            final parts = pollResponse.lastHeat.split('#');
            if (parts.length == 2) {
              final roundId = int.tryParse(parts[0]);
              final heat = int.tryParse(parts[1]);

              if (roundId != null && heat != null) {
                final detailResult = await getHeatDetail(
                  roundId: roundId,
                  heat: heat,
                );
                yield detailResult;
              } else {
                yield const Right(null);
              }
            } else {
              yield const Right(null);
            }
          } else {
            yield const Right(null); // No completed heats yet
          }
        },
      );

      await Future.delayed(pollInterval);
    }
  }
}
