import 'package:flutter/foundation.dart';
import 'webrtc_stream.dart';
import 'foreground_stream.dart';

/// خدمة بثّ عامّة (singleton) تحمل الناشر الحيّ خارج الشاشة، فيستمرّ البثّ عند
/// «تصغير» شاشة البثّ والعودة لباقي التطبيق. مؤشّر عائم يظهر في كل الشاشات
/// طالما [live] صحيحة، ويعيد فتح شاشة البثّ عند الضغط.
class LiveBroadcast {
  LiveBroadcast._();
  static final LiveBroadcast instance = LiveBroadcast._();

  WhipBroadcaster? bc;
  Map<String, dynamic>? session;
  int incidentId = 0;
  bool cohost = false;
  int startEpochMs = 0;

  /// إشعار تفاعلي لظهور/اختفاء المؤشّر العائم.
  final ValueNotifier<bool> live = ValueNotifier<bool>(false);

  bool get isLive => bc != null;

  /// ثوانٍ منذ بدء البثّ (للمؤقّت في المؤشّر والشاشة).
  int get elapsedSeconds =>
      startEpochMs == 0 ? 0 : ((DateTime.now().millisecondsSinceEpoch - startEpochMs) ~/ 1000);

  void begin(WhipBroadcaster b, Map<String, dynamic> s, int iid, bool co) {
    bc = b;
    session = s;
    incidentId = iid;
    cohost = co;
    startEpochMs = DateTime.now().millisecondsSinceEpoch;
    live.value = true;
    // خدمة أمامية: يستمرّ البثّ حتى بعد قفل الشاشة/الخروج من التطبيق
    StreamForeground.start(iid);
  }

  /// إيقاف البثّ نهائياً وتحرير الموارد. مرّر [api] لرفع التسجيل الذاتيّ للخادم.
  Future<void> end({dynamic api}) async {
    final sid = session?['session_id'] as int?;
    final dur = elapsedSeconds;
    String? recPath;
    try {
      await bc?.stop();
      recPath = bc?.recordedPath;
    } catch (_) {}
    await StreamForeground.stop();
    bc = null;
    session = null;
    incidentId = 0;
    startEpochMs = 0;
    live.value = false;
    // رفع تسجيل الجهاز في الخلفية (لا يعطّل إغلاق الشاشة)
    if (api != null && sid != null && recPath != null) {
      // ignore: avoid_dynamic_calls
      api.securityStreamUploadRecording(sid, recPath, durationSec: dur).catchError((_) {});
    }
  }
}
