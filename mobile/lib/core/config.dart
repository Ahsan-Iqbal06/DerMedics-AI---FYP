import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Where the DerMedics backend lives.
///
/// Order of precedence:
///  1. An address the user saved in the app (Server settings on the sign-in screen), e.g. http://192.168.18.128:8000
///  2. A build-time override: flutter build ios --dart-define=API_BASE_URL=http://192.168.1.10:8000
///  3. Web: the same computer that served the page, on port 8000 (so phones on the same Wi-Fi just work)
///  4. Android emulator: 10.0.2.2 (the host PC); everything else: localhost
class AppConfig {
  static const _override = String.fromEnvironment('API_BASE_URL');
  static const _prefsKey = 'server_url';
  static String? _saved;

  /// Call once at startup, before the first request.
  static Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _saved = prefs.getString(_prefsKey);
    } catch (_) {
      _saved = null;
    }
  }

  static String get defaultBaseUrl {
    if (_override.isNotEmpty) return _override;
    if (kIsWeb) return '${Uri.base.scheme}://${Uri.base.host}:8000';
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
  }

  static String get baseUrl => _saved ?? defaultBaseUrl;
  static String get apiUrl => '$baseUrl/api';
  static bool get isCustom => _saved != null;

  /// Saves a server address such as "192.168.18.128:8000" (http:// is added if missing). Pass null to reset.
  static Future<void> setServerUrl(String? url) async {
    final prefs = await SharedPreferences.getInstance();
    final cleaned = normalize(url);
    _saved = cleaned;
    if (cleaned == null) {
      await prefs.remove(_prefsKey);
    } else {
      await prefs.setString(_prefsKey, cleaned);
    }
  }

  static String? normalize(String? url) {
    var u = url?.trim() ?? '';
    if (u.isEmpty) return null;
    if (!u.startsWith('http://') && !u.startsWith('https://')) u = 'http://$u';
    while (u.endsWith('/')) {
      u = u.substring(0, u.length - 1);
    }
    if (u.endsWith('/api')) u = u.substring(0, u.length - 4);
    return u;
  }
}
