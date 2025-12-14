import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/race/race_poll_provider.dart';

class CurrentHeatCard extends ConsumerWidget {
  const CurrentHeatCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pollStream = ref.watch(racePollStreamProvider());

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: pollStream.when(
          data: (response) {
            final heat = response.currentHeat;

            // Look up round name from rounds array
            String? roundName;
            if (heat.roundid != null) {
              final matchingRound = response.rounds.firstWhere(
                (r) => r.roundid == heat.roundid,
                orElse: () => response.rounds.first,
              );
              roundName = matchingRound.roundname;
            }

            final timerState = response.timerState;

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Round name header
                Text(
                  roundName ?? 'Current Heat',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 16),

                // Timer Status and Heat Counter - side by side
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Timer Status Card (2/3 width) - Traffic Light
                    Expanded(
                      flex: 2,
                      child: Card(
                        elevation: 1,
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              // Traffic light circle
                              Container(
                                width: 80,
                                height: 80,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: _getTrafficLightColor(timerState.state),
                                  boxShadow: [
                                    BoxShadow(
                                      color: _getTrafficLightColor(timerState.state).withOpacity(0.5),
                                      blurRadius: 12,
                                      spreadRadius: 2,
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 12),
                              // Status label
                              Text(
                                _getTimerStateDescription(timerState.state),
                                style: TextStyle(
                                  color: Colors.grey[700],
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),

                    // Heat Counter Card (1/3 width)
                    Expanded(
                      flex: 1,
                      child: Card(
                        elevation: 1,
                        color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            children: [
                              Icon(
                                Icons.format_list_numbered,
                                size: 32,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                heat.heat?.toString() ?? '-',
                                style: TextStyle(
                                  fontSize: 28,
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                              Text(
                                'of ${heat.numberOfHeats}',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),

                // Additional info if available
                if (heat.className != null && heat.className!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _buildInfoRow(
                    context,
                    'Class',
                    heat.className!,
                    Icons.category,
                  ),
                ],
              ],
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
                    'Failed to load heat data',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    error.toString().replaceAll('Exception: ', ''),
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    return Row(
      children: [
        Icon(
          icon,
          size: 20,
          color: Colors.grey[600],
        ),
        const SizedBox(width: 12),
        Text(
          '$label:',
          style: TextStyle(
            color: Colors.grey[700],
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.end,
          ),
        ),
      ],
    );
  }

  String _getTimerStateDescription(int state) {
    // Based on DerbyNet timer states
    switch (state) {
      case 0:
        return 'Not Connected';
      case 1:
        return 'Connected';
      case 2:
        return 'Ready';
      case 3:
        return 'Staging';
      case 4:
        return 'Racing';
      case 5:
        return 'Finished';
      default:
        return 'Unknown';
    }
  }

  /// Traffic light color mapping for simplified display
  /// Red = Stopped/Waiting, Yellow = Staging, Green = Racing
  Color _getTrafficLightColor(int state) {
    switch (state) {
      case 3: // Staging
        return Colors.yellow[700]!;
      case 4: // Racing
        return Colors.green[600]!;
      default: // Not Connected, Connected, Ready, Finished
        return Colors.red[600]!;
    }
  }
}
