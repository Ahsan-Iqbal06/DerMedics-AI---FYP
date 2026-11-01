import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

/// Thrown for any API failure, carrying a message safe to show to the user.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.errorCode});
  final String message;
  final int? statusCode;

  /// Machine-readable reason from the server's X-Error-Code header, e.g. 'email_not_verified'.
  final String? errorCode;

  @override
  String toString() => message;

  static ApiException from(Object error) {
    if (error is ApiException) return error;
    if (error is DioException) {
      final data = error.response?.data;
      final code = error.response?.statusCode;
      if (data is Map && data['detail'] is String) {
        return ApiException(data['detail'] as String,
            statusCode: code, errorCode: error.response?.headers.value('x-error-code'));
      }
      switch (error.type) {
        case DioExceptionType.connectionError:
        case DioExceptionType.connectionTimeout:
          return ApiException('Cannot reach the DerMedics server. Check your connection and try again.');
        case DioExceptionType.receiveTimeout:
        case DioExceptionType.sendTimeout:
          return ApiException('The server took too long to respond. Please try again.');
        default:
          return ApiException('Something went wrong (${code ?? 'network'}). Please try again.', statusCode: code);
      }
    }
    return ApiException('Something went wrong. Please try again.');
  }
}

/// Keeps the sign-in tokens: Keychain/Keystore on phones, browser storage on the web.
/// (Secure storage on the web needs HTTPS, which a phone opening the app over plain Wi-Fi doesn't have.)
class TokenStore {
  static const _access = 'access_token';
  static const _refresh = 'refresh_token';
  final _storage = const FlutterSecureStorage();

  String? _cachedAccess;

  Future<String?> _read(String key) async {
    if (kIsWeb) return (await SharedPreferences.getInstance()).getString(key);
    return _storage.read(key: key);
  }

  Future<void> _write(String key, String value) async {
    if (kIsWeb) {
      await (await SharedPreferences.getInstance()).setString(key, value);
    } else {
      await _storage.write(key: key, value: value);
    }
  }

  Future<void> _delete(String key) async {
    if (kIsWeb) {
      await (await SharedPreferences.getInstance()).remove(key);
    } else {
      await _storage.delete(key: key);
    }
  }

  Future<String?> get accessToken async => _cachedAccess ??= await _read(_access);
  Future<String?> get refreshToken => _read(_refresh);

  Future<void> save(String access, String refresh) async {
    _cachedAccess = access;
    await _write(_access, access);
    await _write(_refresh, refresh);
  }

  Future<void> clear() async {
    _cachedAccess = null;
    await _delete(_access);
    await _delete(_refresh);
  }
}

/// Dio client that attaches the access token and transparently refreshes it once on a 401.
class ApiClient {
  ApiClient(this.tokens) {
    dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 60),
    ));
    dio.interceptors.add(QueuedInterceptorsWrapper(
      onRequest: (options, handler) async {
        // The server address can be changed in the app at any time.
        options.baseUrl = AppConfig.apiUrl;
        if (options.extra['auth'] != false) {
          final token = await tokens.accessToken;
          if (token != null) options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final req = error.requestOptions;
        final isAuthCall = req.extra['auth'] == false;
        if (error.response?.statusCode == 401 && !isAuthCall && req.extra['retried'] != true) {
          if (await _refresh()) {
            req.extra['retried'] = true;
            req.headers['Authorization'] = 'Bearer ${await tokens.accessToken}';
            try {
              return handler.resolve(await dio.fetch(req));
            } on DioException catch (e) {
              return handler.next(e);
            }
          }
          await tokens.clear();
          onSessionExpired?.call();
        }
        handler.next(error);
      },
    ));
  }

  final TokenStore tokens;
  late final Dio dio;
  void Function()? onSessionExpired;

  Future<bool> _refresh() async {
    final refresh = await tokens.refreshToken;
    if (refresh == null) return false;
    try {
      final res = await Dio(BaseOptions(baseUrl: AppConfig.apiUrl))
          .post('/auth/refresh', data: {'refresh_token': refresh});
      await tokens.save(res.data['access_token'] as String, res.data['refresh_token'] as String);
      return true;
    } catch (_) {
      return false;
    }
  }

  static Options get noAuth => Options(extra: {'auth': false});

  Future<T> call<T>(Future<Response<dynamic>> Function(Dio dio) request, T Function(dynamic data) parse) async {
    try {
      final res = await request(dio);
      return parse(res.data);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}
