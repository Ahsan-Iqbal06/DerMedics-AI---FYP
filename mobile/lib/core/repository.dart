import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'models.dart';

final tokenStoreProvider = Provider((ref) => TokenStore());
final apiClientProvider = Provider((ref) => ApiClient(ref.watch(tokenStoreProvider)));
final repositoryProvider = Provider((ref) => DerMedicsRepository(ref.watch(apiClientProvider)));

class AuthResult {
  AuthResult(this.user, this.accessToken, this.refreshToken);
  final AppUser user;
  final String accessToken;
  final String refreshToken;
}

class DerMedicsRepository {
  DerMedicsRepository(this.api);
  final ApiClient api;

  AuthResult _auth(dynamic d) => AuthResult(
        AppUser.fromJson(d['user'] as Map<String, dynamic>),
        d['access_token'] as String,
        d['refresh_token'] as String,
      );

  // ---------- Auth ----------
  Future<AuthResult> login(String email, String password) => api.call(
        (dio) => dio.post('/auth/login', data: {'email': email, 'password': password}, options: ApiClient.noAuth),
        _auth,
      );

  Future<AuthResult> register({
    required String fullName,
    required String email,
    required String password,
    required String confirmPassword,
    required String country,
    required String city,
    required bool acceptTerms,
  }) =>
      api.call(
        (dio) => dio.post(
          '/auth/register',
          data: {
            'full_name': fullName,
            'email': email,
            'password': password,
            'confirm_password': confirmPassword,
            'country': country,
            'city': city,
            'accept_terms': acceptTerms,
          },
          options: ApiClient.noAuth,
        ),
        _auth,
      );

  Future<void> logout(String refreshToken) => api.call(
        (dio) => dio.post('/auth/logout', data: {'refresh_token': refreshToken}, options: ApiClient.noAuth),
        (_) {},
      );

  Future<AppUser> me() => api.call((dio) => dio.get('/auth/me'), (d) => AppUser.fromJson(d as Map<String, dynamic>));

  Future<AppUser> updateProfile({String? fullName, String? country, String? city}) => api.call(
        (dio) => dio.patch('/auth/me', data: {
          'full_name': ?fullName,
          'country': ?country,
          'city': ?city,
        }),
        (d) => AppUser.fromJson(d as Map<String, dynamic>),
      );

  Future<AppUser> uploadAvatar(Uint8List bytes, String filename) => api.call(
        (dio) => dio.post('/auth/me/avatar', data: FormData.fromMap({'image': MultipartFile.fromBytes(bytes, filename: filename)})),
        (d) => AppUser.fromJson(d as Map<String, dynamic>),
      );

  Future<AppUser> removeAvatar() =>
      api.call((dio) => dio.delete('/auth/me/avatar'), (d) => AppUser.fromJson(d as Map<String, dynamic>));

  Future<void> changePassword(String current, String next) => api.call(
        (dio) => dio.post('/auth/change-password', data: {'current_password': current, 'new_password': next}),
        (_) {},
      );

  // ---------- Dashboard ----------
  Future<Dashboard> dashboard() =>
      api.call((dio) => dio.get('/dashboard'), (d) => Dashboard.fromJson(d as Map<String, dynamic>));

  // ---------- AI pipeline ----------
  Future<Analysis> analyze({
    required Uint8List bytes,
    required String filename,
    required String bodyArea,
    required String symptoms,
  }) =>
      api.call(
        (dio) => dio.post(
          '/analysis',
          data: FormData.fromMap({
            'image': MultipartFile.fromBytes(bytes, filename: filename),
            'body_area': bodyArea,
            'symptoms': symptoms,
            'consent': 'true',
          }),
        ),
        (d) => Analysis.fromJson(d as Map<String, dynamic>),
      );

  Future<Analysis> analysis(int id) =>
      api.call((dio) => dio.get('/analysis/$id'), (d) => Analysis.fromJson(d as Map<String, dynamic>));

  // ---------- Reports ----------
  Future<Report> createReport({
    required int analysisId,
    required bool myself,
    String? name,
    int? age,
    String? relationship,
    String notes = '',
  }) =>
      api.call(
        (dio) => dio.post('/reports', data: {
          'analysis_id': analysisId,
          'subject_type': myself ? 'myself' : 'someone_else',
          if (!myself) 'subject_name': name,
          'subject_age': age,
          if (!myself) 'relationship': relationship,
          'health_notes': notes,
        }),
        (d) => Report.fromJson(d as Map<String, dynamic>),
      );

  Future<List<ReportSummary>> reports({String filter = 'all', String query = ''}) => api.call(
        (dio) => dio.get('/reports', queryParameters: {'filter': filter, 'q': query}),
        (d) => (d as List).map((e) => ReportSummary.fromJson(e as Map<String, dynamic>)).toList(),
      );

  Future<Report> report(int id) =>
      api.call((dio) => dio.get('/reports/$id'), (d) => Report.fromJson(d as Map<String, dynamic>));

  Future<void> deleteReport(int id) => api.call((dio) => dio.delete('/reports/$id'), (_) {});

  Future<Uint8List> reportPdf(int id) => api.call(
        (dio) => dio.get('/reports/$id/pdf', options: Options(responseType: ResponseType.bytes)),
        (d) => Uint8List.fromList(d as List<int>),
      );

  // ---------- Care ----------
  Future<List<Dermatologist>> dermatologists({
    String country = '',
    String city = '',
    String query = '',
    String? condition,
    double? lat,
    double? lng,
  }) =>
      api.call(
        (dio) => dio.get('/dermatologists', queryParameters: {
          'country': country,
          'city': city,
          'q': query,
          'condition': ?condition,
          'lat': ?lat,
          'lng': ?lng,
        }),
        (d) => (d as List).map((e) => Dermatologist.fromJson(e as Map<String, dynamic>)).toList(),
      );
}
