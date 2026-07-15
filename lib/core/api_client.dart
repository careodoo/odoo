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

  Future<Map<String, dynamic>> workerOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/worker/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> createWorker(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/client/worker/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> clientContracts() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/contracts'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientRequests() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/requests'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientObservations() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/observations'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> createObservation(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/client/observation/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> observationToWorkOrder(int id) async =>
      _handle(await http.post(_u('/client/observation/$id/workorder'), headers: await _headers()));

  Future<List<dynamic>> clientPpm() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/ppm'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> createRequest(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/client/request/create'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> servicesList() async {
    try {
      return List<dynamic>.from((await _handle(
              await http.get(_u('/services'), headers: await _headers())))['data'] as List);
    } catch (_) { return const []; }
  }

  Future<Map<String, dynamic>> manageOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/manage/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> manageUpsert(String kind, Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(
              _u('/client/manage/$kind'), headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<void> manageDelete(String kind, int id) async =>
      _handle(await http.post(_u('/client/manage/$kind/$id/delete'), headers: await _headers()));

  /// Absolute URL for a contract copy (needs the Bearer token to fetch).
  String contractCopyUrl(String path) => path.startsWith('http') ? path : '$baseUrl$path';

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

  // ---- contracted services (segmented menu) --------------------------------
  Future<List<dynamic>> clientServices() async {
    try {
      final body = await _handle(await http.get(_u('/client/services'), headers: await _headers()));
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
            await http.get(_u('/client/products$qs'), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> clientProduct(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/product/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> favoriteToggle(int productId) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/favorite/toggle'),
              headers: await _headers(), body: jsonEncode({'product_id': productId})))) ['data'] as Map);

  Future<Map<String, dynamic>> clientFavorites() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/favorites'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> orderCreate(List<Map<String, dynamic>> lines) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/order/create'),
              headers: await _headers(), body: jsonEncode({'lines': lines})))) ['data'] as Map);

  Future<List<dynamic>> clientOrders() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/orders'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientOrder(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/order/$id'), headers: await _headers())))['data'] as Map);

  Future<void> orderCancel(int id) async =>
      _handle(await http.post(_u('/client/order/$id/cancel'), headers: await _headers()));

  // ---- invoices ------------------------------------------------------------
  Future<Map<String, dynamic>> clientInvoices() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/invoices'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientInvoice(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/invoice/$id'), headers: await _headers())))['data'] as Map);

  Future<void> invoiceApprove(int id, String comment) async =>
      _handle(await http.post(_u('/client/invoice/$id/approve'),
          headers: await _headers(), body: jsonEncode({'comment': comment})));

  Future<void> invoiceReject(int id, String comment) async =>
      _handle(await http.post(_u('/client/invoice/$id/reject'),
          headers: await _headers(), body: jsonEncode({'comment': comment})));

  Future<List<dynamic>> clientSchedules() async =>
      List<dynamic>.from(((await _handle(
              await http.get(_u('/client/schedules'), headers: await _headers())))['data']
          as Map)['schedules'] as List);

  Future<Map<String, dynamic>> clientAttendanceData() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/attendance'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> notifyOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/notify/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> notifySend(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/notify/send'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> notifySent() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/notify/sent'), headers: await _headers())))['data'] as List);

  // ---- client-scoped security suite ----------------------------------------
  Future<Map<String, dynamic>> clientSecuritySummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/security/summary'), headers: await _headers())))['data'] as Map);

  /// kind: incidents | patrols | gatepasses | visitors | inspections | guards | keys
  Future<List<dynamic>> clientSecurity(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/security/$kind'), headers: await _headers())))['data'] as List);

  // ---- client-scoped agriculture / landscaping suite -----------------------
  Future<Map<String, dynamic>> clientAgriSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/agri/summary'), headers: await _headers())))['data'] as Map);

  /// kind: zones | plants | operations | species
  Future<List<dynamic>> clientAgri(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/agri/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientAgriPlant(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/agri/plant/$id'), headers: await _headers())))['data'] as Map);

  /// Raise a service request for a tree work. opType: prune|inspect|pest|fertilize|water|other
  Future<Map<String, dynamic>> clientAgriRequest(int plantId, String opType, {String note = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/agri/request'),
              headers: await _headers(), body: jsonEncode({'plant_id': plantId, 'op_type': opType, 'note': note}))))['data'] as Map);

  /// Client approves/rejects a zone's irrigation plan. decision: approve|reject
  Future<Map<String, dynamic>> clientAgriZoneDecision(int zoneId, String decision, {String comment = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/agri/zone/$zoneId/$decision'),
              headers: await _headers(), body: jsonEncode({'comment': comment}))))['data'] as Map);

  // ---- client-scoped cleaning suite ----------------------------------------
  Future<Map<String, dynamic>> clientCleanSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/clean/summary'), headers: await _headers())))['data'] as Map);

  /// kind: audits | schedules | rounds | consumables
  Future<List<dynamic>> clientClean(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/clean/$kind'), headers: await _headers())))['data'] as List);

  /// Client acknowledges an audit. decision: accept | dispute
  Future<Map<String, dynamic>> clientCleanAuditAck(int auditId, String decision, {String comment = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/clean/audit/$auditId/$decision'),
              headers: await _headers(), body: jsonEncode({'comment': comment}))))['data'] as Map);

  // ---- client-scoped facade cleaning suite ---------------------------------
  Future<Map<String, dynamic>> clientFacadeSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/facade/summary'), headers: await _headers())))['data'] as Map);

  /// kind: zones | permits
  Future<List<dynamic>> clientFacade(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/facade/$kind'), headers: await _headers())))['data'] as List);

  // ---- client-scoped internal inventory ------------------------------------
  Future<Map<String, dynamic>> clientInvSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/inv/summary'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> clientInvStores() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/inv/stores'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> clientInvItems({int? storeId, bool low = false}) async {
    final qs = <String>[];
    if (storeId != null) qs.add('store_id=$storeId');
    if (low) qs.add('low=1');
    final path = '/client/inv/items${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return List<dynamic>.from((await _handle(
            await http.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<List<dynamic>> clientInvMoves() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/inv/moves'), headers: await _headers())))['data'] as List);

  /// Worker scans a product barcode to consume it from a store.
  Future<Map<String, dynamic>> clientInvScanIssue(int storeId, String barcode,
          {double quantity = 1.0, int? facilityId, int? locationId}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/inv/scan-issue'),
              headers: await _headers(),
              body: jsonEncode({
                'store_id': storeId, 'barcode': barcode, 'quantity': quantity,
                if (facilityId != null) 'facility_id': facilityId,
                if (locationId != null) 'location_id': locationId,
              }))))['data'] as Map);

  Future<Map<String, dynamic>> clientInvReceive(int storeId, String barcode,
          {double quantity = 1.0, double unitCost = 0.0, String orderRef = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/inv/receive'),
              headers: await _headers(),
              body: jsonEncode({
                'store_id': storeId, 'barcode': barcode, 'quantity': quantity,
                'unit_cost': unitCost, 'order_ref': orderRef,
              }))))['data'] as Map);

  Future<List<dynamic>> clientInvLocations({int? storeId}) async {
    final path = '/client/inv/locations${storeId != null ? '?store_id=$storeId' : ''}';
    return List<dynamic>.from((await _handle(await http.get(_u(path), headers: await _headers())))['data'] as List);
  }

  /// Issue a product to a destination location (any employee, from the app).
  Future<Map<String, dynamic>> clientInvIssue(int storeId, {int? productId, String? barcode, double quantity = 1.0, int? locationId, String note = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/inv/issue'),
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
              await http.get(_u('/client/inv/consumption?period=$period'), headers: await _headers())))['data'] as Map);

  // ---- client-scoped waste transfer & treatment ----------------------------
  Future<Map<String, dynamic>> clientWasteSummary() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/waste/summary'), headers: await _headers())))['data'] as Map);

  /// kind: orders | trips | centers
  Future<List<dynamic>> clientWaste(String kind) async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/client/waste/$kind'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> clientWasteOptions() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/client/waste/options'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> clientWasteCreate(int projectId, {int? pickupId, int? itemId, double qty = 1.0}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/client/waste/order/create'),
              headers: await _headers(),
              body: jsonEncode({
                'project_id': projectId,
                if (pickupId != null) 'pickup_location_id': pickupId,
                'items': itemId != null ? [{'item_id': itemId, 'quantity': qty}] : [],
              }))))['data'] as Map);

  // ---- CARE 2 CARE (home services storefront) ------------------------------
  Future<Map<String, dynamic>> whoami() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/whoami'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cHome() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/c2c/home'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> c2cServices({int? categoryId, String q = ''}) async {
    final qs = <String>[];
    if (categoryId != null) qs.add('category_id=$categoryId');
    if (q.isNotEmpty) qs.add('q=${Uri.encodeComponent(q)}');
    final path = '/c2c/services${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return List<dynamic>.from((await _handle(await http.get(_u(path), headers: await _headers())))['data'] as List);
  }

  Future<Map<String, dynamic>> c2cService(int id) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/c2c/service/$id'), headers: await _headers())))['data'] as Map);

  Future<Map<String, dynamic>> c2cBook(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/book'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cBookings() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/c2c/bookings'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cCancel(int id) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/booking/$id/cancel'),
              headers: await _headers(), body: jsonEncode({}))))['data'] as Map);

  Future<Map<String, dynamic>> c2cRate(int id, int stars, {String feedback = ''}) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/booking/$id/rate'),
              headers: await _headers(), body: jsonEncode({'rating': stars, 'feedback': feedback}))))['data'] as Map);

  Future<Map<String, dynamic>> c2cAccount() async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/c2c/account'), headers: await _headers())))['data'] as Map);

  Future<List<dynamic>> c2cOffers() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/c2c/offers'), headers: await _headers())))['data'] as List);

  Future<List<dynamic>> c2cSubscriptions() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/c2c/subscriptions'), headers: await _headers())))['data'] as List);

  Future<Map<String, dynamic>> c2cContractCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/contract/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cContracts() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/c2c/contracts'), headers: await _headers())))['data'] as List);

  /// decision: approve | reject
  Future<Map<String, dynamic>> c2cContractDecide(int id, String decision) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/contract/$id/$decision'),
              headers: await _headers(), body: jsonEncode({}))))['data'] as Map);

  /// Available booking slots + rules for a service on a date (YYYY-MM-DD).
  Future<Map<String, dynamic>> c2cSlots(int serviceId, String date) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/c2c/slots?service_id=$serviceId&date=$date'), headers: await _headers())))['data'] as Map);

  /// Validate a promo/coupon code → {valid, discount_pct, title}.
  Future<Map<String, dynamic>> c2cCoupon(String code) async =>
      Map<String, dynamic>.from((await _handle(
              await http.get(_u('/c2c/coupon?code=${Uri.encodeQueryComponent(code)}'), headers: await _headers())))['data'] as Map);

  // ---- CARE 2 CARE product shop -------------------------------------------
  Future<Map<String, dynamic>> c2cProducts({int? categoryId, String q = ''}) async {
    final qs = <String>[];
    if (categoryId != null) qs.add('category_id=$categoryId');
    if (q.isNotEmpty) qs.add('q=${Uri.encodeQueryComponent(q)}');
    final path = '/c2c/products${qs.isEmpty ? '' : '?${qs.join('&')}'}';
    return Map<String, dynamic>.from((await _handle(await http.get(_u(path), headers: await _headers())))['data'] as Map);
  }

  Future<Map<String, dynamic>> c2cShopOrderCreate(Map<String, dynamic> body) async =>
      Map<String, dynamic>.from((await _handle(await http.post(_u('/c2c/order/create'),
              headers: await _headers(), body: jsonEncode(body))))['data'] as Map);

  Future<List<dynamic>> c2cShopOrders() async =>
      List<dynamic>.from((await _handle(
              await http.get(_u('/c2c/orders'), headers: await _headers())))['data'] as List);
}

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}
