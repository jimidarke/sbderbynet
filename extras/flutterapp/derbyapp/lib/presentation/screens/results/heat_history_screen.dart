import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../data/models/race/ondeck_entry_model.dart';
import '../../providers/race/race_results_provider.dart';
import '../../routes/app_router.dart';

/// Screen showing list of all completed heats
/// Tappable to view detail of each heat
class HeatHistoryScreen extends ConsumerWidget {
  const HeatHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupedHistory = ref.watch(groupedHeatHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Heat History'),
      ),
      body: groupedHistory.when(
        data: (heatGroups) {
          if (heatGroups.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.history_outlined,
                    size: 80,
                    color: Colors.grey[400],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No Heat History',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Completed heats will appear here',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(groupedHeatHistoryProvider);
              await Future.delayed(const Duration(milliseconds: 500));
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: heatGroups.length,
              itemBuilder: (context, index) {
                final group = heatGroups[index];
                return _HeatHistoryListItem(
                  heatGroup: group,
                  onTap: () => context.push(
                    AppRoutes.heatDetail(
                      roundId: group.roundId,
                      heat: group.heat,
                    ),
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 64, color: Colors.red),
                const SizedBox(height: 16),
                Text(
                  'Failed to load heat history',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  error.toString().replaceAll('Exception: ', ''),
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Individual heat list item widget with expandable results
class _HeatHistoryListItem extends StatelessWidget {
  final HeatGroup heatGroup;
  final VoidCallback onTap;

  const _HeatHistoryListItem({
    required this.heatGroup,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final winner = heatGroup.winner;
    final sortedEntries = heatGroup.sortedEntries;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          childrenPadding: const EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: 16,
          ),
          leading: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: heatGroup.isComplete
                  ? Theme.of(context).colorScheme.primaryContainer
                  : Colors.grey[200],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '${heatGroup.heat}',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: heatGroup.isComplete
                        ? Theme.of(context).colorScheme.primary
                        : Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Heat ${heatGroup.heat}',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                heatGroup.roundName,
                style: TextStyle(
                  color: Colors.grey[700],
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
              if (winner != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Winner: #${winner.carnumber} (${winner.result?.toStringAsFixed(3)}s)',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
              ],
              const SizedBox(height: 6),
              _buildPinnyChips(heatGroup.entries),
            ],
          ),
          children: [
            const Divider(height: 16),
            ...sortedEntries.map((entry) {
              // Only show place/medals if heat is complete
              final place = heatGroup.isComplete
                  ? heatGroup.getPlaceForEntry(entry)
                  : entry.lane;
              return _buildCompactResultRow(
                place: place,
                pinny: entry.carnumber,
                name: entry.name,
                time: entry.result,
                speed: null, // Speed not available in OnDeck data
                showMedals: heatGroup.isComplete,
              );
            }),
          ],
        ),
      ),
    );
  }

  /// Build pinny number chips for collapsed view
  Widget _buildPinnyChips(List<OnDeckEntryModel> entries) {
    final pinnies = entries
        .where((e) => e.carnumber > 0)
        .map((e) => e.carnumber)
        .toList();

    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: pinnies
          .map((pinny) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '#$pinny',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ))
          .toList(),
    );
  }

  /// Build compact result row for expanded view
  Widget _buildCompactResultRow({
    required int place,
    required int pinny,
    required String name,
    required double? time,
    double? speed,
    bool showMedals = true,
  }) {
    // Show medals for top 3 if heat is complete, otherwise show lane number
    final displayText = showMedals
        ? (place == 1 ? '🥇' : place == 2 ? '🥈' : place == 3 ? '🥉' : '$place')
        : 'L$place'; // Lane number for incomplete heats

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      child: Row(
        children: [
          SizedBox(
            width: 24,
            child: Text(
              displayText,
              style: TextStyle(
                fontSize: showMedals ? 16 : 13,
                fontWeight: showMedals ? FontWeight.normal : FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '#$pinny',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              name,
              style: const TextStyle(fontSize: 13),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (time != null) ...[
            Text(
              '${time.toStringAsFixed(1)}s',
              style: const TextStyle(
                fontFamily: 'RobotoMono',
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (speed != null && speed > 0) ...[
              const SizedBox(width: 8),
              Text(
                '${speed.toStringAsFixed(1)}km/h',
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
