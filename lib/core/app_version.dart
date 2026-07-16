import 'package:package_info_plus/package_info_plus.dart';

/// The app's REAL version, read from the package at runtime.
///
/// A screen used to print a hardcoded "v1.8.0" long after the app had moved to
/// 2.12 — which is exactly how a stale install gets mistaken for a fresh one.
/// Never hardcode a version string again; read it from here.
class AppVersion {
  static String _v = '';

  /// e.g. "2.12.1+28" — empty until [load] completes.
  static String get value => _v;

  static Future<void> load() async {
    try {
      final i = await PackageInfo.fromPlatform();
      _v = '${i.version}+${i.buildNumber}';
    } catch (_) {
      _v = '';
    }
  }
}
