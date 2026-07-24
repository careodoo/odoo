import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// البث المباشر عبر مزوّد خارجي. المدير يُعدّ عدة خدمات في الباك ايند
/// (RTMP/HLS)، والحارس يختار مزوّداً فيولّد الخادم رابط إدخال (يبثّ إليه عبر
/// أداة RTMP مثل Larix) ورابط مشاهدة (HLS) يُشعَر به الفريق. لا يعتمد على أي
/// SDK داخل التطبيق (تفادياً لمشكلة Agora مع AGP 9).
class Stream {
  static Future<void> goLive(BuildContext context, {int? incidentId, String? title}) async {
    final api = context.read<AuthProvider>().api;
    List<dynamic> provs;
    try {
      provs = await api.securityStreamProviders();
    } catch (e) {
      if (context.mounted) _err(context, '$e'.replaceFirst('Exception: ', ''));
      return;
    }
    if (provs.isEmpty) {
      if (context.mounted) _err(context, tr('لا توجد خدمة بث مُعدّة في الباك ايند بعد.', 'No streaming provider configured yet.'));
      return;
    }
    // اختيار المزوّد إن تعدّد
    Map? provider = provs.first as Map;
    if (provs.length > 1 && context.mounted) {
      provider = await showModalBottomSheet<Map>(context: context, backgroundColor: const Color(0xFF152238),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => ListView(shrinkWrap: true, children: [
          const Padding(padding: EdgeInsets.all(14), child: Text('اختر خدمة البث', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
          for (final p in provs.cast<Map>()) ListTile(
            leading: const Icon(Icons.cast_rounded, color: Color(0xFFE5484D)),
            title: Text('${p['name']}', style: const TextStyle(color: Colors.white)),
            subtitle: Text('${p['type']}', style: const TextStyle(color: Color(0xFF9CB2CD))),
            onTap: () => Navigator.pop(_, p)),
        ]));
      if (provider == null) return;
    }
    // اختيار المشاهدين: الفريق كامل أو أعضاء محدّدون
    List<int>? viewerIds;
    if (context.mounted) {
      viewerIds = await _pickViewers(context);
      if (viewerIds == null && context.mounted) {
        // ألغى الاختيار
        return;
      }
    }
    try {
      final s = await api.securityStreamStart(
          incidentId: incidentId, providerId: provider['id'] as int,
          viewerIds: (viewerIds != null && viewerIds.isNotEmpty) ? viewerIds : null);
      if (!context.mounted) return;
      _showLiveSheet(context, s);
    } catch (e) {
      if (context.mounted) _err(context, '$e'.replaceFirst('Exception: ', ''));
    }
  }

  /// اختيار مشاهدي البث: يعيد قائمة user_ids المحدّدة، أو [] للفريق كامل،
  /// أو null إن ألغى المستخدم.
  static Future<List<int>?> _pickViewers(BuildContext context) async {
    // «الفريق كامل» سريعاً، أو فتح قائمة الأعضاء للاختيار
    final choice = await showModalBottomSheet<String>(context: context, backgroundColor: const Color(0xFF152238),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Padding(padding: EdgeInsets.all(14), child: Text('من يشاهد البث؟', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        ListTile(leading: const Icon(Icons.groups_rounded, color: Color(0xFF37C98A)),
            title: const Text('الفريق كامل', style: TextStyle(color: Colors.white)),
            onTap: () => Navigator.pop(_, 'all')),
        ListTile(leading: const Icon(Icons.person_search_rounded, color: Color(0xFF4AA8FF)),
            title: const Text('اختيار أعضاء محدّدين', style: TextStyle(color: Colors.white)),
            onTap: () => Navigator.pop(_, 'pick')),
        const SizedBox(height: 8),
      ])));
    if (choice == null) return null;
    if (choice == 'all') return const [];
    // جلب أعضاء الفريق واختيار من له user_id
    final teamData = await context.read<AuthProvider>().api.securityMyTeam();
    final members = <Map>[];
    for (final t in ((teamData['teams'] as List?) ?? const []).cast<Map>()) {
      for (final m in ((t['members'] as List?) ?? const []).cast<Map>()) {
        if (m['user_id'] != null && m['is_me'] != true) members.add(m);
      }
    }
    if (!context.mounted) return null;
    if (members.isEmpty) { _err(context, tr('لا أعضاء لديهم حساب مستخدم', 'No members with an account')); return const []; }
    final selected = <int>{};
    final ok = await showModalBottomSheet<bool>(context: context, backgroundColor: const Color(0xFF152238), isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => StatefulBuilder(builder: (_, setD) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Padding(padding: EdgeInsets.all(14), child: Text('اختر المشاهدين', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        Flexible(child: ListView(shrinkWrap: true, children: [
          for (final m in members) CheckboxListTile(
            value: selected.contains(m['user_id']),
            activeColor: const Color(0xFF4AA8FF),
            title: Text('${m['name']}', style: const TextStyle(color: Colors.white)),
            subtitle: m['role'] != null ? Text('${m['role']}', style: const TextStyle(color: Color(0xFF9CB2CD))) : null,
            onChanged: (v) => setD(() => v == true ? selected.add(m['user_id'] as int) : selected.remove(m['user_id'])),
          ),
        ])),
        Padding(padding: const EdgeInsets.all(12), child: SizedBox(width: double.infinity,
            child: FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
                onPressed: () => Navigator.pop(_, true), child: Text('بث للمحدّدين (${selected.length})')))),
      ]))));
    if (ok != true) return null;
    return selected.toList();
  }

  /// بعد بدء البث: نعرض رابط الإدخال (للحارس ليبثّ إليه عبر أداة RTMP) + تأكيد
  /// أن الفريق أُشعِر.
  static void _showLiveSheet(BuildContext context, Map s) {
    final ingest = '${s['ingest_url'] ?? ''}';
    final playback = '${s['playback_url'] ?? ''}';
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: const Color(0xFF0F1B2E),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Container(width: 10, height: 10, decoration: const BoxDecoration(color: Color(0xFFE5484D), shape: BoxShape.circle)),
            const SizedBox(width: 8),
            Text('🔴 ${tr('أنت الآن على الهواء', 'You are live')}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          ]),
          const SizedBox(height: 6),
          Text('${tr('عبر', 'via')} ${s['provider'] ?? ''} — ${tr('أُشعِر الفريق للمشاهدة', 'team notified to watch')}',
              style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
          if (ingest.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(tr('رابط البث (ألصقه في تطبيق البث لديك RTMP):', 'Broadcast URL (paste in your RTMP app):'),
                style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: const Color(0xFF152238), borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Expanded(child: SelectableText(ingest, style: const TextStyle(color: Color(0xFF4AA8FF), fontSize: 11.5))),
                IconButton(icon: const Icon(Icons.copy_rounded, color: Colors.white, size: 18),
                    onPressed: () { Clipboard.setData(ClipboardData(text: ingest)); ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(tr('نُسخ الرابط', 'Copied')), backgroundColor: const Color(0xFF16A34A))); }),
              ]),
            ),
          ],
          const SizedBox(height: 16),
          if (playback.isNotEmpty)
            OutlinedButton.icon(
              onPressed: () => launchUrl(Uri.parse(playback), mode: LaunchMode.externalApplication),
              icon: const Icon(Icons.play_circle_rounded, color: Color(0xFF37C98A)),
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF37C98A), side: const BorderSide(color: Color(0xFF37C98A))),
              label: Text(tr('معاينة رابط المشاهدة', 'Preview watch link'))),
          const SizedBox(height: 10),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF152238)),
              onPressed: () => Navigator.pop(context), child: Text(tr('تم', 'Done'))),
        ]),
      ));
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
