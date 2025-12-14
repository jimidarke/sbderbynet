import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../core/constants/app_constants.dart';

/// Local data source for secure credential storage using Flutter Secure Storage
/// Data is encrypted at rest using platform-specific secure storage (Android Keystore/iOS Keychain)
class SecureStorageSource {
  final FlutterSecureStorage _storage;

  SecureStorageSource(this._storage);

  /// Save user credentials
  Future<void> saveCredentials({
    required String username,
    required String password,
  }) async {
    await Future.wait([
      _storage.write(key: AppConstants.storageKeyUsername, value: username),
      _storage.write(key: AppConstants.storageKeyPassword, value: password),
    ]);
  }

  /// Get stored username
  Future<String?> getUsername() async {
    return await _storage.read(key: AppConstants.storageKeyUsername);
  }

  /// Get stored password
  Future<String?> getPassword() async {
    return await _storage.read(key: AppConstants.storageKeyPassword);
  }

  /// Save session data (cookie and role)
  Future<void> saveSession({
    required String sessionCookie,
    required String role,
  }) async {
    await Future.wait([
      _storage.write(key: AppConstants.storageKeySessionCookie, value: sessionCookie),
      _storage.write(key: AppConstants.storageKeyUserRole, value: role),
    ]);
  }

  /// Get session cookie (PHPSESSID)
  Future<String?> getSessionCookie() async {
    return await _storage.read(key: AppConstants.storageKeySessionCookie);
  }

  /// Get user role
  Future<String?> getUserRole() async {
    return await _storage.read(key: AppConstants.storageKeyUserRole);
  }

  /// Clear all stored data (logout)
  Future<void> clearAll() async {
    await _storage.deleteAll();
  }

  /// Check if user has saved credentials
  Future<bool> hasCredentials() async {
    final username = await getUsername();
    final password = await getPassword();
    return username != null && password != null;
  }

  /// Check if user has valid session
  Future<bool> hasSession() async {
    final sessionCookie = await getSessionCookie();
    return sessionCookie != null;
  }
}
