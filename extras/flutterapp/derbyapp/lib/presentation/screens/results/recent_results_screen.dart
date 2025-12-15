import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/race/race_results_provider.dart';
import '../../widgets/results/heat_results_card.dart';
import '../../routes/app_router.dart';

/// Screen showing the most recently completed heat and its results
/// Auto-refreshes every 2 seconds to show new results
class RecentResultsScreen extends ConsumerWidget {
  const RecentResultsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentResultsStream = ref.watch(recentResultsStreamProvider());

    return Scaffold(
      appBar: AppBar(
        title: const Text('Recent Results'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'View All Heats',
            onPressed: () => context.push(AppRoutes.heatHistory),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(recentResultsStreamProvider);
          await Future.delayed(const Duration(milliseconds: 500));
        },
        child: recentResultsStream.when(
          data: (heatDetail) {
            if (heatDetail == null) {
              return Center(
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.emoji_events_outlined,
                        size: 80,
                        color: Colors.grey[400],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No Results Yet',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Complete a heat to see results here',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ),
              );
            }

            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header with "Most Recent" badge
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.new_releases,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Most Recent',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.primary,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Heat results card (reusable widget)
                  HeatResultsCard(heatDetail: heatDetail),

                  const SizedBox(height: 24),

                  // Quick actions
                  OutlinedButton.icon(
                    onPressed: () => context.push(AppRoutes.heatHistory),
                    icon: const Icon(Icons.history),
                    label: const Text('View All Heat History'),
                  ),
                ],
              ),
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => Center(
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, size: 64, color: Colors.red),
                    const SizedBox(height: 16),
                    Text(
                      'Failed to load results',
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
        ),
      ),
    );
  }
}
