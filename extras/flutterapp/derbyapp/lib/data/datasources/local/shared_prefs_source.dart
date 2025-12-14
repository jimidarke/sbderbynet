import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/constants/app_constants.dart';

/// Local data source for non-sensitive data using SharedPreferences
class SharedPrefsSource {
  final SharedPreferences _prefs;

  SharedPrefsSource(this._prefs);

  /// Save server URL
  Future<bool> saveServerUrl(String url) async {
    return await _prefs.setString(AppConstants.storageKeyServerUrl, url);
  }

  /// Get server URL
  String? getServerUrl() {
    return _prefs.getString(AppConstants.storageKeyServerUrl);
  }

  /// Check if server URL is configured
  bool hasServerUrl() {
    return _prefs.containsKey(AppConstants.storageKeyServerUrl);
  }

  /// Clear server URL
  Future<bool> clearServerUrl() async {
    return await _prefs.remove(AppConstants.storageKeyServerUrl);
  }

  /// Clear all data
  Future<bool> clearAll() async {
    return await _prefs.clear();
  }
}
