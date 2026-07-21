import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'i18n.dart';

/// Thin client over the Odoo `/api/v1` token API.
///
/// The base URL is the only thing to change per deployment. Auth is a Bearer
/// token stored in the OS secure storage (Keychain / Keystore) — never a cookie,
/// so it works exactly the same on a real device as in these server tests.

/// Every request gets a deadline.
///
/// package:http has no default timeout, so a request that stalls on a flaky
/// mobile network never completes and never throws — the screen keeps its
/// spinner forever and the user reports "the app does not load". A dead
/// request must fail loudly enough for the UI to show something.
class _TimeoutClient extends http.BaseClient {
  _TimeoutClient(this._inner, this._limit);
  final http.Client _inner;
  final Duration _limit;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      _inner.send(request).timeout(_limit);
}

/// 30s: long enough for a slow 3G round trip carrying a big work-order list,
/// short enough that a stalled request surfaces while the user is still
/// looking at the screen.
final http.Client _net = _TimeoutClient(http.Client(), const Duration(seconds: 30));

class ApiClient {
  ApiClient({String? baseUrl})
      : baseUrl = baseUrl ?? const String.fromEnvironment(
              'CARE_API_BASE',
              defaultValue: 'https://ecare.care-kw.com/api/v1',
            );

  final String baseUrl;
  final _storage = const FlutterSecureStorage();

  /// Reading the token can throw, and losing the token is not an error worth
  /// blocking a login for.
  ///
  /// The value is encrypted with a key held in the Android Keystore. Keys are
  /// never included in a backup, but the encrypted preferences ARE — so after
  /// a restore, or some OEM update paths, the ciphertext is present and the
  /// key that opens it is gone. Every read then throws
  /// `BadPaddingException: BAD_DECRYPT` and the app cannot even reach the
  /// login request. A stale token we cannot decrypt is worth exactly nothing,
  /// so drop it and carry on as a logged-out app.
  Future<String?> _readToken() async {
    try {
      return await _storage.read(key: _tokenKey);
    } catch (_) {
      try {
        await _storage.deleteAll();
      } catch (_) {/* nothing left to salvage */}
      return null;
    }
  }
  static const _tokenKey = 'care_token';

  Future<String?> get token => _readToken();
  Future<void> _setToken(String? t) async => t == null
      ? _storage.delete(key: _tokenKey).catchError((_) {})
      : _storage.write(key: _tokenKey, value: t).catchError((_) {});
  Future<void> setToken(String? t) => _setToken(t); // public (for impersonation restore)

  Future<Map<String, String>> _headers() async {
    final t = await token;
    return {
      'Content-Type': 'application/json; charset=utf-8',
      // Drive translated record values (facility/location names…) by the
      // language the user picked in the app.
      'X-Lang': gLang,
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
    // Whatever the keyboard did to it, an address with stray spaces or a
    // capitalised domain is the same account — one real login arrived as
    // "rajab. ibrahim.@Care-kw.com" and was rejected as a wrong password.
    // Normalise here so no screen has to remember to.
    login = login.trim().replaceAll(' ', '');
    if (login.contains('@')) login = login.toLowerCase();
    final r = await _net.post(_u('/auth/login'),
        headers: await _headers(),
        body: jsonEncode({'login': login, 'password': password, 'device': device}));
    final body = await _handle(r) as Map;
    await _setToken(body['token'] as String?);
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  /// Public self-registration → CARE 2 CARE customer; auto-logs in.
  Future<Map<String, dynamic>> signup({required String name, String? email, String? phone, required String password, String? device}) async {
    final r = await _net.post(_u('/auth/signup'),
        headers: await _headers(),
        body: jsonEncode({'name': name, 'email': email, 'phone': phone, 'password': password, 'device': device}));
    final body = await _handle(r) as Map;
    await _setToken(body['token'] as String?);
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  Future<void> logout() async {
    try {
      await _net.post(_u('/auth/logout'), headers: await _headers());
    } finally {
      await _setToken(null);
    }
  }

  // ---- resources -----------------------------------------------------------
  Future<Map<String, dynamic>> me() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/me'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> workOrders({String? state}) async {
    final q = state != null ? '?state=$state' : '';
    final body = await _handle(
        await _net.get(_u('/workorders$q'), headers: await _headers()));
    return List<dynamic>.from(body['data'] as List);
  }

  Future<Map<String, dynamic>> workOrderDetail(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/workorders/$id/detail'), headers: await _headers())))['data'] as Map);

  Future<void> workOrderVerify(int id) async =>
      _handle(await _net.post(_u('/workorders/$id/verify'), headers: await _headers()));

  Future<void> workOrderReject(int id, String reason) async =>
      _handle(await _net.post(_u('/workorders/$id/reject'),
          headers: await _headers(), body: jsonEncode({'reason': reason})));

  Future<Map<String, dynamic>> createWorkOrder(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/workorders/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> servicesCatalog() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/services'), headers: await _headers())))['data'] as List);

  /// Options for the client's "new work order" form (facilities+locations,
  /// services, teams, workers, priorities).
  Future<Map<String, dynamic>> clientWorkorderOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/workorder/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientWorkorderCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/workorder/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> workOrderPhoto(int id, String base64Data, String filename, String mediaType) async =>
      _handle(await _net.post(_u('/workorders/$id/photo'),
          headers: await _headers(),
          body: jsonEncode({'data': base64Data, 'filename': filename, 'media_type': mediaType})));

  Future<void> workOrderNote(int id, String note) async =>
      _handle(await _net.post(_u('/workorders/$id/note'),
          headers: await _headers(), body: jsonEncode({'note': note})));

  Future<Map<String, dynamic>> workOrderStart(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/workorders/$id/start'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> workOrderDone(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/workorders/$id/done'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> scan(String code) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/scan'),
              headers: await _headers(),
              body: jsonEncode({'code': code})))) ['data'] as Map);

  // ---- security ------------------------------------------------------------
  /// kind: incidents | patrols | keys | gatepasses
  Future<List<dynamic>> securityList(String kind) async {
    final body = await _handle(
        await _net.get(_u('/security/$kind'), headers: await _headers()));
    return List<dynamic>.from(body['data'] as List);
  }

  // ---- branding (public, no token) -----------------------------------------
  Future<Map<String, dynamic>> branding() async {
    final r = await _net.get(_u('/branding'),
        headers: {'Content-Type': 'application/json'});
    final body = await _handle(r) as Map;
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  // ---- client --------------------------------------------------------------
  Future<Map<String, dynamic>> clientOverview() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/overview'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientAnalytics({
    String period = 'month', String serviceType = 'all', String priority = 'all',
    String state = 'all', int? facilityId, int? employeeId,
  }) async {
    final p = <String, String>{'period': period};
    if (serviceType != 'all') p['service_type'] = serviceType;
    if (priority != 'all') p['priority'] = priority;
    if (state != 'all') p['state'] = state;
    if (facilityId != null) p['facility_id'] = '$facilityId';
    if (employeeId != null) p['employee_id'] = '$employeeId';
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return Map<String, dynamic>.from((await _handle(
        await _net.get(_u('/client/analytics?$qs'), headers: await _headers())))['data'] as Map);
  }

