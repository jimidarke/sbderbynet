import 'package:equatable/equatable.dart';

/// Base class for all failures in the application
/// Uses Equatable for value equality comparisons
abstract class Failure extends Equatable {
  final String message;

  const Failure(this.message);

  @override
  List<Object> get props => [message];
}

/// Failure when server returns an error response
class ServerFailure extends Failure {
  const ServerFailure(super.message);
}

/// Failure when there's no internet connection
class NetworkFailure extends Failure {
  const NetworkFailure(super.message);
}

/// Failure when authentication fails (invalid credentials, expired session, etc.)
class AuthFailure extends Failure {
  const AuthFailure(super.message);
}

/// Failure when cache operations fail
class CacheFailure extends Failure {
  const CacheFailure(super.message);
}

/// Failure when data validation fails
class ValidationFailure extends Failure {
  const ValidationFailure(super.message);
}

/// Failure for unexpected errors
class UnknownFailure extends Failure {
  const UnknownFailure(super.message);
}

/// Failure when request times out
class TimeoutFailure extends Failure {
  const TimeoutFailure(super.message);
}
