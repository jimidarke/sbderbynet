/// Application-wide constants
class AppConstants {
  AppConstants._(); // Private constructor

  // App info
  static const String appName = 'SBDerbyNet';
  static const String appVersion = '1.0.0';

  // Polling intervals
  static const Duration coordinatorPollInterval = Duration(seconds: 1);
  static const Duration kioskPollInterval = Duration(seconds: 2);

  // Network timeouts
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 10);
  static const Duration sendTimeout = Duration(seconds: 10);

  // Storage keys
  static const String storageKeyServerUrl = 'server_url';
  static const String storageKeyUsername = 'username';
  static const String storageKeyPassword = 'password';
  static const String storageKeySessionCookie = 'phpsessid';
  static const String storageKeyUserRole = 'user_role';

  // User roles
  static const String roleAdmin = 'admin';
  static const String roleStaff = 'staff';
  static const String roleGuest = 'guest';

  // Default values
  static const String defaultServerUrl = 'http://192.168.100.10';

  // Error messages
  static const String errorNoInternet = 'No internet connection';
  static const String errorServerUnreachable = 'Cannot reach DerbyNet server';
  static const String errorInvalidCredentials = 'Invalid username or password';
  static const String errorSessionExpired = 'Session expired. Please login again';
  static const String errorUnknown = 'An unexpected error occurred';
}
