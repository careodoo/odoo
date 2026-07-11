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

  bool get isLoggedIn => profile != null;

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
    await api.logout();
    profile = null;
    notifyListeners();
  }
}
