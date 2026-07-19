import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Compares the running build against the minimum the back office publishes and
/// prompts once per launch — blocking when the update is mandatory.
class UpdateGate {
  static bool _checked = false;

  /// Reset so a manual "check for updates" can run again.
  static void reset() => _checked = false;

  static Future<void> check(BuildContext context, {bool silentWhenCurrent = true}) async {
    if (_checked) return;
    _checked = true;
    try {
      final cfg = await context.read<AuthProvider>().api.appConfig();
      final info = await PackageInfo.fromPlatform();
      final min = '${cfg['min_version'] ?? ''}'.trim();
      final needsUpdate = min.isNotEmpty && _older(info.version, min);
      if (!needsUpdate) {
        // a manual check should say something rather than appear to do nothing
        if (!silentWhenCurrent && context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('تطبيقك محدَّث (${info.version})', 'You are up to date (${info.version})')),
            backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
        }
        return;
      }
      final force = cfg['force_update'] == true;
      final url = '${cfg['store_url'] ?? cfg['android_url'] ?? ''}';
      if (!context.mounted) return;
      await showModalBottomSheet(
        context: context,
        isDismissible: !force,
        enableDrag: !force,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (c) => PopScope(
          canPop: !force,
          child: _UpdateSheet(
            message: '${cfg['update_message'] ?? ''}',
            current: info.version,
            required_: min,
            force: force,
            url: url,
          ),
        ),
      );
    } catch (_) {
      // never block the app on a failed check
    }
  }

  /// true when [current] is an older semantic version than [min].
  static bool _older(String current, String min) {
    List<int> parts(String v) => v.split('+').first.split('.')
        .map((x) => int.tryParse(x.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0).toList();
    final a = parts(current), b = parts(min);
    for (var i = 0; i < 3; i++) {
      final x = i < a.length ? a[i] : 0, y = i < b.length ? b[i] : 0;
      if (x != y) return x < y;
    }
    return false;
  }
}



/// The update prompt. A stock alert dialog made a release look like an error;
/// this reads as an announcement — brand red, what is new, and one clear action.
class _UpdateSheet extends StatelessWidget {
  const _UpdateSheet({
    required this.message,
    required this.current,
    required this.required_,
    required this.force,
    required this.url,
  });

  final String message;
  final String current;
  final String required_;
  final bool force;
  final String url;

  static const _red = Color(0xFFC0392B);
  static const _ink = Color(0xFF14202B);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
      ),
      padding: const EdgeInsets.fromLTRB(22, 12, 22, 26),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        if (!force)
          Container(
            width: 42, height: 4,
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
                color: Colors.grey.shade300, borderRadius: BorderRadius.circular(3)),
          )
        else
          const SizedBox(height: 8),
        Container(
          width: 66, height: 66,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFE24A3B), _red]),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: _red.withValues(alpha: 0.3),
                blurRadius: 18, offset: const Offset(0, 8))],
          ),
          child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 32),
        ),
        const SizedBox(height: 16),
        Text(force ? tr('تحديث مطلوب', 'Update required')
                   : tr('إصدار جديد من CARE', 'A new version of CARE'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: _ink)),
        if (message.trim().isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(message,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13.5, height: 1.55, color: Colors.grey.shade700)),
        ],
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
          decoration: BoxDecoration(
              color: const Color(0xFFF6F7F9), borderRadius: BorderRadius.circular(13)),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            _version(tr('لديك', 'Yours'), current, Colors.grey.shade500),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Icon(Icons.arrow_back_rounded, size: 16, color: Colors.grey.shade400),
            ),
            _version(tr('الأحدث', 'Latest'), required_, _red),
          ]),
        ),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: Material(
            color: Colors.transparent,
            child: Ink(
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFFE24A3B), _red]),
                borderRadius: BorderRadius.circular(15),
                boxShadow: [BoxShadow(color: _red.withValues(alpha: 0.3),
                    blurRadius: 14, offset: const Offset(0, 7))],
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(15),
                onTap: url.isEmpty ? null : () async {
                  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                },
                child: SizedBox(
                  height: 54,
                  child: Center(
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.download_rounded, color: Colors.white, size: 20),
                      const SizedBox(width: 9),
                      Text(tr('تحديث الآن', 'Update now'),
                          style: const TextStyle(color: Colors.white, fontSize: 16,
                              fontWeight: FontWeight.w900)),
                    ]),
                  ),
                ),
              ),
            ),
          ),
        ),
        if (!force) ...[
          const SizedBox(height: 4),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(tr('لاحقاً', 'Later'),
                style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
          ),
        ] else ...[
          const SizedBox(height: 12),
          Text(tr('لا يمكن متابعة استخدام التطبيق قبل التحديث',
                  'The app cannot be used until it is updated'),
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500)),
        ],
      ]),
    );
  }

  Widget _version(String label, String value, Color color) =>
      Column(mainAxisSize: MainAxisSize.min, children: [
        Text(label, style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500,
            fontWeight: FontWeight.w700)),
        const SizedBox(height: 2),
        Text(value, style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900, color: color)),
      ]);
}
