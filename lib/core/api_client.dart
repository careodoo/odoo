import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Thin client over the Odoo `/api/v1` token API.
///
/// The base URL is the only thing to change per deployment. Auth is a Bearer
/// token stored in the OS secure storage (Keychain / Keystore) — never a cookie,
/// so it works exactly the same on a real device as in these server tests.
class ApiClient {
  ApiClient({String? baseUrl})
      : baseUrl = baseUrl ?? const String.fromEnvironment(
              'CARE_API_BASE',
              defaultValue: 'https://ecare.care-kw.com/api/v1',
            );

  final String baseUrl;
  final _storage = const FlutterSecureStorage();
  static const _tokenKey = 'care_token';

  Future<String?> get token => _storage.read(key: _tokenKey);
  Future<void> _setToken(String? t) async => t == null
      ? _storage.delete(key: _tokenKey)
      : _storage.write(key: _tokenKey, value: t);

  Future<Map<String, String>> _headers() async {
    final t = await token;
    return {
      'Content-Type': 'application/json; charset=utf-8',
      if (t != null) 'Authorization': 'Bearer $t',
    };
  }

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  /// Returns the decoded `data` payload, or throws [ApiException].
  Future<dynamic> _handle(http.Response r) async {
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      throw ApiException(r.statusCode, 'استجابة غير صالحة من الخادم');
    }
    if (r.statusCode >= 200 && r.statusCode < 300 && body is Map && body['ok'] == true) {
      return body;
    }
    final msg = (body is Map ? body['error'] : null) ?? 'خطأ (${r.statusCode})';
    throw ApiException(r.statusCode, msg.toString());
  }

  // ---- auth ----------------------------------------------------------------
  Future<Map<String, dynamic>> login(String login, String password,
      {String? device}) async {
    final r = await http.post(_u('/auth/login'),
        headers: await _headers(),
        body: jsonEncode({'login': login, 'password': password, 'device': device}));
    final body = await _handle(r) as Map;
    await _setToken(body['token'] as String?);
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  Future<void> logout() async {
    try {
      await http.post(_u('/auth/logout'), headers: await _headers());
    } finally {
      await _setToken(null);
    }
  }

  // ---- resources -----------------------------------------------------------
  Future<Map<String, dynamic>> me() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/me'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> workOrders({String? state}) async {
    final q = state != null ? '?state=$state' : '';
    final body = await _handle(
        await http.get(_u('/workorders$q'), headers: await _headers()));
    return List<dynamic>.from(body['data'] as List);
  }

  Future<Map<String, dynamic>> workOrderStart(int id) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/workorders/$id/start'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> workOrderDone(int id) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/workorders/$id/done'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> scan(String code) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/scan'),
              headers: await _headers(),
              body: jsonEncode({'code': code})))) ['data'] as Map);

  // ---- security ------------------------------------------------------------
  /// kind: incidents | patrols | keys | gatepasses
  Future<List<dynamic>> securityList(String kind) async {
    final body = await _handle(
        await http.get(_u('/security/$kind'), headers: await _headers()));
    return List<dynamic>.from(body['data'] as List);
  }

  // ---- branding (public, no token) -----------------------------------------
  Future<Map<String, dynamic>> branding() async {
    final r = await http.get(_u('/branding'),
        headers: {'Content-Type': 'application/json'});
    final body = await _handle(r) as Map;
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  // ---- client --------------------------------------------------------------
  Future<Map<String, dynamic>> clientOverview() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/overview'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientFacility(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/facility/$id'), headers: await _headers())))['data'] as Map);

  // ---- notifications -------------------------------------------------------
  Future<(List<dynamic>, int)> notifications() async {
    final body = await _handle(await http.get(_u('/notifications'), headers: await _headers()));
    return (List<dynamic>.from(body['data'] as List), (body['unread'] as int?) ?? 0);
  }

  Future<void> markNotifRead(int id) async =>
      _handle(await http.post(_u('/notifications/$id/read'), headers: await _headers()));

  Future<void> markAllNotifsRead() async =>
      _handle(await http.post(_u('/notifications/read_all'), headers: await _headers()));

  // ---- admin ---------------------------------------------------------------
  Future<Map<String, dynamic>> adminDashboard() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/admin/dashboard'), headers: await _headers())))['data'] as Map);

  // ---- supervisor ----------------------------------------------------------
  Future<Map<String, dynamic>> stats() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/stats'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> team() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/team'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> employees() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/employees'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> assignable() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/workorders/assignable'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> assign(int woId, int employeeId) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/workorders/$woId/assign'),
              headers: await _headers(),
              body: jsonEncode({'employee_id': employeeId})))) ['data'] as Map);

  Future<Map<String, dynamic>> createIncident({
    required String type,
    required String severity,
    required String description,
  }) async {
    final body = await _handle(await http.post(_u('/security/incidents'),
        headers: await _headers(),
        body: jsonEncode({'type': type, 'severity': severity, 'description': description})));
    return Map<String, dynamic>.from(body['data'] as Map);
  }
}

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}
