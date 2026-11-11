import 'package:flutter/foundation.dart';
import 'webrtc_stream.dart';
import 'foreground_stream.dart';

/// A global streaming service (singleton) that holds the live publisher off-screen, so the stream continues when
/// «minimizing» the stream screen and returning to the rest of the app. A floating indicator appears on all screens
/// as long as [live] is true, and reopens the stream screen when tapped.
class LiveBroadcast {
  LiveBroadcast._();
  static final LiveBroadcast instance = LiveBroadcast._();

  WhipBroadcaster? bc;
  Map<String, dynamic>? session;
  int incidentId = 0;
  bool cohost = false;
  int startEpochMs = 0;

  /// Reactive notifier for the floating indicator's show/hide.
  final ValueNotifier<bool> live = ValueNotifier<bool>(false);

  bool get isLive => bc != null;

  /// Seconds since the stream started (for the timer in the indicator and the screen).
  int get elapsedSeconds =>
      startEpochMs == 0 ? 0 : ((DateTime.now().millisecondsSinceEpoch - startEpochMs) ~/ 1000);

  void begin(WhipBroadcaster b, Map<String, dynamic> s, int iid, bool co) {
    bc = b;
    session = s;
    incidentId = iid;
    cohost = co;
    startEpochMs = DateTime.now().millisecondsSinceEpoch;
    live.value = true;
    // Foreground service: the stream continues even after screen lock / leaving the app
    StreamForeground.start(iid);
  }

  /// Stop the stream permanently and release resources. Pass [api] to upload the self-recording to the server.
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
    // Upload the device recording in the background (doesn't block closing the screen)
    if (api != null && sid != null && recPath != null) {
      // ignore: avoid_dynamic_calls
      api.securityStreamUploadRecording(sid, recPath, durationSec: dur).catchError((_) {});
    }
  }
}
