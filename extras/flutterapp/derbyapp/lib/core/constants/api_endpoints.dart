/// API endpoint constants for DerbyNet server
/// Base URL is configured dynamically by user (e.g., http://192.168.100.10)
class ApiEndpoints {
  ApiEndpoints._(); // Private constructor to prevent instantiation

  // Main action endpoint
  static const String action = '/action.php';

  // Authentication endpoints
  static const String login = '$action?action=role.login';

  // Query endpoints
  static const String pollCoordinator = '$action?query=poll.coordinator';
  static const String pollKiosk = '$action?query=poll.kiosk';
  static const String pollOnDeck = '$action?query=poll&values=ondeck';
  static const String racerList = '$action?query=racer.list';
  static const String classList = '$action?query=class.list';
  static const String roundList = '$action?query=round.list';
  static const String awardList = '$action?query=award.list';

  // Device status endpoints
  static const String deviceStatus = '/device-status-api.php';

  // Action endpoints (for future use)
  static const String racerPass = '$action?action=racer.pass';
  static const String racerAdd = '$action?action=racer.add';
  static const String scheduleGenerate = '$action?action=schedule.generate';

  /// Build full URL with base URL
  /// Example: buildUrl('http://192.168.100.10', pollCoordinator)
  static String buildUrl(String baseUrl, String endpoint) {
    // Remove trailing slash from baseUrl if present
    final cleanBase = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return '$cleanBase$endpoint';
  }

  /// Add query parameters to endpoint
  /// Example: withParams(pollCoordinator, {'roundid': '5', 'heat': '3'})
  static String withParams(String endpoint, Map<String, dynamic> params) {
    if (params.isEmpty) return endpoint;

    final uri = Uri.parse(endpoint);
    final newParams = Map<String, dynamic>.from(uri.queryParameters)..addAll(params);

    return Uri(
      path: uri.path,
      queryParameters: newParams.map((key, value) => MapEntry(key, value.toString())),
    ).toString();
  }
}
