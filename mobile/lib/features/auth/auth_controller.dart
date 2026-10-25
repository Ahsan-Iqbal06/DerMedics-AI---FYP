import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

class AuthState {
  const AuthState(this.status, [this.user]);
  final AuthStatus status;
  final AppUser? user;
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(AuthController.new);

class AuthController extends Notifier<AuthState> {
  DerMedicsRepository get _repo => ref.read(repositoryProvider);
  TokenStore get _tokens => ref.read(tokenStoreProvider);

  @override
  AuthState build() {
    ref.read(apiClientProvider).onSessionExpired = () => state = const AuthState(AuthStatus.unauthenticated);
    _restore();
    return const AuthState(AuthStatus.unknown);
  }

  /// On launch, a stored session is validated against /auth/me (refreshing the access token if needed).
  Future<void> _restore() async {
    if (await _tokens.refreshToken == null) {
      state = const AuthState(AuthStatus.unauthenticated);
      return;
    }
    try {
      state = AuthState(AuthStatus.authenticated, await _repo.me());
    } on ApiException catch (e) {
      if (e.statusCode == 401 || e.statusCode == 403) await _tokens.clear();
      state = const AuthState(AuthStatus.unauthenticated);
    }
  }

  Future<void> login(String email, String password) async {
    final res = await _repo.login(email.trim(), password);
    await _tokens.save(res.accessToken, res.refreshToken);
    state = AuthState(AuthStatus.authenticated, res.user);
  }

  Future<void> register({
    required String fullName,
    required String email,
    required String password,
    required String confirmPassword,
    required String country,
    required String city,
    required bool acceptTerms,
  }) async {
    final res = await _repo.register(
      fullName: fullName.trim(),
      email: email.trim(),
      password: password,
      confirmPassword: confirmPassword,
      country: country.trim(),
      city: city.trim(),
      acceptTerms: acceptTerms,
    );
    await _tokens.save(res.accessToken, res.refreshToken);
    state = AuthState(AuthStatus.authenticated, res.user);
  }

  void setUser(AppUser user) => state = AuthState(AuthStatus.authenticated, user);

  Future<void> logout() async {
    final refresh = await _tokens.refreshToken;
    if (refresh != null) {
      try {
        await _repo.logout(refresh);
      } catch (_) {
        // Still sign out locally if the server can't be reached.
      }
    }
    await _tokens.clear();
    state = const AuthState(AuthStatus.unauthenticated);
  }
}

/// Client-side mirrors of the backend's validation rules, for instant feedback.
class Validators {
  static final _email = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$');

  static String? email(String? v) {
    if (v == null || v.trim().isEmpty) return 'Enter your email';
    if (!_email.hasMatch(v.trim())) return 'Enter a valid email address';
    return null;
  }

  static String? name(String? v) {
    final s = v?.trim() ?? '';
    if (s.length < 2 || !s.contains(RegExp(r'[A-Za-z]'))) return 'Enter your full name';
    return null;
  }

  static List<(String, bool)> passwordChecks(String v) => [
        ('8+ characters', v.length >= 8),
        ('Uppercase', v.contains(RegExp(r'[A-Z]'))),
        ('Lowercase', v.contains(RegExp(r'[a-z]'))),
        ('Number', v.contains(RegExp(r'\d'))),
        ('Symbol', v.contains(RegExp(r'[^A-Za-z0-9]'))),
      ];

  static String? strongPassword(String? v) {
    if (v == null || v.isEmpty) return 'Enter a password';
    final missing = passwordChecks(v).where((c) => !c.$2).map((c) => c.$1.toLowerCase()).toList();
    if (missing.isNotEmpty) return 'Password needs: ${missing.join(', ')}';
    return null;
  }
}
