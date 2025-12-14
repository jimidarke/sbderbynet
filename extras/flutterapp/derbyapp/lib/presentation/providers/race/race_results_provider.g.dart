// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'race_results_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$onDeckChartHash() => r'fc1af3cc7905a0cb2dc6abb6c991644952fa9bbc';

/// Provider for ondeck chart (heat history)
///
/// Copied from [onDeckChart].
@ProviderFor(onDeckChart)
final onDeckChartProvider = AutoDisposeFutureProvider<OnDeckResponse>.internal(
  onDeckChart,
  name: r'onDeckChartProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$onDeckChartHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef OnDeckChartRef = AutoDisposeFutureProviderRef<OnDeckResponse>;
String _$heatDetailHash() => r'faeebc5c1f47756b91cc27a9cf6e7a2535a5bb97';

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

/// Provider for specific heat detail
///
/// Copied from [heatDetail].
@ProviderFor(heatDetail)
const heatDetailProvider = HeatDetailFamily();

/// Provider for specific heat detail
///
/// Copied from [heatDetail].
class HeatDetailFamily extends Family<AsyncValue<HeatDetailModel>> {
  /// Provider for specific heat detail
  ///
  /// Copied from [heatDetail].
  const HeatDetailFamily();

  /// Provider for specific heat detail
  ///
  /// Copied from [heatDetail].
  HeatDetailProvider call({required int roundId, required int heat}) {
    return HeatDetailProvider(roundId: roundId, heat: heat);
  }

  @override
  HeatDetailProvider getProviderOverride(
    covariant HeatDetailProvider provider,
  ) {
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
  String? get name => r'heatDetailProvider';
}

/// Provider for specific heat detail
///
/// Copied from [heatDetail].
class HeatDetailProvider extends AutoDisposeFutureProvider<HeatDetailModel> {
  /// Provider for specific heat detail
  ///
  /// Copied from [heatDetail].
  HeatDetailProvider({required int roundId, required int heat})
    : this._internal(
        (ref) => heatDetail(ref as HeatDetailRef, roundId: roundId, heat: heat),
        from: heatDetailProvider,
        name: r'heatDetailProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$heatDetailHash,
        dependencies: HeatDetailFamily._dependencies,
        allTransitiveDependencies: HeatDetailFamily._allTransitiveDependencies,
        roundId: roundId,
        heat: heat,
      );

  HeatDetailProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.roundId,
    required this.heat,
  }) : super.internal();

  final int roundId;
  final int heat;

  @override
  Override overrideWith(
    FutureOr<HeatDetailModel> Function(HeatDetailRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: HeatDetailProvider._internal(
        (ref) => create(ref as HeatDetailRef),
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
  AutoDisposeFutureProviderElement<HeatDetailModel> createElement() {
    return _HeatDetailProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is HeatDetailProvider &&
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
mixin HeatDetailRef on AutoDisposeFutureProviderRef<HeatDetailModel> {
  /// The parameter `roundId` of this provider.
  int get roundId;

  /// The parameter `heat` of this provider.
  int get heat;
}

class _HeatDetailProviderElement
    extends AutoDisposeFutureProviderElement<HeatDetailModel>
    with HeatDetailRef {
  _HeatDetailProviderElement(super.provider);

  @override
  int get roundId => (origin as HeatDetailProvider).roundId;
  @override
  int get heat => (origin as HeatDetailProvider).heat;
}

String _$recentResultsStreamHash() =>
    r'7c1e9aad1490ee8c852d20c25fcd19e8a4214448';

/// Stream provider for recent results (auto-updating)
///
/// Copied from [recentResultsStream].
@ProviderFor(recentResultsStream)
const recentResultsStreamProvider = RecentResultsStreamFamily();

/// Stream provider for recent results (auto-updating)
///
/// Copied from [recentResultsStream].
class RecentResultsStreamFamily extends Family<AsyncValue<HeatDetailModel?>> {
  /// Stream provider for recent results (auto-updating)
  ///
  /// Copied from [recentResultsStream].
  const RecentResultsStreamFamily();

  /// Stream provider for recent results (auto-updating)
  ///
  /// Copied from [recentResultsStream].
  RecentResultsStreamProvider call({
    Duration pollInterval = const Duration(seconds: 2),
  }) {
    return RecentResultsStreamProvider(pollInterval: pollInterval);
  }

  @override
  RecentResultsStreamProvider getProviderOverride(
    covariant RecentResultsStreamProvider provider,
  ) {
    return call(pollInterval: provider.pollInterval);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'recentResultsStreamProvider';
}

/// Stream provider for recent results (auto-updating)
///
/// Copied from [recentResultsStream].
class RecentResultsStreamProvider
    extends AutoDisposeStreamProvider<HeatDetailModel?> {
  /// Stream provider for recent results (auto-updating)
  ///
  /// Copied from [recentResultsStream].
  RecentResultsStreamProvider({
    Duration pollInterval = const Duration(seconds: 2),
  }) : this._internal(
         (ref) => recentResultsStream(
           ref as RecentResultsStreamRef,
           pollInterval: pollInterval,
         ),
         from: recentResultsStreamProvider,
         name: r'recentResultsStreamProvider',
         debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
             ? null
             : _$recentResultsStreamHash,
         dependencies: RecentResultsStreamFamily._dependencies,
         allTransitiveDependencies:
             RecentResultsStreamFamily._allTransitiveDependencies,
         pollInterval: pollInterval,
       );

  RecentResultsStreamProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.pollInterval,
  }) : super.internal();

  final Duration pollInterval;

  @override
  Override overrideWith(
    Stream<HeatDetailModel?> Function(RecentResultsStreamRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: RecentResultsStreamProvider._internal(
        (ref) => create(ref as RecentResultsStreamRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        pollInterval: pollInterval,
      ),
    );
  }

  @override
  AutoDisposeStreamProviderElement<HeatDetailModel?> createElement() {
    return _RecentResultsStreamProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is RecentResultsStreamProvider &&
        other.pollInterval == pollInterval;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, pollInterval.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin RecentResultsStreamRef on AutoDisposeStreamProviderRef<HeatDetailModel?> {
  /// The parameter `pollInterval` of this provider.
  Duration get pollInterval;
}

class _RecentResultsStreamProviderElement
    extends AutoDisposeStreamProviderElement<HeatDetailModel?>
    with RecentResultsStreamRef {
  _RecentResultsStreamProviderElement(super.provider);

  @override
  Duration get pollInterval =>
      (origin as RecentResultsStreamProvider).pollInterval;
}

String _$groupedHeatHistoryHash() =>
    r'0cc813a060a6a384a56098eebdecd9c1d8a9cf3e';

/// Grouped heat history provider
/// Groups ondeck entries by heat number for easier display
///
/// Copied from [groupedHeatHistory].
@ProviderFor(groupedHeatHistory)
final groupedHeatHistoryProvider =
    AutoDisposeFutureProvider<List<HeatGroup>>.internal(
      groupedHeatHistory,
      name: r'groupedHeatHistoryProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$groupedHeatHistoryHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GroupedHeatHistoryRef = AutoDisposeFutureProviderRef<List<HeatGroup>>;
String _$racingScheduleHash() => r'97f7910ec07ee7b91f9a076a51e4939b19012fa6';

/// Racing schedule provider - shows upcoming heats that haven't been run yet
///
/// Copied from [racingSchedule].
@ProviderFor(racingSchedule)
final racingScheduleProvider =
    AutoDisposeFutureProvider<List<HeatGroup>>.internal(
      racingSchedule,
      name: r'racingScheduleProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$racingScheduleHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef RacingScheduleRef = AutoDisposeFutureProviderRef<List<HeatGroup>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
