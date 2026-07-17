import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'api_client.dart';

/// Firebase Cloud Messaging wiring.
///
/// The server could already authenticate with FCM, but nothing ever arrived
/// because the app never obtained a device token nor registered it — there was
/// simply no device to send to. This closes that half:
///   init Firebase → ask permission (Android 13+ requires it) → get the token →
///   POST it to /notifications/register → keep it fresh on rotation.
class Push {
  static String? token;

  /// Safe to call before login; registration is retried once a token exists.
  static Future<void> init() async {
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('push: firebase init failed: $e');
      return;
    }
    try {
      final fm = FirebaseMessaging.instance;
      // Android 13+ shows nothing without this; iOS always needs it.
      await fm.requestPermission(alert: true, badge: true, sound: true);
      token = await fm.getToken();
      debugPrint('push: token ${token == null ? 'NULL' : '${token!.substring(0, 12)}…'}');
      // FCM rotates tokens; a stale one silently stops delivering.
      fm.onTokenRefresh.listen((t) async {
        token = t;
        await _register(t);
      });
    } catch (e) {
      debugPrint('push: token failed: $e');
    }
  }

  static ApiClient? _api;

  /// Called once the user is authenticated — a token is useless to the server
  /// until it can be attached to a user.
  static Future<void> registerWith(ApiClient api) async {
    _api = api;
    if (token != null) await _register(token!);
  }

  static Future<void> _register(String t) async {
    final api = _api;
    if (api == null) return;
    try {
      await api.registerDevice(t);
      debugPrint('push: device registered');
    } catch (e) {
      debugPrint('push: register failed: $e');
    }
  }

  static Future<void> unregister() async {
    final api = _api;
    if (api == null || token == null) return;
    try {
      await api.unregisterDevice(token!);
    } catch (_) {}
  }
}
