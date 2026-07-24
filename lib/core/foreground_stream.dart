import 'dart:io';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'i18n.dart';

/// يُبقي بثّ الكاميرا/الميكروفون حيّاً في الخلفية عبر خدمة أمامية (Foreground
/// Service). بدونها يوقف Android الكاميرا عند قفل الشاشة أو الخروج من التطبيق.
/// إشعار دائم «أنت تبثّ» مطلوب من النظام ويؤكّد للحارس أن البثّ مستمرّ.
class StreamForeground {
  static bool _inited = false;

  static void _ensureInit() {
    if (_inited) return;
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'care_live_stream',
        channelName: tr('البث المباشر', 'Live stream'),
        channelDescription: tr('استمرار البثّ في الخلفية', 'Keeps the stream alive in background'),
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        onlyAlertOnce: true,
      ),
      iosNotificationOptions: const IOSNotificationOptions(),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.nothing(),
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
    _inited = true;
  }

  /// يبدأ الخدمة الأمامية (Android فقط) بنوع camera + microphone.
  static Future<void> start(int incidentId) async {
    if (!Platform.isAndroid) return;
    try {
      _ensureInit();
      if (await FlutterForegroundTask.isRunningService) return;
      await FlutterForegroundTask.startService(
        serviceTypes: const [ForegroundServiceTypes.camera, ForegroundServiceTypes.microphone],
        notificationTitle: tr('أنت تبثّ مباشرةً', 'You are live'),
        notificationText: tr('البثّ مستمرّ في الخلفية', 'Streaming continues in background'),
      );
    } catch (_) {}
  }

  static Future<void> stop() async {
    if (!Platform.isAndroid) return;
    try {
      if (await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.stopService();
      }
    } catch (_) {}
  }
}
