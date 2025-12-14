import 'package:equatable/equatable.dart';

/// User roles in the application
enum UserRole {
  admin,
  staff,
  guest;

  /// Convert string to UserRole
  static UserRole fromString(String role) {
    switch (role.toLowerCase()) {
      case 'admin':
        return UserRole.admin;
      case 'staff':
        return UserRole.staff;
      case 'guest':
        return UserRole.guest;
      default:
        return UserRole.guest;
    }
  }
}

/// User entity representing an authenticated user
class User extends Equatable {
  final String username;
  final UserRole role;
  final String sessionCookie;

  const User({
    required this.username,
    required this.role,
    required this.sessionCookie,
  });

  @override
  List<Object?> get props => [username, role, sessionCookie];

  /// Check if user has admin privileges
  bool get isAdmin => role == UserRole.admin;

  /// Check if user has staff privileges
  bool get isStaff => role == UserRole.staff || role == UserRole.admin;
}
