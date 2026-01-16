import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../domain/repositories/race_repository.dart';
import '../../../data/repositories/race_repository_impl.dart';
import '../../../data/datasources/remote/race_api_source.dart';
import '../../../data/models/race/coordinator_poll_response.dart';
import '../../../core/utils/network_info.dart';
import '../../../core/constants/app_constants.dart';
import '../auth/auth_provider.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

part 'race_poll_provider.g.dart';

/// Provider for NetworkInfo
@riverpod
NetworkInfo networkInfo(NetworkInfoRef ref) {
  return NetworkInfo(Connectivity());
}

/// Provider for RaceApiSource
@riverpod
RaceApiSource raceApiSource(RaceApiSourceRef ref) {
  final dioClient = ref.watch(dioClientProvider);
  return RaceApiSource(dioClient);
}

/// Provider for RaceRepository
@riverpod
RaceRepository raceRepository(RaceRepositoryRef ref) {
  final raceApiSource = ref.watch(raceApiSourceProvider);
  final networkInfo = ref.watch(networkInfoProvider);

  return RaceRepositoryImpl(
    raceApiSource: raceApiSource,
    networkInfo: networkInfo,
  );
}

/// Stream provider for continuous race status polling
/// Polls every 1 second by default
@riverpod
Stream<CoordinatorPollResponse> racePollStream(
  RacePollStreamRef ref, {
  int? roundId,
  int? heat,
  Duration pollInterval = AppConstants.coordinatorPollInterval,
}) async* {
  final repository = ref.watch(raceRepositoryProvider);

  await for (final result in repository.watchRaceStatus(
    pollInterval: pollInterval,
    roundId: roundId,
    heat: heat,
  )) {
    yield* result.fold(
      (failure) async* {
        throw Exception(failure.message);
      },
      (response) async* {
        yield response;
      },
    );
  }
}

/// Provider for single coordinator poll (one-time fetch)
@riverpod
Future<CoordinatorPollResponse> racePoll(
  RacePollRef ref, {
  int? roundId,
  int? heat,
}) async {
  final repository = ref.watch(raceRepositoryProvider);
  final result = await repository.pollCoordinator(
    roundId: roundId,
    heat: heat,
  );

  return result.fold(
    (failure) => throw Exception(failure.message),
    (response) => response,
  );
}

/// State notifier for controlling race polling
@riverpod
class RacePollController extends _$RacePollController {
  @override
  RacePollState build() {
    return const RacePollState(
      isPolling: false,
      roundId: null,
      heat: null,
    );
  }

  /// Start polling with optional round/heat filters
  void startPolling({int? roundId, int? heat}) {
    state = RacePollState(
      isPolling: true,
      roundId: roundId,
      heat: heat,
    );
  }

  /// Stop polling
  void stopPolling() {
    state = const RacePollState(
      isPolling: false,
      roundId: null,
      heat: null,
    );
  }

  /// Update polling filters
  void updateFilters({int? roundId, int? heat}) {
    state = state.copyWith(
      roundId: roundId,
      heat: heat,
    );
  }
}

/// State class for race poll controller
class RacePollState {
  final bool isPolling;
  final int? roundId;
  final int? heat;

  const RacePollState({
    required this.isPolling,
    this.roundId,
    this.heat,
  });

  RacePollState copyWith({
    bool? isPolling,
    int? roundId,
    int? heat,
  }) {
    return RacePollState(
      isPolling: isPolling ?? this.isPolling,
      roundId: roundId ?? this.roundId,
      heat: heat ?? this.heat,
    );
  }
}
