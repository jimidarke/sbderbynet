import 'package:dartz/dartz.dart';
import '../../core/errors/failures.dart';
import '../entities/user.dart';

/// Authentication repository interface
/// Defines contract for authentication operations
abstract class AuthRepository {
  /// Login with username and password
  /// Returns Either<Failure, User> - Left for failure, Right for success
  Future<Either<Failure, User>> login({
    required String username,
    required String password,
  });

  /// Logout current user
  Future<Either<Failure, void>> logout();

  /// Get currently logged in user from stored session
  Future<Either<Failure, User?>> getCurrentUser();

  /// Check if user is authenticated (has valid session)
  Future<bool> isAuthenticated();
}
