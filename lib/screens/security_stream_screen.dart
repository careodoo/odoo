import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Live streaming coordination (transport-agnostic). A guard "goes live" with a
/// stream URL from their broadcaster (RTMP/HLS/any web stream) which notifies
/// the team; teammates open that URL to watch. In-app camera broadcast via a
/// native SDK (e.g. Agora) is deferred — the current Android toolchain (AGP 9)
/// rejects Agora's native libs — so this uses a bring-your-own-URL model that
/// works with any streaming backend today.
class Stream {
  static Future<void> goLive(BuildContext context, {int? incidentId, String? title}) async {
    final urlC = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text('🎥 ${tr('بدء بث مباشر', 'Start live stream')}'),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(tr('ألصق رابط البث من تطبيق البث لديك (RTMP/HLS/رابط ويب)، وسيصل الفريق إشعار لمشاهدته.',
            'Paste the stream link from your broadcaster (RTMP/HLS/web); your team is notified to watch.'),
            style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600)),
        const SizedBox(height: 10),
        TextField(controller: urlC, autofocus: true, keyboardType: TextInputType.url,
            decoration: InputDecoration(labelText: tr('رابط البث', 'Stream URL'), border: const OutlineInputBorder())),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('بث', 'Go live'))),
      ]));
    if (ok != true || !context.mounted) return;
    try {
      await context.read<AuthProvider>().api.securityStreamStart(incidentId: incidentId, url: urlC.text.trim());
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('🔴 ${tr('أنت الآن على الهواء — أُشعِر الفريق', 'You are live — team notified')}'),
          backgroundColor: const Color(0xFFE5484D)));
      final u = urlC.text.trim();
      if (u.isNotEmpty) { try { await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication); } catch (_) {} }
    } catch (e) {
      if (context.mounted) _err(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  static Future<void> watch(BuildContext context, int incidentId, {String? title}) async {
    try {
      final s = await context.read<AuthProvider>().api.securityStreamWatch(incidentId);
      if (!context.mounted) return;
      if (s['live'] != true) { _err(context, tr('لا يوجد بث مباشر حالياً', 'No live stream right now')); return; }
      final url = '${s['url'] ?? ''}';
      if (url.isEmpty) { _err(context, tr('لم يُرفق رابط للبث', 'No stream link attached')); return; }
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      if (context.mounted) _err(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  static void _err(BuildContext c, String m) => ScaffoldMessenger.of(c).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: const Color(0xFFE11D48)));
}
