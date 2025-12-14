// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'race_poll_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$networkInfoHash() => r'b6405bcbfc4e6333f9373514cdbb2cefba93fc33';

/// Provider for NetworkInfo
///
/// Copied from [networkInfo].
@ProviderFor(networkInfo)
final networkInfoProvider = AutoDisposeProvider<NetworkInfo>.internal(
  networkInfo,
  name: r'networkInfoProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$networkInfoHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef NetworkInfoRef = AutoDisposeProviderRef<NetworkInfo>;
String _$raceApiSourceHash() => r'054befee6219046c2baec7d931dd2d7a343531e7';

/// Provider for RaceApiSource
///
/// Copied from [raceApiSource].
@ProviderFor(raceApiSource)
final raceApiSourceProvider = AutoDisposeProvider<RaceApiSource>.internal(
  raceApiSource,
  name: r'raceApiSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$raceApiSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef RaceApiSourceRef = AutoDisposeProviderRef<RaceApiSource>;
String _$raceRepositoryHash() => r'f795ca15d4ee1391a89dd58ad48570f47c31a811';

/// Provider for RaceRepository
///
/// Copied from [raceRepository].
@ProviderFor(raceRepository)
final raceRepositoryProvider = AutoDisposeProvider<RaceRepository>.internal(
  raceRepository,
  name: r'raceRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$raceRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef RaceRepositoryRef = AutoDisposeProviderRef<RaceRepository>;
String _$racePollStreamHash() => r'812dfcf6a357647f2438cbf7ff117a5d19b9576f';

/// Copied from Dart SDK
class _SystemHash {
  _SystemHash._();

  static int combine(int hash, int value) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + value);
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x0007ffff & hash) << 10));
    return hash ^ (hash >> 6);
  }

  static int finish(int hash) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x03ffffff & hash) << 3));
    // ignore: parameter_assignments
    hash = hash ^ (hash >> 11);
    return 0x1fffffff & (hash + ((0x00003fff & hash) << 15));
  }
}

/// Stream provider for continuous race status polling
/// Polls every 1 second by default
///
/// Copied from [racePollStream].
@ProviderFor(racePollStream)
const racePollStreamProvider = RacePollStreamFamily();

/// Stream provider for continuous race status polling
/// Polls every 1 second by default
///
/// Copied from [racePollStream].
class RacePollStreamFamily extends Family<AsyncValue<CoordinatorPollResponse>> {
  /// Stream provider for continuous race status polling
  /// Polls every 1 second by default
  ///
  /// Copied from [racePollStream].
  const RacePollStreamFamily();

  /// Stream provider for continuous race status polling
  /// Polls every 1 second by default
  ///
  /// Copied from [racePollStream].
  RacePollStreamProvider call({
    int? roundId,
    int? heat,
    Duration pollInterval = AppConstants.coordinatorPollInterval,
  }) {
    return RacePollStreamProvider(
      roundId: roundId,
      heat: heat,
      pollInterval: pollInterval,
    );
  }

