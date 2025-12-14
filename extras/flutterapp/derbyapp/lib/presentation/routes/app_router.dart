import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../screens/server_config/server_config_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../providers/config/server_config_provider.dart';
import '../providers/auth/auth_provider.dart';

part 'app_router.g.dart';

/// Routes
class AppRoutes {
  static const serverConfig = '/server-config';
  static const login = '/login';
  static const dashboard = '/';
}

/// GoRouter provider - simplified for Phase 1
/// Auth bypassed - coordinator endpoint is public
/// Server URL hardcoded - static connection
@riverpod
GoRouter goRouter(GoRouterRef ref) {
  return GoRouter(
    initialLocation: AppRoutes.dashboard,
    debugLogDiagnostics: true,
    routes: [
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
    ],
  );
}
