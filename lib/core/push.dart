import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_client.dart';

/// Firebase Cloud Messaging wiring.
///
/// The server authenticates with FCM and the phone registers its token, but
/// nothing appeared on screen: Android does NOT draw a notification for a
/// message that arrives while the app is in the foreground, and the app had no
/// handler of its own. So every push a user was actually waiting for — app
/// open, watching for it — was delivered and then silently dropped.
///
/// The flow now is: init Firebase → ask permission (Android 13+ requires it) →
/// create a high-importance channel → register the token → and draw the
/// notification ourselves whenever one lands with the app open.
class Push {
  static String? token;
  static final _local = FlutterLocalNotificationsPlugin();

  /// High importance, so it arrives as a heads-up banner rather than silently
  /// in the shade. Matches the manifest's default-channel meta-data.
  static const _channel = AndroidNotificationChannel(
    'care_high', 'إشعارات CARE',
    description: 'Task and message alerts',
    importance: Importance.high,
  );

  /// Tapping a notification should land on the right screen. The shell sets
  /// this; until it does, taps are remembered in [pendingUrl].
  static void Function(String url)? onOpen;
  static String? pendingUrl;

  /// Safe to call before login; registration is retried once a token exists.
  static Future<void> init() async {
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('push: firebase init failed: $e');
      return;
    }
    try {
      await _local.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
          iOS: DarwinInitializationSettings(),
        ),
        onDidReceiveNotificationResponse: (r) => _open(r.payload),
      );
      await _local
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(_channel);
    } catch (e) {
      debugPrint('push: local notifications failed: $e');
    }
    try {
      final fm = FirebaseMessaging.instance;
      // Android 13+ shows nothing without this; iOS always needs it.
      await fm.requestPermission(alert: true, badge: true, sound: true);
      // iOS otherwise swallows foreground pushes before we ever see them.
      await fm.setForegroundNotificationPresentationOptions(
          alert: true, badge: true, sound: true);
      token = await fm.getToken();
      debugPrint('push: token ${token == null ? 'NULL' : '${token!.substring(0, 12)}…'}');
      // FCM rotates tokens; a stale one silently stops delivering.
      fm.onTokenRefresh.listen((t) async {
        token = t;
        await _register(t);
      });
      // app open → draw it ourselves
      FirebaseMessaging.onMessage.listen(_show);
      // app in background, user tapped the banner
      FirebaseMessaging.onMessageOpenedApp.listen((m) => _open(m.data['action_url'] as String?));
      // app was closed entirely and launched by the tap
      final initial = await fm.getInitialMessage();
      if (initial != null) _open(initial.data['action_url'] as String?);
    } catch (e) {
      debugPrint('push: token failed: $e');
    }
  }

  static Future<void> _show(RemoteMessage m) async {
    final n = m.notification;
    final title = n?.title ?? m.data['title'] as String?;
    final body = n?.body ?? m.data['body'] as String?;
    if (title == null && body == null) return;
    try {
      await _local.show(
        m.hashCode,
        title,
        body,
        NotificationDetails(
          android: AndroidNotificationDetails(
            _channel.id, _channel.name,
            channelDescription: _channel.description,
            importance: Importance.high, priority: Priority.high,
            icon: '@mipmap/ic_launcher',
          ),
          iOS: const DarwinNotificationDetails(),
        ),
        payload: m.data['action_url'] as String?,
      );
    } catch (e) {
      debugPrint('push: show failed: $e');
    }
  }

  static void _open(String? url) {
    if (url == null || url.isEmpty) return;
    final h = onOpen;
    if (h != null) {
      h(url);
    } else {
      pendingUrl = url; // the shell picks it up once it is listening
    }
  }

  /// Called by the shell once it can navigate — drains anything tapped before.
  static void attach(void Function(String url) handler) {
    onOpen = handler;
    final p = pendingUrl;
    if (p != null) {
      pendingUrl = null;
      handler(p);
    }
  }

  static ApiClient? _api;

  /// Called once the user is authenticated — a token is useless to the server
  /// until it can be attached to a user.
  static Future<void> registerWith(ApiClient api) async {
    _api = api;
    // A token can arrive after init() (permission prompt, cold network), so
    // fetch once more at login rather than registering nothing at all.
    if (token == null) {
      try {
        token = await FirebaseMessaging.instance.getToken();
      } catch (_) {}
    }
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
