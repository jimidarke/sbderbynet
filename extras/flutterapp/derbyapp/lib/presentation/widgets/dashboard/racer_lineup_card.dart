import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/race/racer_model.dart';
import '../../providers/race/race_poll_provider.dart';

class RacerLineupCard extends ConsumerWidget {
  const RacerLineupCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pollStream = ref.watch(racePollStreamProvider());

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(
                  Icons.groups,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Text(
                  'Racer Lineup',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const Divider(height: 24),

            // Racer List
            pollStream.when(
              data: (response) {
                final racers = response.racers;

                if (racers.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        children: [
                          Icon(
                            Icons.inbox,
                            size: 48,
                            color: Colors.grey[400],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'No racers in current heat',
                            style: TextStyle(
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                return Column(
                  children: racers.map((racer) => _buildRacerTile(
                    context,
                    racer,
                  )).toList(),
                );
              },
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(24.0),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (error, stack) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: Colors.red,
                        size: 48,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Failed to load racers',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRacerTile(BuildContext context, RacerModel racer) {
    final hasFinished = racer.finishtime != null && racer.finishplace != null;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: hasFinished ? Colors.green[50] : Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: hasFinished ? Colors.green : Colors.grey[300]!,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Lane Number Badge
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _getLaneColor(racer.lane),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '${racer.lane}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),

          // Racer Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Name
                Text(
                  racer.name.isNotEmpty ? racer.name : 'Unknown Racer',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 2),

                // Car Name & Number
                Row(
                  children: [
                    if (racer.carname.isNotEmpty) ...[
                      Text(
                        racer.carname,
                        style: TextStyle(
                          color: Colors.grey[700],
                          fontSize: 13,
                        ),
                      ),
                      if (racer.carnumber != null) const Text(' • '),
                    ],
                    if (racer.carnumber != null)
                      Text(
                        '#${racer.carnumber}',
                        style: TextStyle(
                          color: Colors.grey[700],
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),

          // Finish Info
          if (hasFinished)
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: _getPlaceColor(racer.finishplace!),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Text(
                    _getPlaceText(racer.finishplace!),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  Text(
                    '${racer.finishtime!.toStringAsFixed(3)}s',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Color _getLaneColor(int lane) {
    // Cycle through colors for different lanes
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
    ];
    return colors[(lane - 1) % colors.length];
  }

  Color _getPlaceColor(int place) {
    switch (place) {
      case 1:
        return Colors.amber[700]!; // Gold
      case 2:
        return Colors.grey[600]!; // Silver
      case 3:
        return Colors.brown[400]!; // Bronze
      default:
        return Colors.blue[600]!;
    }
  }

  String _getPlaceText(int place) {
    switch (place) {
      case 1:
        return '1st';
      case 2:
        return '2nd';
      case 3:
        return '3rd';
      default:
        return '${place}th';
    }
  }
}
