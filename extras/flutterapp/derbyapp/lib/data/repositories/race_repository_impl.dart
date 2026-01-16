import 'package:dartz/dartz.dart';
import '../../core/errors/exceptions.dart';
import '../../core/errors/failures.dart';
import '../../core/utils/network_info.dart';
import '../../domain/repositories/race_repository.dart';
import '../datasources/remote/race_api_source.dart';
import '../models/race/coordinator_poll_response.dart';

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
}
