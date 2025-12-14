import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../screens/splash_screen.dart';
import '../screens/server_config/server_config_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/results/racing_schedule_screen.dart';
import '../screens/results/heat_history_screen.dart';
import '../screens/results/heat_detail_screen.dart';
import '../providers/config/server_config_provider.dart';
import '../providers/auth/auth_provider.dart';

part 'app_router.g.dart';

/// Routes
class AppRoutes {
  static const splash = '/';
  static const serverConfig = '/server-config';
  static const login = '/login';
  static const dashboard = '/dashboard';
  static const racingSchedule = '/schedule';
  static const heatHistory = '/results/history';

  /// Parameterized route helper for heat detail
  static String heatDetail({required int roundId, required int heat}) =>
      '/results/heat/$roundId/$heat';
}

/// GoRouter provider - simplified for Phase 1
/// Auth bypassed - coordinator endpoint is public
/// Server URL hardcoded - static connection
@riverpod
GoRouter goRouter(GoRouterRef ref) {
  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: true,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        name: 'splash',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const SplashScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.serverConfig,
        name: 'server-config',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const ServerConfigScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.login,
        name: 'login',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const LoginScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.dashboard,
        name: 'dashboard',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const DashboardScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.racingSchedule,
        name: 'racing-schedule',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const RacingScheduleScreen(),
        ),
      ),
      GoRoute(
        path: AppRoutes.heatHistory,
        name: 'heat-history',
        pageBuilder: (context, state) => MaterialPage(
          key: state.pageKey,
          child: const HeatHistoryScreen(),
        ),
      ),
      GoRoute(
        path: '/results/heat/:roundId/:heat',
        name: 'heat-detail',
        pageBuilder: (context, state) {
          final roundId = int.parse(state.pathParameters['roundId']!);
          final heat = int.parse(state.pathParameters['heat']!);

          return MaterialPage(
            key: state.pageKey,
            child: HeatDetailScreen(roundId: roundId, heat: heat),
          );
        },
      ),
    ],
  );
}
