import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/race/race_results_provider.dart';
import '../../widgets/results/heat_results_card.dart';
import '../../widgets/results/racer_result_tile.dart';

/// Detailed view of a specific heat with full racer and result information
class HeatDetailScreen extends ConsumerWidget {
  final int roundId;
  final int heat;

  const HeatDetailScreen({
    super.key,
    required this.roundId,
    required this.heat,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final heatDetailAsync = ref.watch(
      heatDetailProvider(roundId: roundId, heat: heat),
    );

    return Scaffold(
      appBar: AppBar(
        title: Text('Heat $heat Details'),
      ),
      body: heatDetailAsync.when(
        data: (heatDetail) {
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(
                heatDetailProvider(roundId: roundId, heat: heat),
              );
              await Future.delayed(const Duration(milliseconds: 500));
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Heat info header
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            heatDetail.roundName,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Icon(
                                Icons.class_,
                                size: 16,
                                color: Colors.grey[600],
                              ),
                              const SizedBox(width: 4),
                              Text(
                                heatDetail.className,
                                style: TextStyle(color: Colors.grey[700]),
                              ),
                              const Spacer(),
                              Icon(
                                heatDetail.isComplete
                                    ? Icons.check_circle
                                    : Icons.pending,
                                size: 16,
                                color: heatDetail.isComplete
                                    ? Colors.green
                                    : Colors.orange,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                heatDetail.isComplete
                                    ? 'Completed'
                                    : 'In Progress',
                                style: TextStyle(
                                  color: heatDetail.isComplete
                                      ? Colors.green
                                      : Colors.orange,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Results card
                  if (heatDetail.isComplete) ...[
                    HeatResultsCard(heatDetail: heatDetail),
                    const SizedBox(height: 16),
                  ],

                  // Racer details section
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.people, size: 20),
                              const SizedBox(width: 8),
                              Text(
                                'Racers',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ],
                          ),
                          const Divider(height: 24),
                          ...heatDetail.racersWithResults.map(
                            (racerWithResult) => RacerResultTile(
                              racer: racerWithResult.racer,
                              result: heatDetail.isComplete
                                  ? racerWithResult.result
                                  : null,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
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
                  'Failed to load heat details',
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
