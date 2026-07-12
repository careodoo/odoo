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
  Future<void> setToken(String? t) => _setToken(t); // public (for impersonation restore)

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
      throw ApiException(r.statusCode, 'استجابة غير صالحة من الخادم (${r.statusCode})');
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

  Future<Map<String, dynamic>> workOrderDetail(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/workorders/$id/detail'), headers: await _headers())))['data'] as Map);

  Future<void> workOrderVerify(int id) async =>
      _handle(await http.post(_u('/workorders/$id/verify'), headers: await _headers()));

  Future<void> workOrderReject(int id, String reason) async =>
      _handle(await http.post(_u('/workorders/$id/reject'),
          headers: await _headers(), body: jsonEncode({'reason': reason})));

  Future<Map<String, dynamic>> createWorkOrder(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/workorders/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> servicesCatalog() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/services'), headers: await _headers())))['data'] as List);

  Future<void> workOrderPhoto(int id, String base64Data, String filename, String mediaType) async =>
      _handle(await http.post(_u('/workorders/$id/photo'),
          headers: await _headers(),
          body: jsonEncode({'data': base64Data, 'filename': filename, 'media_type': mediaType})));

  Future<void> workOrderNote(int id, String note) async =>
      _handle(await http.post(_u('/workorders/$id/note'),
          headers: await _headers(), body: jsonEncode({'note': note})));

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

  Future<Map<String, dynamic>> clientAnalytics() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/analytics'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientFacility(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/facility/$id'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> clientTeam() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/team'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientWorkOrders({String state = 'all'}) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/workorders?state=$state'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientEmployee(int id, {String period = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/employee/$id?period=$period'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientActivity() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/activity'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientStructure({String period = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/structure?period=$period'), headers: await _headers())))['data'] as Map);

  // ---- per-service data ----------------------------------------------------
  /// path: cleaning/audits | agri/zones | facade/permits
  Future<List<dynamic>> serviceList(String path) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/service/$path'), headers: await _headers())))['data'] as List);

  // ---- occupancy (3D building) ---------------------------------------------
  Future<List<dynamic>> facilities() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/facilities'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> facilityOccupancy(int fid) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/facility/$fid/occupancy'), headers: await _headers())))['data'] as Map);

  // ---- shifts (geofenced) --------------------------------------------------
  Future<Map<String, dynamic>> shiftCurrent() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/shift/current'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> shiftOpen(double lat, double lng) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/shift/open'),
              headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})))) ['data'] as Map);

  Future<Map<String, dynamic>> shiftClose(double lat, double lng) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/shift/close'),
              headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})))) ['data'] as Map);

  Future<List<dynamic>> shiftActive() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/shift/active'), headers: await _headers())))['data'] as List);

  // ---- appraisal -----------------------------------------------------------
  Future<Map<String, dynamic>> appraisalMe() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/appraisal/me'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> appraisalTeam() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/appraisal/team'), headers: await _headers())))['data'] as List);

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
  /// Test-only: list users to impersonate (admin).
  Future<List<dynamic>> adminUsers() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/admin/users'), headers: await _headers())))['data'] as List);

  /// Switch the session to another user (admin). Sets the returned token.
  Future<Map<String, dynamic>> impersonate(String login) async {
    final body = await _handle(await http.post(_u('/admin/impersonate'),
        headers: await _headers(), body: jsonEncode({'login': login}))) as Map;
    await _setToken(body['token'] as String?);
    return Map<String, dynamic>.from(body['data'] as Map);
  }

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

  Future<Map<String, dynamic>> securityDashboard() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/security/dashboard'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> securityData(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/security/data/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> securityRecord(String kind, int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/security/record/$kind/$id'), headers: await _headers())))['data'] as Map);

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