  @override
  RacePollStreamProvider getProviderOverride(
    covariant RacePollStreamProvider provider,
  ) {
    return call(
      roundId: provider.roundId,
      heat: provider.heat,
      pollInterval: provider.pollInterval,
    );
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'racePollStreamProvider';
}

/// Stream provider for continuous race status polling
/// Polls every 1 second by default
///
/// Copied from [racePollStream].
class RacePollStreamProvider
    extends AutoDisposeStreamProvider<CoordinatorPollResponse> {
  /// Stream provider for continuous race status polling
  /// Polls every 1 second by default
  ///
  /// Copied from [racePollStream].
  RacePollStreamProvider({
    int? roundId,
    int? heat,
    Duration pollInterval = AppConstants.coordinatorPollInterval,
  }) : this._internal(
         (ref) => racePollStream(
           ref as RacePollStreamRef,
           roundId: roundId,
           heat: heat,
           pollInterval: pollInterval,
         ),
         from: racePollStreamProvider,
         name: r'racePollStreamProvider',
         debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
             ? null
             : _$racePollStreamHash,
         dependencies: RacePollStreamFamily._dependencies,
         allTransitiveDependencies:
             RacePollStreamFamily._allTransitiveDependencies,
         roundId: roundId,
         heat: heat,
         pollInterval: pollInterval,
       );

  RacePollStreamProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.roundId,
    required this.heat,
    required this.pollInterval,
  }) : super.internal();

  final int? roundId;
  final int? heat;
  final Duration pollInterval;

  @override
  Override overrideWith(
    Stream<CoordinatorPollResponse> Function(RacePollStreamRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: RacePollStreamProvider._internal(
        (ref) => create(ref as RacePollStreamRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        roundId: roundId,
        heat: heat,
        pollInterval: pollInterval,
      ),
    );
  }

  @override
  AutoDisposeStreamProviderElement<CoordinatorPollResponse> createElement() {
    return _RacePollStreamProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is RacePollStreamProvider &&
        other.roundId == roundId &&
        other.heat == heat &&
        other.pollInterval == pollInterval;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, roundId.hashCode);
    hash = _SystemHash.combine(hash, heat.hashCode);
    hash = _SystemHash.combine(hash, pollInterval.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin RacePollStreamRef
    on AutoDisposeStreamProviderRef<CoordinatorPollResponse> {
  /// The parameter `roundId` of this provider.
  int? get roundId;

  /// The parameter `heat` of this provider.
  int? get heat;

  /// The parameter `pollInterval` of this provider.
  Duration get pollInterval;
}

class _RacePollStreamProviderElement
    extends AutoDisposeStreamProviderElement<CoordinatorPollResponse>
    with RacePollStreamRef {
  _RacePollStreamProviderElement(super.provider);

  @override
  int? get roundId => (origin as RacePollStreamProvider).roundId;
  @override
  int? get heat => (origin as RacePollStreamProvider).heat;
  @override
  Duration get pollInterval => (origin as RacePollStreamProvider).pollInterval;
}

String _$racePollHash() => r'135ddf145e087d52a9ed1dcc6e6d5aabfe8fc248';

/// Provider for single coordinator poll (one-time fetch)
///
/// Copied from [racePoll].
@ProviderFor(racePoll)
const racePollProvider = RacePollFamily();

/// Provider for single coordinator poll (one-time fetch)
///
/// Copied from [racePoll].
class RacePollFamily extends Family<AsyncValue<CoordinatorPollResponse>> {
  /// Provider for single coordinator poll (one-time fetch)
  ///
  /// Copied from [racePoll].
  const RacePollFamily();

  /// Provider for single coordinator poll (one-time fetch)
  ///
  /// Copied from [racePoll].
  RacePollProvider call({int? roundId, int? heat}) {
    return RacePollProvider(roundId: roundId, heat: heat);
  }

  @override
  RacePollProvider getProviderOverride(covariant RacePollProvider provider) {
    return call(roundId: provider.roundId, heat: provider.heat);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'racePollProvider';
}

/// Provider for single coordinator poll (one-time fetch)
///
/// Copied from [racePoll].
class RacePollProvider
    extends AutoDisposeFutureProvider<CoordinatorPollResponse> {
  /// Provider for single coordinator poll (one-time fetch)
  ///
  /// Copied from [racePoll].
  RacePollProvider({int? roundId, int? heat})
    : this._internal(
        (ref) => racePoll(ref as RacePollRef, roundId: roundId, heat: heat),
        from: racePollProvider,
        name: r'racePollProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$racePollHash,
        dependencies: RacePollFamily._dependencies,
        allTransitiveDependencies: RacePollFamily._allTransitiveDependencies,
        roundId: roundId,
        heat: heat,
      );

  RacePollProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.roundId,
    required this.heat,
  }) : super.internal();

  final int? roundId;
  final int? heat;

  @override
  Override overrideWith(
    FutureOr<CoordinatorPollResponse> Function(RacePollRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: RacePollProvider._internal(
        (ref) => create(ref as RacePollRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        roundId: roundId,
        heat: heat,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<CoordinatorPollResponse> createElement() {
    return _RacePollProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is RacePollProvider &&
        other.roundId == roundId &&
        other.heat == heat;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, roundId.hashCode);
    hash = _SystemHash.combine(hash, heat.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin RacePollRef on AutoDisposeFutureProviderRef<CoordinatorPollResponse> {
  /// The parameter `roundId` of this provider.
  int? get roundId;

  /// The parameter `heat` of this provider.
  int? get heat;
}

class _RacePollProviderElement
    extends AutoDisposeFutureProviderElement<CoordinatorPollResponse>
    with RacePollRef {
  _RacePollProviderElement(super.provider);

  @override
  int? get roundId => (origin as RacePollProvider).roundId;
  @override
  int? get heat => (origin as RacePollProvider).heat;
}

String _$racePollControllerHash() =>
    r'2a9c0501c60d894d96767f61df037397316b95db';

/// State notifier for controlling race polling
///
/// Copied from [RacePollController].
@ProviderFor(RacePollController)
final racePollControllerProvider =
    AutoDisposeNotifierProvider<RacePollController, RacePollState>.internal(
      RacePollController.new,
      name: r'racePollControllerProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$racePollControllerHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$RacePollController = AutoDisposeNotifier<RacePollState>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
