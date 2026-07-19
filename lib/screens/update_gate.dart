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
      await showDialog(
        context: context,
        barrierDismissible: !force,
        builder: (c) => PopScope(
          canPop: !force,
          child: AlertDialog(
            title: Row(children: [
              const Icon(Icons.system_update_rounded, color: Color(0xFF0891B2)),
              const SizedBox(width: 8),
              Expanded(child: Text(tr('تحديث متوفّر', 'Update available'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17))),
            ]),
            content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${cfg['update_message'] ?? ''}', style: const TextStyle(fontSize: 14, height: 1.4)),
              const SizedBox(height: 10),
              Text('${tr('إصدارك', 'Yours')}: ${info.version}   •   ${tr('المطلوب', 'Required')}: $min',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ]),
            actions: [
              if (!force)
                TextButton(onPressed: () => Navigator.pop(c), child: Text(tr('لاحقاً', 'Later'))),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0891B2)),
                onPressed: () async {
                  if (url.isNotEmpty) {
                    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                  }
                },
                icon: const Icon(Icons.download_rounded),
                label: Text(tr('تحديث الآن', 'Update now')),
              ),
            ],
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
