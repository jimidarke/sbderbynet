import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../constants/app_constants.dart';
import '../errors/exceptions.dart';

/// Configured Dio client for making HTTP requests to DerbyNet server
class DioClient {
  late final Dio _dio;
  final Logger _logger = Logger();

  DioClient({String? baseUrl}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl ?? AppConstants.defaultServerUrl,
        connectTimeout: AppConstants.connectTimeout,
        receiveTimeout: AppConstants.receiveTimeout,
        sendTimeout: AppConstants.sendTimeout,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      ),
    );

    _dio.interceptors.add(_loggingInterceptor());
    _dio.interceptors.add(_errorInterceptor());
  }

  /// Get the Dio instance
  Dio get dio => _dio;

  /// Update the base URL (when user changes server configuration)
  void updateBaseUrl(String newBaseUrl) {
    _dio.options.baseUrl = newBaseUrl;
    _logger.i('Base URL updated to: $newBaseUrl');
  }

  /// Add session cookie to headers
  void setSessionCookie(String sessionCookie) {
    _dio.options.headers['Cookie'] = sessionCookie;
    _logger.d('Session cookie set');
  }

  /// Remove session cookie from headers
  void clearSessionCookie() {
    _dio.options.headers.remove('Cookie');
    _logger.d('Session cookie cleared');
  }

  /// Logging interceptor for debugging
  Interceptor _loggingInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) {
        _logger.d('REQUEST[${options.method}] => PATH: ${options.path}');
        _logger.d('Headers: ${options.headers}');
        if (options.data != null) {
          _logger.d('Data: ${options.data}');
        }
        return handler.next(options);
      },
      onResponse: (response, handler) {
        _logger.d('RESPONSE[${response.statusCode}] => PATH: ${response.requestOptions.path}');
        _logger.d('Data: ${response.data}');
        return handler.next(response);
      },
      onError: (error, handler) {
        _logger.e('ERROR[${error.response?.statusCode}] => PATH: ${error.requestOptions.path}');
        _logger.e('Message: ${error.message}');
        return handler.next(error);
      },
    );
  }

  /// Error handling interceptor
  Interceptor _errorInterceptor() {
    return InterceptorsWrapper(
      onError: (error, handler) {
        if (error.type == DioExceptionType.connectionTimeout ||
            error.type == DioExceptionType.receiveTimeout ||
            error.type == DioExceptionType.sendTimeout) {
          throw TimeoutException('Request timed out', error.response?.statusCode);
        }

        if (error.type == DioExceptionType.connectionError) {
          throw NetworkException('No internet connection', error.response?.statusCode);
        }

        if (error.response != null) {
          final statusCode = error.response!.statusCode;

          if (statusCode == 401 || statusCode == 403) {
            throw AuthException('Authentication failed', statusCode);
          }

          if (statusCode != null && statusCode >= 500) {
            throw ServerException('Server error occurred', statusCode);
          }

          if (statusCode != null && statusCode >= 400) {
            throw ServerException(
              error.response?.data['message'] ?? 'Client error occurred',
              statusCode,
            );
          }
        }

        return handler.next(error);
      },
    );
  }

  /// GET request
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      _logger.e('GET request failed: ${e.message}');
      rethrow;
    }
  }

  /// POST request
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      _logger.e('POST request failed: ${e.message}');
      rethrow;
    }
  }

  /// PUT request
  Future<Response> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      _logger.e('PUT request failed: ${e.message}');
      rethrow;
    }
  }

  /// DELETE request
  Future<Response> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      _logger.e('DELETE request failed: ${e.message}');
      rethrow;
    }
  }
}
