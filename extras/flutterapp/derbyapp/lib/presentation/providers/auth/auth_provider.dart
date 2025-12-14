import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../domain/entities/user.dart';
import '../../../domain/repositories/auth_repository.dart';
import '../../../data/repositories/auth_repository_impl.dart';
import '../../../data/datasources/remote/auth_api_source.dart';
import '../../../data/datasources/local/secure_storage_source.dart';
import '../../../core/network/dio_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/server_config_provider.dart';

part 'auth_provider.g.dart';

/// Provider for DioClient instance
@riverpod
DioClient dioClient(DioClientRef ref) {
  final serverConfigAsync = ref.watch(serverConfigProvider);
  final serverUrl = serverConfigAsync.value ?? 'http://192.168.100.10/derbynet';
  return DioClient(baseUrl: serverUrl);
}

/// Provider for SecureStorageSource
@riverpod
SecureStorageSource secureStorageSource(SecureStorageSourceRef ref) {
  return SecureStorageSource(const FlutterSecureStorage());
}

/// Provider for AuthApiSource
@riverpod
AuthApiSource authApiSource(AuthApiSourceRef ref) {
  final dioClient = ref.watch(dioClientProvider);
  return AuthApiSource(dioClient);
}

/// Provider for AuthRepository
@riverpod
AuthRepository authRepository(AuthRepositoryRef ref) {
  final authApiSource = ref.watch(authApiSourceProvider);
  final secureStorage = ref.watch(secureStorageSourceProvider);
  final dioClient = ref.watch(dioClientProvider);

  return AuthRepositoryImpl(
    authApiSource: authApiSource,
    secureStorage: secureStorage,
    dioClient: dioClient,
  );
}

/// Auth state notifier that manages authentication state
@riverpod
class Auth extends _$Auth {
  @override
  Future<User?> build() async {
    // Check if user is already authenticated on app start
    final repository = ref.read(authRepositoryProvider);
    final result = await repository.getCurrentUser();

    return result.fold(
      (failure) => null,
      (user) => user,
    );
  }

  /// Login with username and password
  Future<void> login({
    required String username,
    required String password,
  }) async {
    state = const AsyncValue.loading();

    final repository = ref.read(authRepositoryProvider);
    final result = await repository.login(
      username: username,
      password: password,
    );

    state = await AsyncValue.guard(() async {
      return result.fold(
        (failure) => throw Exception(failure.message),
        (user) => user,
      );
    });
  }

  /// Logout current user
  Future<void> logout() async {
    state = const AsyncValue.loading();

    final repository = ref.read(authRepositoryProvider);
    final result = await repository.logout();

    state = await AsyncValue.guard(() async {
      return result.fold(
        (failure) => throw Exception(failure.message),
        (_) => null,
      );
    });
  }

  /// Check if user is authenticated
  bool get isAuthenticated => state.value != null;

  /// Get current user
  User? get currentUser => state.value;
}