  /// Everything one building is, across every service.
  Future<Map<String, dynamic>> facilityInsight(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/facility/$id/insight'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientFacility(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/facility/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientLocation(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/location/$id'), headers: await _headers())))['data'] as Map);

  // ---- record-name translations --------------------------------------------
  Future<List<dynamic>> i18nLanguages() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/i18n/languages'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> i18nGet(String kind, int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/i18n/get?kind=$kind&id=$id'), headers: await _headers())))['data'] as Map);

  Future<void> i18nSet(String kind, int id, Map<String, String> values) async =>
      _handle(await _net.post(_u('/client/i18n/set'), headers: await _headers(),
          body: jsonEncode({'kind': kind, 'id': id, 'values': values})));

  /// Teams as service-grouped blocks with their own attendance/workload stats.
  Future<Map<String, dynamic>> clientTeams() async =>
      Map<String, dynamic>.from((await _handle(
          await _net.get(_u('/client/teams'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> clientTeam() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/team'), headers: await _headers())))['data'] as List);

  /// Work orders plus the stats and facets for the whole filtered set (not
  /// just the page shown) — see /client/workorders.
  Future<Map<String, dynamic>> clientWorkOrders({
    String state = 'all',
    String period = 'all',
    String? serviceType,
    String? priority,
    int? employeeId,
    int? facilityId,
    String? q,
  }) async {
    final p = <String, String>{'state': state, 'period': period};
    if (serviceType != null && serviceType != 'all') p['service_type'] = serviceType;
    if (priority != null && priority != 'all') p['priority'] = priority;
    if (employeeId != null) p['employee_id'] = '$employeeId';
    if (facilityId != null) p['facility_id'] = '$facilityId';
    if (q != null && q.trim().isNotEmpty) p['q'] = q.trim();
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return Map<String, dynamic>.from((await _handle(
        await _net.get(_u('/client/workorders?$qs'), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> workerOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/worker/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> createWorker(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/worker/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> clientContracts() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/contracts'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientRequests() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/requests'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientObservations() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/observations'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> createObservation(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/observation/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> observationToWorkOrder(int id) async =>
      _handle(await _net.post(_u('/client/observation/$id/workorder'), headers: await _headers()));

  Future<Map<String, dynamic>> observationDetail(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/observation/$id'), headers: await _headers())))['data'] as Map);

  Future<void> observationCancel(int id) async =>
      _handle(await _net.post(_u('/client/observation/$id/cancel'), headers: await _headers()));

  Future<void> observationAddMedia(int id, List<Map<String, dynamic>> media) async =>
      _handle(await _net.post(_u('/client/observation/$id/media'),
          headers: await _headers(), body: jsonEncode({'media': media})));

  Future<List<dynamic>> clientPpm() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/ppm'), headers: await _headers())))['data'] as List);

  /// Categories and items a collection request can point at.
  Future<Map<String, dynamic>> wasteCatalogue() async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/waste/catalogue'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> createRequest(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/request/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<Map<String, dynamic>> requestConvert(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/request/$id/convert'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> requestCancel(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/request/$id/cancel'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> servicesList() async {
    try {
      return List<dynamic>.from((await _handle(
              await _net.get(_u('/services'), headers: await _headers())))['data'] as List);
    } catch (_) { return const []; }
  }

  Future<Map<String, dynamic>> manageOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/manage/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> manageUpsert(String kind, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/manage/$kind'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> manageDelete(String kind, int id) async =>
      _handle(await _net.post(_u('/client/manage/$kind/$id/delete'), headers: await _headers()));

  /// Absolute URL for a contract copy (needs the Bearer token to fetch).
  String contractCopyUrl(String path) => path.startsWith('http') ? path : '$baseUrl$path';

  Future<Map<String, dynamic>> clientEmployee(int id, {String period = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/employee/$id?period=$period'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientActivity({
    String period = 'all', String kind = 'all', int? employeeId, int? facilityId,
  }) async {
    final p = <String, String>{'period': period, 'kind': kind};
    if (employeeId != null) p['employee_id'] = '$employeeId';
    if (facilityId != null) p['facility_id'] = '$facilityId';
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return Map<String, dynamic>.from((await _handle(
        await _net.get(_u('/client/activity?$qs'), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> clientStructure({String period = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/structure?period=$period'), headers: await _headers())))['data'] as Map);

  // ---- per-service data ----------------------------------------------------
  /// path: cleaning/audits | agri/zones | facade/permits
  Future<List<dynamic>> serviceList(String path) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/service/$path'), headers: await _headers())))['data'] as List);

  // ---- occupancy (3D building) ---------------------------------------------
  Future<List<dynamic>> facilities() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/facilities'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> facilityOccupancy(int fid) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/facility/$fid/occupancy'), headers: await _headers())))['data'] as Map);

  // ---- shifts (geofenced) --------------------------------------------------
  Future<Map<String, dynamic>> shiftCurrent() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/shift/current'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> shiftOpen(double lat, double lng) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/shift/open'),
              headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})))) ['data'] as Map);

  Future<Map<String, dynamic>> shiftClose(double lat, double lng) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/shift/close'),
              headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})))) ['data'] as Map);

  Future<List<dynamic>> shiftActive() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/shift/active'), headers: await _headers())))['data'] as List);

  // ---- appraisal -----------------------------------------------------------
  Future<Map<String, dynamic>> appraisalMe() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/appraisal/me'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> appraisalTeam() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/appraisal/team'), headers: await _headers())))['data'] as List);

  // ---- notifications -------------------------------------------------------
  Future<(List<dynamic>, int)> notifications() async {
    final body = await _handle(await _net.get(_u('/notifications'), headers: await _headers()));
    return (List<dynamic>.from(body['data'] as List), (body['unread'] as int?) ?? 0);
  }

  Future<void> markNotifRead(int id) async =>
      _handle(await _net.post(_u('/notifications/$id/read'), headers: await _headers()));

  Future<void> markAllNotifsRead() async =>
      _handle(await _net.post(_u('/notifications/read_all'), headers: await _headers()));

  // ---- admin ---------------------------------------------------------------
  /// Test-only: list users to impersonate (admin).
  Future<List<dynamic>> adminUsers() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/admin/users'), headers: await _headers())))['data'] as List);

  /// Switch the session to another user (admin). Sets the returned token.
  Future<Map<String, dynamic>> impersonate(String login) async {
    final body = await _handle(await _net.post(_u('/admin/impersonate'),
        headers: await _headers(), body: jsonEncode({'login': login}))) as Map;
    await _setToken(body['token'] as String?);
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  Future<Map<String, dynamic>> adminDashboard() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/admin/dashboard'), headers: await _headers())))['data'] as Map);

  // ---- supervisor ----------------------------------------------------------
  Future<Map<String, dynamic>> stats() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/stats'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> team() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/team'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> employees() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/employees'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> assignable() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/workorders/assignable'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> assign(int woId, int employeeId) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/workorders/$woId/assign'),
              headers: await _headers(),
              body: jsonEncode({'employee_id': employeeId})))) ['data'] as Map);

  Future<Map<String, dynamic>> securityDashboard() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/security/dashboard'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> securityData(String kind) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/security/data/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> securityRecord(String kind, int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/security/record/$kind/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> createIncident({
    required String type,
    required String severity,
    required String description,
  }) async {
    final body = await _handle(await _net.post(_u('/security/incidents'),
        headers: await _headers(),
        body: jsonEncode({'type': type, 'severity': severity, 'description': description})));
    return Map<String, dynamic>.from(body['data'] as Map);
  }

  // ---- contracted services (segmented menu) --------------------------------
  Future<List<dynamic>> clientServices() async {
    try {
      final body = await _handle(await _net.get(_u('/client/services'), headers: await _headers()));
      return List<dynamic>.from((body['data'] as Map)['services'] as List);
    } catch (_) { return const []; }
  }

  // ---- shop: products / favorites / cart → order ---------------------------
  Future<Map<String, dynamic>> clientProducts({String? q, int? categoryId, bool favorites = false}) async {
    final params = <String>[];
    if (q != null && q.isNotEmpty) params.add('q=${Uri.encodeComponent(q)}');
    if (categoryId != null) params.add('category_id=$categoryId');
    if (favorites) params.add('favorites=1');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    return Map<String, dynamic>.from((await _handle(
            await _net.get(_u('/client/products$qs'), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> clientProduct(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/product/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> favoriteToggle(int productId) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/favorite/toggle'),
              headers: await _headers(), body: jsonEncode({'product_id': productId})))) ['data'] as Map);

  Future<Map<String, dynamic>> clientFavorites() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/favorites'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> orderCreate(
    List<Map<String, dynamic>> lines, {
    int? addressId,
    String? deliveryDate,
    String? note,
  }) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/order/create'),
          headers: await _headers(),
          body: jsonEncode({
            'lines': lines,
            if (addressId != null) 'address_id': addressId,
            if (deliveryDate != null) 'delivery_date': deliveryDate,
            if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
          })))) ['data'] as Map);

  /// Addresses this client may have an order delivered to.
  Future<List<dynamic>> clientAddresses() async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/client/addresses'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientOrders({String? period, String? dateFrom, String? dateTo}) async {
    final p = <String, String>{};
    if (period != null) p['period'] = period;
    if (dateFrom != null) p['date_from'] = dateFrom;
    if (dateTo != null) p['date_to'] = dateTo;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return List<dynamic>.from((await _handle(await _net.get(
        _u('/client/orders${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as List);
  }

  /// Query string (period/date_from/date_to) for the orders PDF & Excel routes.
  String ordersReportQuery({String? period, String? dateFrom, String? dateTo}) {
    final p = <String, String>{};
    if (period != null) p['period'] = period;
    if (dateFrom != null) p['date_from'] = dateFrom;
    if (dateTo != null) p['date_to'] = dateTo;
    return p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
  }

  Future<Map<String, dynamic>> clientOrder(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/order/$id'), headers: await _headers())))['data'] as Map);

  Future<void> orderCancel(int id) async =>
      _handle(await _net.post(_u('/client/order/$id/cancel'), headers: await _headers()));

  // ---- invoices ------------------------------------------------------------
  Future<Map<String, dynamic>> clientInvoices() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/invoices'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientInvoice(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/invoice/$id'), headers: await _headers())))['data'] as Map);

  Future<void> invoiceApprove(int id, String comment) async =>
      _handle(await _net.post(_u('/client/invoice/$id/approve'),
          headers: await _headers(), body: jsonEncode({'comment': comment})));

  Future<void> invoiceReject(int id, String comment) async =>
      _handle(await _net.post(_u('/client/invoice/$id/reject'),
          headers: await _headers(), body: jsonEncode({'comment': comment})));

  // ---- client-scoped assets register ---------------------------------------
  Future<Map<String, dynamic>> clientAssetsSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/assets/summary'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> clientAssets({String? category, String? status, String? q}) async {
    final p = <String, String>{};
    if (category != null && category != 'all') p['category'] = category;
    if (status != null && status != 'all') p['status'] = status;
    if (q != null && q.isNotEmpty) p['q'] = q;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return List<dynamic>.from((await _handle(await _net.get(
        _u('/client/assets${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> clientAsset(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/asset/$id'), headers: await _headers())))['data'] as Map);

  // ---- maintenance service --------------------------------------------------
  /// Minimum supported build, update message and store link (no auth needed).
  Future<Map<String, dynamic>> appConfig() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/app/config'))))['data'] as Map);

  /// What a scanned code actually is, before anyone commits to issuing it.
  Future<Map<String, dynamic>> invLookup(String code, {int? storeId}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/inv/lookup?code=${Uri.encodeQueryComponent(code)}'
                  '${storeId != null ? '&store_id=$storeId' : ''}'),
              headers: await _headers())))['data'] as Map);

  /// Destinations with their QR code and NFC tag.
  Future<Map<String, dynamic>> invLocations() async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/inv/locations'), headers: await _headers())))['data'] as Map);

  /// What the plate already knows — visits, owner, VIP or blocked, notes.
  Future<Map<String, dynamic>> valetPlate(String plate) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/valet/plate?plate=${Uri.encodeQueryComponent(plate)}'),
              headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> valetDrivers({int? facilityId}) async =>
      ((await _handle(await _net.get(
              _u('/valet/drivers${facilityId != null ? '?facility_id=$facilityId' : ''}'),
              headers: await _headers())))['data'] as Map)['drivers'] as List;

  Future<Map<String, dynamic>> valetPark(int ticketId, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/valet/ticket/$ticketId/park'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  /// One incident with its evidence, updates, location and stream.
  Future<Map<String, dynamic>> incidentDetail(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/security/incident/$id'), headers: await _headers())))['data'] as Map);

  Future<void> incidentMedia(int id, Map<String, dynamic> body) async =>
      _handle(await _net.post(_u('/security/incident/$id/media'),
          headers: await _headers(), body: jsonEncode(body)));

  Future<void> incidentUpdate(int id, String body) async =>
      _handle(await _net.post(_u('/security/incident/$id/update'),
          headers: await _headers(), body: jsonEncode({'body': body})));

  Future<void> incidentLocate(int id, double lat, double lng) async =>
      _handle(await _net.post(_u('/security/incident/$id/locate'),
          headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})));

  Future<Map<String, dynamic>> incidentToWorkorder(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/security/incident/$id/to_workorder'),
              headers: await _headers())))['data'] as Map);

  // ---- hospitality pantry ---------------------------------------------------
  /// Supplies with their balance in servings, plus recent purchases.
  Future<Map<String, dynamic>> hospStock() async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/hosp/stock'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> hospPurchaseCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/purchase/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> hospPurchaseAct(int id, String act) async =>
      _handle(await _net.post(_u('/hosp/purchase/$id/$act'),
          headers: await _headers()));

  /// Where I am served — set once, changeable unless the client locked it.
  Future<void> hospSetPlace(Map<String, dynamic> body) async =>
      _handle(await _net.post(_u('/hosp/place'),
          headers: await _headers(), body: jsonEncode(body)));

  // ---- service registry (the 39 sections, shared with the web portal) --------
  /// What each service is made of. The backend declares it once, so a section
  /// added there appears in the app and the portal without either being edited.
  Future<Map<String, dynamic>> svcRegistry() async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/svc'), headers: await _headers())))['data'] as Map);

  /// One section's records, plus whether this client may add or cancel here.
  Future<Map<String, dynamic>> svcSection(String code, String key, {int page = 1}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/svc/$code/$key?page=$page'),
              headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> svcAdd(String code, String key, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/svc/$code/$key/add'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> svcCancel(String code, String key, int id) async =>
      _handle(await _net.post(_u('/client/svc/$code/$key/$id/cancel'),
          headers: await _headers()));

  // ---- valet parking ---------------------------------------------------------
  /// One service's slice of the client's work — the per-service screens all
  /// read the same enriched work-order envelope, filtered by service type.
  Future<Map<String, dynamic>> clientServiceBoard(String serviceType, {String state = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/workorders?state=$state&service_type=$serviceType'),
              headers: await _headers())))['data'] as Map);

  // ---- hospitality ----
  Future<Map<String, dynamic>> hospMenu() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/hosp/menu'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> hospMyOrders() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/hosp/orders'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> hospCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/order/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<Map<String, dynamic>> hospFavOrder(int id, {String? room}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/favorite/$id/order'),
              headers: await _headers(),
              body: jsonEncode({if (room != null) 'room': room}))))['data'] as Map);

  Future<Map<String, dynamic>> hospRate(int id, int rating, {String? note}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/order/$id/rate'),
              headers: await _headers(),
              body: jsonEncode({'rating': '$rating', if (note != null) 'note': note}))))['data'] as Map);

  Future<Map<String, dynamic>> hospCancel(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/order/$id/cancel'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> hospKitchen() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/hosp/kitchen'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> hospKitchenAct(int id, String act) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/hosp/kitchen/$id/$act'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> valetBoard() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/valet/board'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> valetTickets({String? state, String? q}) async {
    final p = <String, String>{};
    if (state != null) p['state'] = state;
    if (q != null && q.isNotEmpty) p['q'] = q;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return List<dynamic>.from((await _handle(await _net.get(
        _u('/valet/tickets${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> valetCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/valet/ticket/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  /// action: park | request | deliver | cancel
  Future<Map<String, dynamic>> valetAction(int id, String action, {Map<String, dynamic>? body}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/valet/ticket/$id/$action'), headers: await _headers(),
              body: jsonEncode(body ?? {}))))['data'] as Map);

  Future<Map<String, dynamic>> valetShift(String action, {int? facilityId}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/valet/shift/$action'), headers: await _headers(),
              body: jsonEncode({if (facilityId != null) 'facility_id': facilityId}))))['data'] as Map);

  // ---- support desk (Odoo Helpdesk) ------------------------------------------
  Future<Map<String, dynamic>> supportTickets() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/support/tickets'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> supportTicket(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/support/ticket/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> supportCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/support/ticket/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<Map<String, dynamic>> supportReply(int id, String body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/support/ticket/$id/reply'), headers: await _headers(),
              body: jsonEncode({'body': body}))))['data'] as Map);

  // ---- material issue policy (client / admin) --------------------------------
  Future<Map<String, dynamic>> invPolicy({int? storeId}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/client/inv/policy${storeId != null ? '?store_id=$storeId' : ''}'),
              headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> invPolicySetItem(int itemId,
          {bool? allow, double? maxQty, List<int>? serviceIds}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/inv/policy/item/$itemId'), headers: await _headers(),
              body: jsonEncode({
                if (allow != null) 'allow_worker_issue': allow,
                if (maxQty != null) 'max_issue_qty': maxQty,
                if (serviceIds != null) 'allowed_service_ids': serviceIds,
              }))))['data'] as Map);

  Future<Map<String, dynamic>> invPolicySetStore(int storeId, bool allow) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/inv/policy/store/$storeId'), headers: await _headers(),
              body: jsonEncode({'worker_issue_allowed': allow}))))['data'] as Map);

  /// One cleaning audit in full, with its checklist item by item.
  Future<Map<String, dynamic>> cleaningAudit(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/service/cleaning/audit/$id'), headers: await _headers())))['data'] as Map);

  // ---- NFC tag provisioning -------------------------------------------------
  Future<Map<String, dynamic>> nfcLocations({int? facilityId, String? state, String? q}) async {
    final p = <String, String>{};
    if (facilityId != null) p['facility_id'] = '$facilityId';
    if (state != null && state != 'all') p['state'] = state;
    if (q != null && q.isNotEmpty) p['q'] = q;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return Map<String, dynamic>.from((await _handle(await _net.get(
        _u('/nfc/locations${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as Map);
  }

  /// Bind a physical tag (its hardware uid) to a location and activate it.
  Future<Map<String, dynamic>> nfcProvision(int locationId, String uid,
          {bool written = false, bool force = false, String? note}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/nfc/location/$locationId/provision'), headers: await _headers(),
              body: jsonEncode({'uid': uid, 'written': written, 'force': force, if (note != null) 'note': note}))))['data'] as Map);

  /// action: 'disable' | 'enable' | 'revoke'
  Future<Map<String, dynamic>> nfcAction(int locationId, String action) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/nfc/location/$locationId/$action'), headers: await _headers())))['data'] as Map);

  /// Tap any tag and find out which location it belongs to.
  Future<Map<String, dynamic>> nfcVerify(String value) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/nfc/verify'),
              headers: await _headers(), body: jsonEncode({'value': value}))))['data'] as Map);

  // ---- directory + chat -----------------------------------------------------
  Future<List<dynamic>> directory({String? q}) async {
    final path = '/directory${q != null && q.isNotEmpty ? '?q=${Uri.encodeQueryComponent(q)}' : ''}';
    return List<dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<List<dynamic>> chatThreads() async =>
      List<dynamic>.from((await _handle(await _net.get(_u('/chat/threads'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> chatMessages(int peer) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(_u('/chat/$peer/messages'), headers: await _headers())))['data'] as Map);

  /// Send a chat message: text, a photo/video, or both.
  Future<Map<String, dynamic>> chatSend(int peer, String body,
          {String? data, String? mediaType, String? name}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/chat/$peer/send'),
              headers: await _headers(),
              body: jsonEncode({
                'body': body,
                if (data != null) 'data': data,
                if (mediaType != null) 'media_type': mediaType,
                if (name != null) 'name': name,
              }))))['data'] as Map);

  Future<int> chatUnread() async =>
      ((await _handle(await _net.get(_u('/chat/unread'), headers: await _headers())))['data'] as Map)['unread'] as int? ?? 0;

  /// The worker's complete personal file (identity, assignment, documents,
  /// accommodation, attendance) honouring the app-settings visibility switches.
  Future<Map<String, dynamic>> meProfile() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/me/profile'), headers: await _headers())))['data'] as Map);

  /// The quality inspector's console: inspected teams/facilities, observation
  /// stats, severity breakdown, recent notes and the data the quick-note needs.
  Future<Map<String, dynamic>> meQuality({String period = 'month'}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/me/quality?period=$period'), headers: await _headers())))['data'] as Map);

  /// The supervisor's scope: supervised teams (service/facility/client/project),
  /// per-member load & achievements, team aggregate, and the quality queue.
  Future<Map<String, dynamic>> meSupervisor({String period = 'month'}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/me/supervisor?period=$period'), headers: await _headers())))['data'] as Map);

  Future<void> observationAssign(int id, int employeeId) async =>
      _handle(await _net.post(_u('/client/observation/$id/assign'),
          headers: await _headers(), body: jsonEncode({'employee_id': employeeId})));

  Future<Map<String, dynamic>> meAchievements({String period = 'month'}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/me/achievements?period=$period'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> maintSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/summary'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> maintFaults({String? state, int? departmentId, String? q}) async {
    final p = <String, String>{};
    if (state != null && state != 'all') p['state'] = state;
    if (departmentId != null) p['department_id'] = '$departmentId';
    if (q != null && q.isNotEmpty) p['q'] = q;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return List<dynamic>.from((await _handle(await _net.get(
        _u('/client/maint/faults${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> maintFault(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/fault/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> maintFaultCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/maint/fault/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> maintFaultAction(int id, String action) async =>
      _handle(await _net.post(_u('/client/maint/fault/$id/$action'), headers: await _headers()));

  Future<List<dynamic>> maintInspections() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/inspections'), headers: await _headers())))['data'] as List);

  Future<void> maintInspectionCreate(Map<String, dynamic> body) async =>
      _handle(await _net.post(_u('/client/maint/inspection/create'), headers: await _headers(), body: jsonEncode(body)));

  Future<void> maintInspectionDone(int id, String result) async =>
      _handle(await _net.post(_u('/client/maint/inspection/$id/done'), headers: await _headers(), body: jsonEncode({'result': result})));

  Future<List<dynamic>> maintParts() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/parts'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> maintDepartments() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/departments'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> maintOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/maint/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientAssetOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/asset/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientAssetCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/asset/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<Map<String, dynamic>> clientAssetUpdate(int id, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/asset/$id/update'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> clientAssetDelete(int id) async =>
      _handle(await _net.post(_u('/client/asset/$id/delete'), headers: await _headers()));

  Future<Map<String, dynamic>> clientScheduleOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/schedule/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientScheduleCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/schedule/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<Map<String, dynamic>> clientScheduleDetail(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/schedule/$id'), headers: await _headers())))['data'] as Map);

  /// action: 'pause' | 'resume' | 'stop' | 'reactivate'. For 'pause', optionally
  /// pass pauseUntil (YYYY-MM-DD) to auto-resume, and a reason.
  Future<Map<String, dynamic>> scheduleAction(int id, String action, {String? pauseUntil, String? reason}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/schedule/$id/$action'), headers: await _headers(),
              body: jsonEncode({if (pauseUntil != null) 'pause_until': pauseUntil, if (reason != null) 'reason': reason}))))['data'] as Map);

  Future<List<dynamic>> clientSchedules() async =>
      List<dynamic>.from(((await _handle(
              await _net.get(_u('/client/schedules'), headers: await _headers())))['data']
          as Map)['schedules'] as List);

  Future<Map<String, dynamic>> clientAttendanceData({
    String period = 'all', int? employeeId, int? facilityId,
  }) async {
    final p = <String, String>{'period': period};
    if (employeeId != null) p['employee_id'] = '$employeeId';
    if (facilityId != null) p['facility_id'] = '$facilityId';
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return Map<String, dynamic>.from((await _handle(
        await _net.get(_u('/client/attendance?$qs'), headers: await _headers())))['data'] as Map);
  }

  /// Per-service client settings (notifications, weekly report, thresholds).
  Future<List<dynamic>> serviceSettings() async =>
      ((await _handle(await _net.get(
              _u('/client/service-settings'), headers: await _headers())))['data'] as Map)['services'] as List;

  Future<void> saveServiceSetting(String code, Map<String, dynamic> prefs) async =>
      _handle(await _net.post(_u('/client/service-settings'),
          headers: await _headers(),
          body: jsonEncode({'service_code': code, 'prefs': prefs})));

  /// Material-handling jobs for my sites, with movement stats.
  Future<Map<String, dynamic>> handlingJobs({String? state}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
          _u('/client/handling/jobs${state != null ? '?state=$state' : ''}'),
          headers: await _headers())))['data'] as Map);

  /// Disinfection rounds for my sites + the workers/teams I can assign them to.
  Future<Map<String, dynamic>> disinfectRounds({String? state}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
          _u('/client/disinfect/rounds${state != null ? '?state=$state' : ''}'),
          headers: await _headers())))['data'] as Map);

  /// Assign a round to a worker and/or team, with an optional planned time.
  Future<Map<String, dynamic>> disinfectAssign(int id,
          {int? employeeId, int? teamId, String? plannedAt}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
          _u('/client/disinfect/$id/assign'),
          headers: await _headers(),
          body: jsonEncode({
            if (employeeId != null) 'employee_id': employeeId,
            if (teamId != null) 'team_id': teamId,
            if (plannedAt != null) 'planned_at': plannedAt,
          }))))['data'] as Map);

  /// Am I currently checked in? (drives the self-punch button).
  Future<Map<String, dynamic>> attendanceStatus() async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
          _u('/client/attendance/status'), headers: await _headers())))['data'] as Map);

  /// Self check-in / check-out — toggles like a fingerprint punch.
  Future<Map<String, dynamic>> attendancePunch({double? lat, double? lng}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
          _u('/client/attendance/punch'),
          headers: await _headers(),
          body: jsonEncode({if (lat != null) 'lat': lat, if (lng != null) 'lng': lng}))))['data'] as Map);

  /// Every attendance record for one worker on this client's sites.
  Future<Map<String, dynamic>> clientEmployeeAttendance(int eid, {String period = 'all'}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
          _u('/client/employee/$eid/attendance?period=$period'),
          headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> notifyOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/notify/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> notifySend(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/notify/send'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> notifySent() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/notify/sent'), headers: await _headers())))['data'] as List);

  /// How many recipients the current audience selection resolves to.
  Future<int> notifyPreview(Map<String, dynamic> body) async =>
      ((Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/notify/preview'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map))['count'] ?? 0) as int;

  Future<List<dynamic>> notifyScheduled() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/notify/scheduled'), headers: await _headers())))['data'] as List);

  Future<void> notifyScheduledCancel(int id) async =>
      _handle(await _net.post(_u('/client/notify/scheduled/cancel'),
          headers: await _headers(), body: jsonEncode({'id': id})));

  // ---- client-scoped security suite ----------------------------------------
  Future<Map<String, dynamic>> clientSecuritySummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/security/summary'), headers: await _headers())))['data'] as Map);

  /// kind: incidents | patrols | gatepasses | visitors | inspections | guards | keys
  Future<List<dynamic>> clientSecurity(String kind) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/security/$kind'), headers: await _headers())))['data'] as List);

  /// Gate-cashier board: today's takings, per-cashier breakdown, receipts.
  Future<Map<String, dynamic>> securityCashier() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/security/cashier'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientSecurityOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/security/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientSecurityPositioning() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/security/positioning'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientSecurityGatepassCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/security/gatepass/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  // ---- client-scoped agriculture / landscaping suite -----------------------
  Future<Map<String, dynamic>> clientAgriSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/agri/summary'), headers: await _headers())))['data'] as Map);

  /// kind: zones | plants | operations | species
  Future<List<dynamic>> clientAgri(String kind) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/agri/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientAgriPlant(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/agri/plant/$id'), headers: await _headers())))['data'] as Map);

  /// Raise a service request for a tree work. opType: prune|inspect|pest|fertilize|water|other
  Future<Map<String, dynamic>> clientAgriRequest(int plantId, String opType,
          {String note = '', String priority = '1', String? preferredDate}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/agri/request'),
              headers: await _headers(), body: jsonEncode({
                'plant_id': plantId, 'op_type': opType, 'note': note,
                'priority': priority, if (preferredDate != null) 'preferred_date': preferredDate,
              }))))['data'] as Map);

  /// Client approves/rejects a zone's irrigation plan. decision: approve|reject
  Future<Map<String, dynamic>> clientAgriZoneDecision(int zoneId, String decision, {String comment = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/agri/zone/$zoneId/$decision'),
              headers: await _headers(), body: jsonEncode({'comment': comment}))))['data'] as Map);

  // ---- client-scoped cleaning suite ----------------------------------------
  Future<Map<String, dynamic>> clientCleanSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/clean/summary'), headers: await _headers())))['data'] as Map);

  /// kind: audits | schedules | rounds | consumables
  Future<List<dynamic>> clientClean(String kind) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/clean/$kind'), headers: await _headers())))['data'] as List);

  /// Client acknowledges an audit. decision: accept | dispute
  Future<Map<String, dynamic>> clientCleanAuditAck(int auditId, String decision, {String comment = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/clean/audit/$auditId/$decision'),
              headers: await _headers(), body: jsonEncode({'comment': comment}))))['data'] as Map);

  // ---- client-scoped facade cleaning suite ---------------------------------
  Future<Map<String, dynamic>> clientFacadeSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/facade/summary'), headers: await _headers())))['data'] as Map);

  /// kind: zones | permits
  Future<List<dynamic>> clientFacade(String kind) async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/facade/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientFacadeOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/facade/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientFacadePermitCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/client/facade/permit/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  // ---- client-scoped internal inventory ------------------------------------
  Future<Map<String, dynamic>> clientInvSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/inv/summary'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> clientInvStores() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/client/inv/stores'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientInvItems({int? storeId, bool low = false}) async {
    final qs = <String>[];
    if (storeId != null) qs.add('store_id=$storeId');
    if (low) qs.add('low=1');
    final path = '/client/inv/items${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return List<dynamic>.from((await _handle(
            await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<List<dynamic>> clientInvMoves({
    String? type, String? period, int? facilityId, int? buildingId,
    int? locationId, int? productId, int? employeeId, String? q,
  }) async {
    final p = <String, String>{};
    if (type != null) p['type'] = type;
    if (period != null) p['period'] = period;
    if (facilityId != null) p['facility_id'] = '$facilityId';
    if (buildingId != null) p['building_id'] = '$buildingId';
    if (locationId != null) p['location_id'] = '$locationId';
    if (productId != null) p['product_id'] = '$productId';
    if (employeeId != null) p['employee_id'] = '$employeeId';
    if (q != null && q.isNotEmpty) p['q'] = q;
    final qs = p.entries.map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}').join('&');
    return List<dynamic>.from((await _handle(await _net.get(
        _u('/client/inv/moves${qs.isEmpty ? '' : '?$qs'}'), headers: await _headers())))['data'] as List);
  }

  /// Worker scans a product barcode to consume it from a store.
  Future<Map<String, dynamic>> clientInvScanIssue(int storeId, String barcode,
          {double quantity = 1.0, int? facilityId, int? locationId}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/inv/scan-issue'),
              headers: await _headers(),
              body: jsonEncode({
                'store_id': storeId, 'barcode': barcode, 'quantity': quantity,
                if (facilityId != null) 'facility_id': facilityId,
                if (locationId != null) 'location_id': locationId,
              }))))['data'] as Map);

  Future<Map<String, dynamic>> clientInvReceive(int storeId, String barcode,
          {double quantity = 1.0, double unitCost = 0.0, String orderRef = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/inv/receive'),
              headers: await _headers(),
              body: jsonEncode({
                'store_id': storeId, 'barcode': barcode, 'quantity': quantity,
                'unit_cost': unitCost, 'order_ref': orderRef,
              }))))['data'] as Map);

  Future<List<dynamic>> clientInvLocations({int? storeId}) async {
    final path = '/client/inv/locations${storeId != null ? '?store_id=$storeId' : ''}';
    return List<dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  /// Issue a product to a destination location (any employee, from the app).
  Future<Map<String, dynamic>> clientInvIssue(int storeId, {int? productId, String? barcode, double quantity = 1.0, int? locationId, String note = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/inv/issue'),
              headers: await _headers(),
              body: jsonEncode({
                'store_id': storeId, 'quantity': quantity,
                if (productId != null) 'product_id': productId,
                if (barcode != null) 'barcode': barcode,
                if (locationId != null) 'location_id': locationId,
                if (note.isNotEmpty) 'note': note,
              }))))['data'] as Map);

  Future<Map<String, dynamic>> clientInvConsumption({String period = 'month'}) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/inv/consumption?period=$period'), headers: await _headers())))['data'] as Map);

  // ---- client-scoped waste transfer & treatment ----------------------------
  Future<Map<String, dynamic>> clientWasteSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/waste/summary'), headers: await _headers())))['data'] as Map);

  /// kind: orders | trips | centers (+ optional search/filter)
  Future<List<dynamic>> clientWaste(String kind, {String? q, String? state, String? dateFrom, String? dateTo}) async {
    final p = <String>[];
    if (q != null && q.isNotEmpty) p.add('q=${Uri.encodeQueryComponent(q)}');
    if (state != null && state.isNotEmpty) p.add('state=$state');
    if (dateFrom != null) p.add('date_from=$dateFrom');
    if (dateTo != null) p.add('date_to=$dateTo');
    final path = '/client/waste/$kind${p.isEmpty ? '' : '?${p.join('&')}'}';
    return List<dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> clientWasteOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/waste/options'), headers: await _headers())))['data'] as Map);

  /// Treatment-center receiver: incoming orders assigned to me.
  Future<List<dynamic>> wasteReceiverOrders({bool all = false}) async =>
      List<dynamic>.from((await _handle(await _net.get(
              _u('/waste/receiver/orders${all ? '?all=1' : ''}'), headers: await _headers())))['data'] as List);

  /// Receiver submits final data + media + confirmation for an order.
  /// media: [{name, mimetype, data(base64)}], items: [{item_id, quantity}], confirm: delivered|completed|processing
  Future<Map<String, dynamic>> wasteOrderReceive(int orderId, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/waste/order/$orderId/receive'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  /// Driver's assigned waste trips (active by default; all=1 for history).
  Future<List<dynamic>> wasteDriverTrips({bool all = false}) async =>
      List<dynamic>.from((await _handle(await _net.get(
              _u('/waste/driver/trips${all ? '?all=1' : ''}'), headers: await _headers())))['data'] as List);

  /// Driver posts their live location for a trip.
  Future<void> wasteTripSetLocation(int tripId, double lat, double lng) async =>
      _handle(await _net.post(_u('/waste/trip/$tripId/location'),
          headers: await _headers(), body: jsonEncode({'lat': lat, 'lng': lng})));

  /// Live driver location for a waste trip.
  Future<Map<String, dynamic>> wasteTripTrack(int tripId) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/waste/trip/$tripId/track'), headers: await _headers())))['data'] as Map);

  /// Period statistics (dateFrom/dateTo = YYYY-MM-DD) → aggregates + breakdowns.
  Future<Map<String, dynamic>> clientWasteStats({String? dateFrom, String? dateTo}) async {
    final qs = <String>[];
    if (dateFrom != null) qs.add('date_from=$dateFrom');
    if (dateTo != null) qs.add('date_to=$dateTo');
    final path = '/client/waste/stats${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return Map<String, dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> clientWasteCreate(int projectId, {int? pickupId, int? typeId, int? itemId, double qty = 1.0, String? requestDatetime, String? notes}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/client/waste/order/create'),
              headers: await _headers(),
              body: jsonEncode({
                'project_id': projectId,
                if (pickupId != null) 'pickup_location_id': pickupId,
                if (typeId != null) 'type_id': typeId,
                if (requestDatetime != null) 'request_datetime': requestDatetime,
                if (notes != null && notes.isNotEmpty) 'notes': notes,
                'items': itemId != null ? [{'item_id': itemId, 'quantity': qty}] : [],
              }))))['data'] as Map);

  // ---- CARE 2 CARE (home services storefront) ------------------------------
  Future<Map<String, dynamic>> whoami() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/whoami'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cHome() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/home'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> c2cServices({int? categoryId, String q = ''}) async {
    final qs = <String>[];
    if (categoryId != null) qs.add('category_id=$categoryId');
    if (q.isNotEmpty) qs.add('q=${Uri.encodeComponent(q)}');
    final path = '/c2c/services${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return List<dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> c2cService(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/service/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cBook(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/book'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cBookings() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/bookings'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cCancel(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/booking/$id/cancel'),
              headers: await _headers(), body: jsonEncode({}))))['data'] as Map);

  Future<Map<String, dynamic>> c2cRate(int id, int stars, {String feedback = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/booking/$id/rate'),
              headers: await _headers(), body: jsonEncode({'rating': stars, 'feedback': feedback}))))['data'] as Map);

  Future<Map<String, dynamic>> c2cAccount() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/account'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> c2cOffers() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/offers'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> c2cSubscriptions() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/subscriptions'), headers: await _headers())))['data'] as List);

  /// Subscribe to a plan → creates a request the team activates.
  Future<Map<String, dynamic>> c2cSubscribe(int planId, {String? note, int? addressId}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/subscribe'),
          headers: await _headers(),
          body: jsonEncode({
            'plan_id': planId,
            if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
            if (addressId != null) 'address_id': addressId,
          })))) ['data'] as Map);

  Future<List<dynamic>> c2cMySubscriptions() async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/c2c/my-subscriptions'), headers: await _headers())))['data'] as List);

  Future<void> c2cSubscriptionCancel(int id) async =>
      _handle(await _net.post(_u('/c2c/subscription/$id/cancel'), headers: await _headers()));

  /// Generate a Upayment payment link for a booking/subscription.
  Future<Map<String, dynamic>> c2cPayCreate(String kind, int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/pay/create'),
          headers: await _headers(), body: jsonEncode({'kind': kind, 'id': id}))))['data'] as Map);

  Future<List<dynamic>> c2cVideos() async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/c2c/videos'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cReviewSubmit(int serviceId, int rating, {String? comment}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/review/submit'),
          headers: await _headers(),
          body: jsonEncode({'service_id': serviceId, 'rating': rating,
                            if (comment != null) 'comment': comment}))))['data'] as Map);

  Future<List<dynamic>> c2cRfqOptions() async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/c2c/rfq/options'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> c2cCategoriesList() async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/c2c/categories'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cContractCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/contract/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cContracts() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/contracts'), headers: await _headers())))['data'] as List);

  /// decision: approve | reject
  Future<Map<String, dynamic>> c2cContractDecide(int id, String decision) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/contract/$id/$decision'),
              headers: await _headers(), body: jsonEncode({}))))['data'] as Map);

  /// Available booking slots + rules for a service on a date (YYYY-MM-DD).
  Future<Map<String, dynamic>> c2cSlots(int serviceId, String date) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/slots?service_id=$serviceId&date=$date'), headers: await _headers())))['data'] as Map);

  /// Validate a promo/coupon code → {valid, discount_pct, title}.
  Future<Map<String, dynamic>> c2cCoupon(String code) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/coupon?code=${Uri.encodeQueryComponent(code)}'), headers: await _headers())))['data'] as Map);

  // ---- CARE 2 CARE product shop -------------------------------------------
  Future<Map<String, dynamic>> c2cProducts({int? categoryId, String q = ''}) async {
    final qs = <String>[];
    if (categoryId != null) qs.add('category_id=$categoryId');
    if (q.isNotEmpty) qs.add('q=${Uri.encodeQueryComponent(q)}');
    final path = '/c2c/products${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return Map<String, dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> c2cShopOrderCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/order/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cShopOrders() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/orders'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cShopOrder(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/order/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cShopOrderCancel(int id, {String reason = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/order/$id/cancel'),
              headers: await _headers(), body: jsonEncode({'reason': reason}))))['data'] as Map);

  // ---- delivery addresses --------------------------------------------------
  Future<List<dynamic>> c2cAddresses() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/addresses'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cAddressSave(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/address/save'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> c2cAddressDelete(int id) async =>
      _handle(await _net.post(_u('/c2c/address/$id/delete'), headers: await _headers()));

  /// Driver: accept the trip / advance its status (accept|pickuped|arrived).
  Future<Map<String, dynamic>> wasteDriverAction(int tripId, String action) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/waste/driver/trip/$tripId/action'),
              headers: await _headers(), body: jsonEncode({'action': action}))))['data'] as Map);

  // ---- push device registration -------------------------------------------
  Future<void> registerDevice(String token, {String platform = 'android', String? deviceName}) async =>
      _handle(await _net.post(_u('/notifications/register'),
          headers: await _headers(),
          body: jsonEncode({'token': token, 'platform': platform, 'device_name': deviceName})));

  Future<void> unregisterDevice(String token) async =>
      _handle(await _net.post(_u('/notifications/unregister'),
          headers: await _headers(), body: jsonEncode({'token': token})));

  // ---- PMS (native project management) ------------------------------------
  Future<Map<String, dynamic>> pmsOverview() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/pms/overview'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> pmsProjects({String q = ''}) async =>
      List<dynamic>.from((await _handle(await _net.get(
              _u('/pms/projects${q.isEmpty ? '' : '?q=${Uri.encodeQueryComponent(q)}'}'),
              headers: await _headers())))['data'] as List);

  /// The sections available for a project (materials, team, fuel, …).
  Future<Map<String, dynamic>> pmsSections(int id) async =>
      Map<String, dynamic>.from((await _handle(
          await _net.get(_u('/pms/project/$id/sections'), headers: await _headers())))['data'] as Map);

  /// One section's rows + stats.
  Future<Map<String, dynamic>> pmsSection(int id, String code) async =>
      Map<String, dynamic>.from((await _handle(
          await _net.get(_u('/pms/project/$id/section/$code'), headers: await _headers())))['data'] as Map);

  /// Pick-lists a section's create form needs.
  Future<Map<String, dynamic>> pmsSectionOptions(int id, String code) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
          _u('/pms/project/$id/section/$code/options'), headers: await _headers())))['data'] as Map);

  Future<void> pmsSupplyReceive(int supplyId) async =>
      _handle(await _net.post(_u('/pms/supply/$supplyId/receive'), headers: await _headers()));

  Future<Map<String, dynamic>> pmsEmployeeFile(int id) async =>
      Map<String, dynamic>.from((await _handle(
          await _net.get(_u('/pms/employee/$id/file'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> pmsVehicleFile(int id) async =>
      Map<String, dynamic>.from((await _handle(
          await _net.get(_u('/pms/vehicle/$id/file'), headers: await _headers())))['data'] as Map);

  /// Create a record in a section (delivery / expense / timesheet / docrequest).
  Future<Map<String, dynamic>> pmsSectionCreate(int id, String action, Map<String, dynamic> vals) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
          _u('/pms/project/$id/$action/create'), headers: await _headers(),
          body: jsonEncode(vals))))['data'] as Map);

  Future<Map<String, dynamic>> pmsProject(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/pms/project/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> pmsTasks({int? projectId, int? stageId, String filter = '', String q = ''}) async {
    final qs = <String>[];
    if (projectId != null) qs.add('project_id=$projectId');
    if (stageId != null) qs.add('stage_id=$stageId');
    if (filter.isNotEmpty) qs.add('filter=$filter');
    if (q.isNotEmpty) qs.add('q=${Uri.encodeQueryComponent(q)}');
    return Map<String, dynamic>.from((await _handle(await _net.get(
            _u('/pms/tasks${qs.isEmpty ? '' : '?${qs.join('&')}'}'),
            headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> pmsTask(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/pms/task/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> pmsTaskStage(int id, int stageId) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/task/$id/stage'),
              headers: await _headers(), body: jsonEncode({'stage_id': stageId}))))['data'] as Map);

  Future<void> pmsTaskNote(int id, String note) async =>
      _handle(await _net.post(_u('/pms/task/$id/note'),
          headers: await _headers(), body: jsonEncode({'note': note})));

  Future<Map<String, dynamic>> pmsTaskPriority(int id, bool starred) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/task/$id/priority'),
              headers: await _headers(), body: jsonEncode({'priority': starred}))))['data'] as Map);

  /// Forward a task to another internal user (PMS routing).
  Future<Map<String, dynamic>> pmsTaskForward(int id, int toUserId, {String? reason}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/task/$id/forward'),
          headers: await _headers(),
          body: jsonEncode({'forward_to_id': toUserId, if (reason != null) 'reason': reason}))))['data'] as Map);

  Future<Map<String, dynamic>> pmsTaskAccept(int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/task/$id/accept'),
          headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> pmsTaskReject(int id, {String? reason}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/task/$id/reject'),
          headers: await _headers(),
          body: jsonEncode({if (reason != null) 'reason': reason}))))['data'] as Map);

  /// Internal users a task may be forwarded to.
  Future<List<dynamic>> pmsForwardUsers(int projectId) async =>
      List<dynamic>.from((await _handle(
          await _net.get(_u('/pms/project/$projectId/forward-users'), headers: await _headers())))['data'] as List);

  /// Create a task in a project.
  Future<Map<String, dynamic>> pmsTaskCreate(int projectId, Map<String, dynamic> vals) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/pms/project/$projectId/task/create'),
          headers: await _headers(), body: jsonEncode(vals))))['data'] as Map);

  // ---- management (native back-office) -------------------------------------
  /// Systems this user may access (server applies Odoo permissions).
  Future<List<dynamic>> managementApps() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/management/apps'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> managementList(String key, {String q = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/management/$key/list${q.isEmpty ? '' : '?q=${Uri.encodeQueryComponent(q)}'}'),
              headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> managementDetail(String key, int id) async =>
      Map<String, dynamic>.from((await _handle(await _net.get(
              _u('/management/$key/$id'), headers: await _headers())))['data'] as Map);

  /// Run a whitelisted workflow action (server gates by state + permissions).
  Future<Map<String, dynamic>> managementAction(String key, int id, String action) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/management/$key/$id/action'),
              headers: await _headers(), body: jsonEncode({'action': action}))))['data'] as Map);

  // ---- waste operations (ops manager) -------------------------------------
  /// Orders this ops manager owns. filter: unassigned | open | done
  Future<List<dynamic>> wasteOpsOrders({String filter = 'open'}) async =>
      List<dynamic>.from((await _handle(await _net.get(
              _u('/waste/ops/orders?filter=$filter'), headers: await _headers())))['data'] as List);

  /// Drivers registered on this order's project (the assignable pool).
  Future<List<dynamic>> wasteOpsDrivers(int orderId) async =>
      List<dynamic>.from((await _handle(await _net.get(
              _u('/waste/ops/drivers?order_id=$orderId'), headers: await _headers())))['data'] as List);

  /// Assign a driver — this is where the operation starts.
  Future<Map<String, dynamic>> wasteOpsAssign(int orderId, int driverId) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(
              _u('/waste/ops/order/$orderId/assign'),
              headers: await _headers(), body: jsonEncode({'driver_id': driverId}))))['data'] as Map);

  /// Account profile info + stats.
  Future<Map<String, dynamic>> accountInfo() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/account/info'), headers: await _headers())))['data'] as Map);

  /// Edit my own profile (name / email / phone). Server only ever writes env.user.
  Future<Map<String, dynamic>> accountUpdate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/account/update'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  /// Set my profile photo from base64 (data URI or raw).
  Future<Map<String, dynamic>> accountSetPhoto(String base64Image) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/account/photo'),
              headers: await _headers(), body: jsonEncode({'image': base64Image}))))['data'] as Map);

  /// Change password (verifies the current one).
  Future<Map<String, dynamic>> accountChangePassword(String oldPw, String newPw) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/account/change_password'),
              headers: await _headers(), body: jsonEncode({'old': oldPw, 'new': newPw}))))['data'] as Map);

  /// Request account & data deletion (Google Play requirement).
  Future<Map<String, dynamic>> accountDeleteRequest({String reason = ''}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/account/delete_request'),
              headers: await _headers(), body: jsonEncode({'reason': reason}))))['data'] as Map);

  /// Which portal/app sections this CAFM client may see → set of codes.
  Future<Map<String, dynamic>> clientSections() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/client/sections'), headers: await _headers())))['data'] as Map);

  // ---- CARE 2 CARE staff (crew roles) -------------------------------------
  Future<Map<String, dynamic>> c2cStaffWhoami() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/staff/whoami'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cStaffOverview() async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/staff/overview'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> c2cStaffJobs({String filter = ''}) async {
    final path = '/c2c/staff/jobs${filter.isEmpty ? '' : '?filter=$filter'}';
    return List<dynamic>.from((await _handle(await _net.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> c2cStaffJob(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await _net.get(_u('/c2c/staff/job/$id'), headers: await _headers())))['data'] as Map);

  /// act: start | complete | proof | assign | reassign | quality | approve | note
  Future<Map<String, dynamic>> c2cStaffJobAction(int id, String act, {Map<String, dynamic>? body}) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/staff/job/$id/$act'),
              headers: await _headers(), body: jsonEncode(body ?? {}))))['data'] as Map);

  Future<List<dynamic>> c2cStaffTeam() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/staff/team'), headers: await _headers())))['data'] as List);

  /// Crews available for assignment — leader, the crew's own driver, every
  /// member's live status and how loaded the crew is.
  Future<List<dynamic>> c2cStaffTeams() async =>
      List<dynamic>.from((await _handle(
              await _net.get(_u('/c2c/staff/teams'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cStaffAvailable(bool available) async =>
      Map<String, dynamic>.from((await _handle(await _net.post(_u('/c2c/staff/available'),
              headers: await _headers(), body: jsonEncode({'available': available}))))['data'] as Map);
}

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}
