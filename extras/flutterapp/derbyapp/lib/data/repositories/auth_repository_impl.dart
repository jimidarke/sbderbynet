import 'package:dartz/dartz.dart';
import '../../core/errors/exceptions.dart';
import '../../core/errors/failures.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/local/secure_storage_source.dart';
import '../datasources/remote/auth_api_source.dart';
import '../../core/network/dio_client.dart';

/// Implementation of AuthRepository
class AuthRepositoryImpl implements AuthRepository {
  final AuthApiSource _authApiSource;
  final SecureStorageSource _secureStorage;
  final DioClient _dioClient;

  AuthRepositoryImpl({
    required AuthApiSource authApiSource,
    required SecureStorageSource secureStorage,
    required DioClient dioClient,
  })  : _authApiSource = authApiSource,
        _secureStorage = secureStorage,
        _dioClient = dioClient;

  @override
  Future<Either<Failure, User>> login({
    required String username,
    required String password,
  }) async {
    try {
      // Call API to login
      final result = await _authApiSource.login(
        username: username,
        password: password,
      );

      final sessionCookie = result['sessionCookie'] as String;
      final role = result['role'] as String;

      // Save credentials and session to secure storage
      await _secureStorage.saveCredentials(
        username: username,
        password: password,
      );
      await _secureStorage.saveSession(
        sessionCookie: sessionCookie,
        role: role,
      );

      // Set session cookie in Dio client for future requests
      _dioClient.setSessionCookie(sessionCookie);

      // Create and return User entity
      final user = User(
        username: username,
        role: UserRole.fromString(role),
        sessionCookie: sessionCookie,
      );

      return Right(user);
    } on AuthException catch (e) {
      return Left(AuthFailure(e.message));
    } on NetworkException catch (e) {
      return Left(NetworkFailure(e.message));
    } on ServerException catch (e) {
      return Left(ServerFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      // Clear all secure storage
      await _secureStorage.clearAll();

      // Clear session cookie from Dio client
      _dioClient.clearSessionCookie();

      return const Right(null);
    } on CacheException catch (e) {
      return Left(CacheFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Future<Either<Failure, User?>> getCurrentUser() async {
    try {
      // Check if session exists
      final sessionCookie = await _secureStorage.getSessionCookie();
      final username = await _secureStorage.getUsername();
      final roleString = await _secureStorage.getUserRole();

      if (sessionCookie == null || username == null || roleString == null) {
        return const Right(null);
      }

      // Restore session cookie to Dio client
      _dioClient.setSessionCookie(sessionCookie);

      final user = User(
        username: username,
        role: UserRole.fromString(roleString),
        sessionCookie: sessionCookie,
      );

      return Right(user);
    } on CacheException catch (e) {
      return Left(CacheFailure(e.message));
    } catch (e) {
      return Left(UnknownFailure(e.toString()));
    }
  }

  @override
  Future<bool> isAuthenticated() async {
    return await _secureStorage.hasSession();
  }
}
