// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auth_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$dioClientHash() => r'47f68f9710c837061bee95e6bd326790cff1f197';

/// Provider for DioClient instance
///
/// Copied from [dioClient].
@ProviderFor(dioClient)
final dioClientProvider = AutoDisposeProvider<DioClient>.internal(
  dioClient,
  name: r'dioClientProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$dioClientHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef DioClientRef = AutoDisposeProviderRef<DioClient>;
String _$secureStorageSourceHash() =>
    r'13cb73869dfbebae5f9b96482cfe85a7f81f34d5';

/// Provider for SecureStorageSource
///
/// Copied from [secureStorageSource].
@ProviderFor(secureStorageSource)
final secureStorageSourceProvider =
    AutoDisposeProvider<SecureStorageSource>.internal(
      secureStorageSource,
      name: r'secureStorageSourceProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$secureStorageSourceHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SecureStorageSourceRef = AutoDisposeProviderRef<SecureStorageSource>;
String _$authApiSourceHash() => r'4a69cd538683639d3f13a8f7e797f511d3be3aea';

/// Provider for AuthApiSource
///
/// Copied from [authApiSource].
@ProviderFor(authApiSource)
final authApiSourceProvider = AutoDisposeProvider<AuthApiSource>.internal(
  authApiSource,
  name: r'authApiSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$authApiSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AuthApiSourceRef = AutoDisposeProviderRef<AuthApiSource>;
String _$authRepositoryHash() => r'31608e853dacdb64244cdfc72eecbf696a5d6c64';

/// Provider for AuthRepository
///
/// Copied from [authRepository].
@ProviderFor(authRepository)
final authRepositoryProvider = AutoDisposeProvider<AuthRepository>.internal(
  authRepository,
  name: r'authRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$authRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AuthRepositoryRef = AutoDisposeProviderRef<AuthRepository>;
String _$authHash() => r'50b08fb51979eece1cabb30d2739422fafe0e4cf';

/// Auth state notifier that manages authentication state
///
/// Copied from [Auth].
@ProviderFor(Auth)
final authProvider = AutoDisposeAsyncNotifierProvider<Auth, User?>.internal(
  Auth.new,
  name: r'authProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$authHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$Auth = AutoDisposeAsyncNotifier<User?>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
