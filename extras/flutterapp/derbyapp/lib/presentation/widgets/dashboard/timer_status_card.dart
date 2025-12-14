import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/race/race_poll_provider.dart';

class TimerStatusCard extends ConsumerWidget {
  const TimerStatusCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pollStream = ref.watch(racePollStreamProvider());

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: pollStream.when(
          data: (response) {
            final timer = response.timerState;
            final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
            final secondsSinceContact = now - timer.lastContact;
            final isConnected = secondsSinceContact < 5; // Consider connected if < 5 seconds

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    Icon(
                      isConnected ? Icons.timer : Icons.timer_off,
                      size: 24,
                      color: isConnected ? Colors.blue : Colors.grey,
                    ),
                    const SizedBox(width: 12),
                    Text(
                      'Timer Status',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ],
                ),
                const Divider(height: 24),

                // Timer State
                _buildStatusRow(
                  context,
                  'State',
                  _getTimerStateDescription(timer.state),
                  _getTimerStateIcon(timer.state),
                  _getTimerStateColor(timer.state),
                ),
                const SizedBox(height: 12),

                // Lanes
                _buildInfoRow(
                  context,
                  'Lanes',
                  '${timer.lanes}',
                  Icons.straighten,
                ),
                const SizedBox(height: 12),

                // Last Contact
                _buildInfoRow(
                  context,
                  'Last Contact',
                  secondsSinceContact < 60
                      ? '${secondsSinceContact}s ago'
                      : '${(secondsSinceContact / 60).floor()}m ago',
                  Icons.access_time,
                ),

                // Connection Warning
                if (!isConnected)
                  Container(
                    margin: const EdgeInsets.only(top: 12),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.orange[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: Colors.orange[300]!,
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.warning_amber,
                          color: Colors.orange,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Timer connection may be lost',
                            style: TextStyle(
                              color: Colors.orange[900],
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
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
                    'Failed to load timer status',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusRow(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            size: 20,
            color: color,
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
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color,
              ),
              textAlign: TextAlign.end,
            ),
          ),
        ],
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
        return 'Racing';
      case 4:
        return 'Finished';
      default:
        return 'Unknown ($state)';
    }
  }

  IconData _getTimerStateIcon(int state) {
    switch (state) {
      case 0:
        return Icons.link_off;
      case 1:
        return Icons.link;
      case 2:
        return Icons.check_circle;
      case 3:
        return Icons.play_circle_filled;
      case 4:
        return Icons.flag;
      default:
        return Icons.help_outline;
    }
  }

  Color _getTimerStateColor(int state) {
    switch (state) {
      case 0:
        return Colors.red;
      case 1:
        return Colors.blue;
      case 2:
        return Colors.green;
      case 3:
        return Colors.orange;
      case 4:
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }
}
