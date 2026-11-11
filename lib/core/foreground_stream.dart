/// Intentionally disabled: the camera/microphone foreground service was removed to comply with
/// Google Play requirements (it required a demo video for the FOREGROUND_SERVICE_CAMERA/
/// MICROPHONE permissions). Streaming now works only while the app is open and the screen is on, and stops on
/// screen lock / going to background.
///
/// The interface (start/stop) is kept as is so call sites aren't affected — but it does
/// not run any foreground service.
class StreamForeground {
  /// Nothing — it no longer runs a foreground service.
  static Future<void> start(int incidentId) async {}

  /// Nothing.
  static Future<void> stop() async {}
}
