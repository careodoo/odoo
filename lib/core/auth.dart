import 'i18n.dart';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_client.dart';
import 'push.dart';
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

  // ---- app interface mode (multi-portal switcher) ----
  static const _modeStore = FlutterSecureStorage();
  String? appMode; // 'c2c' | 'cafm' | 'pms' | 'backend' | null (unchosen)
  Map<String, dynamic>? interfaces; // from /whoami
  String? defaultMode; // whoami 'default' — the user's primary interface

  Future<void> setAppMode(String? m) async {
    appMode = m;
    if (m == null) {
      await _modeStore.delete(key: 'c2c_app_mode');
    } else {
      await _modeStore.write(key: 'c2c_app_mode', value: m);
    }
    notifyListeners();
  }

  Future<String?> loadAppMode() async => appMode = await _modeStore.read(key: 'c2c_app_mode');

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

  /// Re-read the profile after the user edits their own details.
  Future<void> refreshProfile() async {
    try {
      profile = Profile.fromJson(await api.me());
      notifyListeners();
    } catch (_) {}
  }

  /// Called once at startup: if a token is stored, fetch the profile.
  ///
  /// This used to drop the token on *any* failure, so a cold start with the
  /// network not up yet, a server restart, or a timeout signed the user out
  /// permanently — which is why closing the app looked like logging out. Only
  /// the server rejecting the token is a reason to forget it.
  Future<void> bootstrap() async {
    loading = true;
    notifyListeners();
    try {
      if (await api.token != null) {
        profile = Profile.fromJson(await api.me());
        _startPolling();
        Push.registerWith(api); // attach this device to the signed-in user
      }
    } on ApiException catch (e) {
      if (e.status == 401 || e.status == 403) {
        await api.logout();          // the token really is dead
        profile = null;
      } else {
        // the server had a bad moment — keep the session and try again
        sessionOffline = true;
      }
    } catch (_) {
      // no network at all: keep the session, show the app, retry on use
      sessionOffline = true;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// True when we hold a token but could not reach the server at launch.
  bool sessionOffline = false;

  /// Retry the profile fetch after a failed cold start, without signing out.
  Future<bool> retrySession() async {
    if (await api.token == null) return false;
    try {
      profile = Profile.fromJson(await api.me());
      sessionOffline = false;
      _startPolling();
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> login(String login, String password) async {
    error = null;
    notifyListeners();
    try {
      profile = Profile.fromJson(await api.login(login, password));
      _startPolling();
      Push.registerWith(api); // this device now belongs to this user
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      error = e.message;
      notifyListeners();
      return false;
    } catch (e) {
      error = tr('تعذّر الاتصال بالخادم', 'Could not reach the server');
      notifyListeners();
      return false;
    }
  }

  /// Public self-registration → CARE 2 CARE customer; auto-logs in on success.
  Future<bool> signup({required String name, String? email, String? phone, required String password}) async {
    error = null;
    notifyListeners();
    try {
      interfaces = null;
      await setAppMode(null);
      profile = Profile.fromJson(await api.signup(name: name, email: email, phone: phone, password: password));
      Push.registerWith(api); // new account → attach this device
      _startPolling();
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      error = e.message;
      notifyListeners();
      return false;
    } catch (e) {
      error = 'تعذّر إنشاء الحساب';
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
    // detach this device first, or its alerts would follow the next user in
    await Push.unregister();
    await api.logout();
    profile = null;
    interfaces = null;
    await setAppMode(null);
    notifyListeners();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }
}
