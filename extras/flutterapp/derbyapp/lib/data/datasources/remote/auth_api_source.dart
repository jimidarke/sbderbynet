import 'package:dio/dio.dart';
import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/errors/exceptions.dart';

/// Remote data source for authentication API calls to DerbyNet server
class AuthApiSource {
  final DioClient _dioClient;

  AuthApiSource(this._dioClient);

  /// Login with username and password
  /// Returns the session cookie (PHPSESSID) and user role
  Future<Map<String, dynamic>> login({
    required String username,
    required String password,
  }) async {
    try {
      final response = await _dioClient.post(
        ApiEndpoints.login,
        data: {
          'name': username,
          'password': password,
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );

      // Extract PHPSESSID cookie from response headers
      String? sessionCookie;
      final cookies = response.headers['set-cookie'];
      if (cookies != null) {
        for (var cookie in cookies) {
          if (cookie.startsWith('PHPSESSID=')) {
            sessionCookie = cookie.split(';')[0]; // Get just the cookie value
            break;
          }
        }
      }

      if (sessionCookie == null) {
        throw AuthException('No session cookie received from server');
      }

      // Check if login was successful
      final data = response.data as Map<String, dynamic>;
      if (data['outcome'] != null && data['outcome'] != 'success') {
        throw AuthException(data['message'] ?? 'Login failed');
      }

      return {
        'sessionCookie': sessionCookie,
        'role': data['role'] ?? username, // Use username as role if not provided
        'outcome': data['outcome'] ?? 'success',
      };
    } on DioException catch (e) {
      if (e.response?.statusCode == 401 || e.response?.statusCode == 403) {
        throw const AuthException('Invalid credentials');
      }
      throw ServerException(
        e.message ?? 'Authentication server error',
        e.response?.statusCode,
      );
    }
  }

  /// Logout (clear session on server side if needed)
  /// For now, this is handled locally by clearing secure storage
  Future<void> logout() async {
    // DerbyNet doesn't have a specific logout endpoint
    // Session is managed by clearing cookies locally
    return;
  }
}
