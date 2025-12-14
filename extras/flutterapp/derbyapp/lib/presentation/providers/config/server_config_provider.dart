import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../data/datasources/local/shared_prefs_source.dart';

part 'server_config_provider.g.dart';

/// Provider for SharedPreferences instance
@riverpod
Future<SharedPreferences> sharedPreferences(SharedPreferencesRef ref) async {
  return await SharedPreferences.getInstance();
}

/// Server configuration notifier
/// Hardcoded for Phase 1 - static server URL
@riverpod
class ServerConfig extends _$ServerConfig {
  @override
  Future<String?> build() async {
    // Phase 1: Hardcoded static server URL
    return 'http://192.168.100.10/derbynet';
  }

  /// Save server URL to persistent storage
  Future<void> setServerUrl(String url) async {
    state = const AsyncValue.loading();

    state = await AsyncValue.guard(() async {
      final prefs = await ref.read(sharedPreferencesProvider.future);
      final prefsSource = SharedPrefsSource(prefs);
      await prefsSource.saveServerUrl(url);
      return url;
    });
  }

  /// Clear server URL from storage
  Future<void> clearServerUrl() async {
    state = const AsyncValue.loading();

    state = await AsyncValue.guard(() async {
      final prefs = await ref.read(sharedPreferencesProvider.future);
      final prefsSource = SharedPrefsSource(prefs);
      await prefsSource.clearServerUrl();
      return null;
    });
  }

  /// Check if server URL is configured
  bool get hasServerUrl => state.value != null && state.value!.isNotEmpty;

  /// Get current server URL
  String? get serverUrl => state.value;
}
