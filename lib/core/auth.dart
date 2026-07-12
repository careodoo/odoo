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

  bool get isLoggedIn => profile != null;
  bool get isImpersonating => _adminToken != null;

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
    await api.logout();
    profile = null;
    notifyListeners();
  }
}
