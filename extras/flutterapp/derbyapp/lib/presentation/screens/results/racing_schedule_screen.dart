import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/race/ondeck_entry_model.dart';
import '../../providers/race/race_results_provider.dart';

/// Screen showing upcoming heats that haven't been run yet
class RacingScheduleScreen extends ConsumerWidget {
  const RacingScheduleScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheduleAsync = ref.watch(racingScheduleProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Racing Schedule'),
      ),
      body: scheduleAsync.when(
        data: (upcomingHeats) {
          if (upcomingHeats.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.check_circle_outline,
                    size: 80,
                    color: Colors.green[400],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'All Heats Complete!',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'No upcoming heats scheduled',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(racingScheduleProvider);
              await Future.delayed(const Duration(milliseconds: 500));
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: upcomingHeats.length,
              itemBuilder: (context, index) {
                final heat = upcomingHeats[index];
                return _ScheduleHeatCard(heat: heat);
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
                  'Failed to load schedule',
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

/// Individual upcoming heat card
class _ScheduleHeatCard extends StatelessWidget {
  final HeatGroup heat;

  const _ScheduleHeatCard({required this.heat});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Heat header
            Row(
              children: [
                Container(
                  width: 50,
                  height: 50,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${heat.heat}',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                      Text(
                        'HEAT',
                        style: TextStyle(
                          fontSize: 9,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        heat.roundName,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${heat.entries.length} racers',
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.schedule,
                  color: Colors.grey[400],
                  size: 28,
                ),
              ],
            ),
            const Divider(height: 24),

            // Racers list
            ...heat.entries.map((entry) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      // Lane badge
                      Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                          color: _getLaneColor(entry.lane),
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            '${entry.lane}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),

                      // Racer info
                      Expanded(
                        child: Text(
                          entry.name,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),

                      // Car number
                      Text(
                        '#${entry.carnumber}',
                        style: TextStyle(
                          color: Colors.grey[700],
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Color _getLaneColor(int lane) {
    final colors = [
      Colors.red[400]!,
      Colors.blue[400]!,
      Colors.green[400]!,
      Colors.amber[700]!,
      Colors.purple[400]!,
      Colors.orange[400]!,
    ];
    return colors[(lane - 1) % colors.length];
  }
}
