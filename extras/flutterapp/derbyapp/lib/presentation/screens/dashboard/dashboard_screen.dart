import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/race/race_poll_provider.dart';
import '../../providers/config/server_config_provider.dart';
import '../../widgets/dashboard/current_heat_card.dart';
import '../../widgets/dashboard/racer_lineup_card.dart';
import '../../widgets/dashboard/connection_indicator.dart';
import 'package:go_router/go_router.dart';
import '../../routes/app_router.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final serverConfigAsync = ref.watch(serverConfigProvider);
    final serverUrl = serverConfigAsync.value ?? '';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Race Dashboard'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          // Connection Indicator
          const ConnectionIndicator(),
          const SizedBox(width: 16),

          // Settings Menu
          PopupMenuButton<String>(
            icon: const Icon(Icons.settings),
            itemBuilder: (context) => [
              PopupMenuItem(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Server',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      serverUrl,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[600],
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              PopupMenuItem(
                child: const Row(
                  children: [
                    Icon(Icons.settings_ethernet),
                    SizedBox(width: 8),
                    Text('Change Server'),
                  ],
                ),
                onTap: () {
                  // Delay to allow popup to close
                  Future.delayed(
                    const Duration(milliseconds: 100),
                    () => context.go(AppRoutes.serverConfig),
                  );
                },
              ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          // Invalidate the race poll to force a refresh
          ref.invalidate(racePollStreamProvider);
          await Future.delayed(const Duration(milliseconds: 500));
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Current Heat Card (includes timer state)
              const CurrentHeatCard(),
              const SizedBox(height: 16),

              // Racer Lineup Card
              const RacerLineupCard(),
              const SizedBox(height: 16),

              // Quick Actions Card
              Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.menu, size: 24),
                          const SizedBox(width: 12),
                          Text(
                            'Quick Actions',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const Divider(height: 24),
                      ElevatedButton.icon(
                        onPressed: () => context.push(AppRoutes.racingSchedule),
                        icon: const Icon(Icons.schedule),
                        label: const Text('View Racing Schedule'),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () => context.push(AppRoutes.heatHistory),
                        icon: const Icon(Icons.history),
                        label: const Text('Heat History'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Last Updated Timestamp
              Consumer(
                builder: (context, ref, child) {
                  final pollStream = ref.watch(racePollStreamProvider());

                  return pollStream.when(
                    data: (response) {
                      final lastContact = response.timerState.lastContact;
                      final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
                      final secondsAgo = now - lastContact;

                      return Center(
                        child: Text(
                          'Last updated: ${secondsAgo}s ago',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 12,
                          ),
                        ),
                      );
                    },
                    loading: () => const Center(
                      child: Text(
                        'Connecting...',
                        style: TextStyle(
                          color: Colors.grey,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    error: (error, _) => const Center(
                      child: Text(
                        'Connection error',
                        style: TextStyle(
                          color: Colors.red,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
