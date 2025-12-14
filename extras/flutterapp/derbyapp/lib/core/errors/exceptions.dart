/// Base class for all exceptions in the application
class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException(this.message, [this.statusCode]);

  @override
  String toString() => 'AppException: $message (Status: $statusCode)';
}

/// Exception thrown when server returns an error
class ServerException extends AppException {
  const ServerException(super.message, [super.statusCode]);
}

/// Exception thrown when there's no internet connection
class NetworkException extends AppException {
  const NetworkException(super.message, [super.statusCode]);
}

/// Exception thrown when authentication fails
class AuthException extends AppException {
  const AuthException(super.message, [super.statusCode]);
}

/// Exception thrown when cache operations fail
class CacheException extends AppException {
  const CacheException(super.message, [super.statusCode]);
}

/// Exception thrown when data validation fails
class ValidationException extends AppException {
  const ValidationException(super.message, [super.statusCode]);
}

/// Exception thrown when request times out
class TimeoutException extends AppException {
  const TimeoutException(super.message, [super.statusCode]);
}
