import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../data/models/race/heat_detail_model.dart';
import '../../../data/models/race/ondeck_entry_model.dart';
import 'race_poll_provider.dart';

part 'race_results_provider.g.dart';

/// Provider for ondeck chart (heat history)
@riverpod
Future<OnDeckResponse> onDeckChart(OnDeckChartRef ref) async {
  final repository = ref.watch(raceRepositoryProvider);
  final result = await repository.getOnDeckChart();

  return result.fold(
    (failure) => throw Exception(failure.message),
    (response) => response,
  );
}

/// Provider for specific heat detail
@riverpod
Future<HeatDetailModel> heatDetail(
  HeatDetailRef ref, {
  required int roundId,
  required int heat,
}) async {
  final repository = ref.watch(raceRepositoryProvider);
  final result = await repository.getHeatDetail(
    roundId: roundId,
    heat: heat,
  );

  return result.fold(
    (failure) => throw Exception(failure.message),
    (response) => response,
  );
}

/// Stream provider for recent results (auto-updating)
@riverpod
Stream<HeatDetailModel?> recentResultsStream(
  RecentResultsStreamRef ref, {
  Duration pollInterval = const Duration(seconds: 2),
}) async* {
  final repository = ref.watch(raceRepositoryProvider);

  await for (final result in repository.watchRecentResults(
    pollInterval: pollInterval,
  )) {
    yield* result.fold(
      (failure) async* {
        throw Exception(failure.message);
      },
      (heatDetail) async* {
        yield heatDetail;
      },
    );
  }
}

/// Grouped heat history provider
/// Groups ondeck entries by heat number for easier display
@riverpod
Future<List<HeatGroup>> groupedHeatHistory(
  GroupedHeatHistoryRef ref,
) async {
  final onDeck = await ref.watch(onDeckChartProvider.future);

  // Fetch coordinator poll to get round names
  final repository = ref.watch(raceRepositoryProvider);
  final coordinatorResult = await repository.pollCoordinator();

  // Build a map of roundId -> roundName
  final Map<int, String> roundNames = {};
  coordinatorResult.fold(
    (failure) {}, // Ignore failures, just won't have round names
    (response) {
      for (final round in response.rounds) {
        roundNames[round.roundid] = round.roundname;
      }
    },
  );

  // Group entries by roundid + heat
  final Map<String, List<OnDeckEntryModel>> grouped = {};

  for (final entry in onDeck.chart) {
    final key = '${entry.roundid}-${entry.heat}';
    grouped.putIfAbsent(key, () => []).add(entry);
  }

  // Convert to HeatGroup objects
  final groups = grouped.entries.map((entry) {
    final parts = entry.key.split('-');
    final roundId = int.parse(parts[0]);
    final heat = int.parse(parts[1]);

    // Check if heat is complete (all entries have results)
    final isComplete = entry.value.every((e) => e.result != null);

    return HeatGroup(
      roundId: roundId,
      heat: heat,
      entries: entry.value,
      isComplete: isComplete,
      roundName: roundNames[roundId] ?? 'Round $roundId',
    );
  }).toList()
    // Filter to only show completed heats in history
    ..removeWhere((group) => !group.isComplete)
    ..sort((a, b) {
      // Sort by roundId first, then heat (descending for recent first)
      final roundCompare = b.roundId.compareTo(a.roundId);
      return roundCompare != 0 ? roundCompare : b.heat.compareTo(a.heat);
    });

  return groups;
}

/// Racing schedule provider - shows upcoming heats that haven't been run yet
@riverpod
Future<List<HeatGroup>> racingSchedule(
  RacingScheduleRef ref,
) async {
  final onDeck = await ref.watch(onDeckChartProvider.future);

  // Fetch coordinator poll to get round names and current heat info
  final repository = ref.watch(raceRepositoryProvider);
  final coordinatorResult = await repository.pollCoordinator();

  // Build a map of roundId -> roundName
  final Map<int, String> roundNames = {};
  coordinatorResult.fold(
    (failure) {},
    (response) {
      for (final round in response.rounds) {
        roundNames[round.roundid] = round.roundname;
      }
    },
  );

  // Group entries by roundid + heat
  final Map<String, List<OnDeckEntryModel>> grouped = {};

  for (final entry in onDeck.chart) {
    final key = '${entry.roundid}-${entry.heat}';
    grouped.putIfAbsent(key, () => []).add(entry);
  }

  // Convert to HeatGroup objects
  final groups = grouped.entries.map((entry) {
    final parts = entry.key.split('-');
    final roundId = int.parse(parts[0]);
    final heat = int.parse(parts[1]);

    // Check if heat is complete (all entries have results)
    final isComplete = entry.value.every((e) => e.result != null);

    return HeatGroup(
      roundId: roundId,
      heat: heat,
      entries: entry.value,
      isComplete: isComplete,
      roundName: roundNames[roundId] ?? 'Round $roundId',
    );
  }).toList()
    // Filter to only show upcoming heats (not yet run)
    ..removeWhere((group) => group.isComplete)
    ..sort((a, b) {
      // Sort by roundId first, then heat (ascending for upcoming)
      final roundCompare = a.roundId.compareTo(b.roundId);
      return roundCompare != 0 ? roundCompare : a.heat.compareTo(b.heat);
    });

  return groups;
}

/// Helper class for grouped heat data
class HeatGroup {
  final int roundId;
  final int heat;
  final List<OnDeckEntryModel> entries;
  final bool isComplete;
  final String roundName;

  HeatGroup({
    required this.roundId,
    required this.heat,
    required this.entries,
    required this.isComplete,
    this.roundName = '',
  });

  /// Get round name from first entry (they all share same round)
  String get displayText => 'Heat $heat';

  /// Get winner (entry with fastest time)
  OnDeckEntryModel? get winner {
    if (!isComplete) return null;

    final withResults = entries.where((e) => e.result != null).toList();
    if (withResults.isEmpty) return null;

    withResults.sort((a, b) => a.result!.compareTo(b.result!));
    return withResults.first;
  }

  /// Get entries sorted by finish time (fastest first)
  List<OnDeckEntryModel> get sortedEntries {
    final withResults = entries.where((e) => e.result != null).toList();
    withResults.sort((a, b) => a.result!.compareTo(b.result!));

    // Add entries without results at the end
    final withoutResults = entries.where((e) => e.result == null).toList();
    return [...withResults, ...withoutResults];
  }

  /// Get finish place for an entry (1-based)
  int getPlaceForEntry(OnDeckEntryModel entry) {
    final sorted = sortedEntries;
    return sorted.indexOf(entry) + 1;
  }
}
