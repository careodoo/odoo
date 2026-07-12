import 'dart:async';
import 'package:flutter/foundation.dart';
import 'api_client.dart';
import '../models/models.dart';

/// Holds session state for the app. Restores a stored token on launch so a
/// field worker isn't asked to log in every shift.
class AuthProvider extends ChangeNotifier {
  AuthProvider(this.api);
  final ApiClient api;

  Profile? profile;
  bool loading = true;
  String? error;
  String? _adminToken; // saved while impersonating
  Timer? _poll;

  bool get isLoggedIn => profile != null;
  bool get isImpersonating => _adminToken != null;

  /// Poll the profile (unread notifications + task counts) every 45s so alerts
  /// surface live while the app is open — the badge updates without re-login.
  void _startPolling() {
    _poll?.cancel();
    _poll = Timer.periodic(const Duration(seconds: 45), (_) => refresh());
  }

  /// Refresh the profile silently; keeps the current one if the call fails.
  Future<void> refresh() async {
    if (profile == null) return;
    try {
      final p = Profile.fromJson(await api.me());
      profile = p;
      notifyListeners();
    } catch (_) {/* transient network error — keep showing the last state */}
  }

  /// Admin test feature: view the app as another user without re-login.
  Future<void> impersonate(String login) async {
    _adminToken ??= await api.token; // remember the admin token once
    final data = await api.impersonate(login);
    profile = Profile.fromJson(data);
    notifyListeners();
  }

  Future<void> exitImpersonation() async {
    if (_adminToken == null) return;
    await api.setToken(_adminToken);
    _adminToken = null;
    profile = Profile.fromJson(await api.me());
    notifyListeners();
  }

  Future<List<dynamic>> impersonatableUsers() => api.adminUsers();

  /// Called once at startup: if a token is stored, fetch the profile.
  Future<void> bootstrap() async {
    loading = true;
    notifyListeners();
    try {
      if (await api.token != null) {
        profile = Profile.fromJson(await api.me());
        _startPolling();
      }
    } catch (_) {
      // stale/expired token → drop it silently, show login
      await api.logout();
      profile = null;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String login, String password) async {
    error = null;
    notifyListeners();
    try {
      profile = Profile.fromJson(await api.login(login, password));
      _startPolling();
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      error = e.message;
      notifyListeners();
      return false;
    } catch (e) {
      error = 'تعذّر الاتصال بالخادم';
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    if (_adminToken != null) {
      // exit impersonation instead of a full logout
      await exitImpersonation();
      return;
    }
    _poll?.cancel();
    _poll = null;
    await api.logout();
    profile = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }
}
