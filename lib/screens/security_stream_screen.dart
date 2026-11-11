import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/live_broadcast.dart';
import 'security_broadcast_screen.dart';
import 'stream_view_screen.dart';

/// Live streaming via an external provider. The admin configures several services in the backend
/// (RTMP/HLS), and the guard picks a provider so the server generates an ingest link (streamed to via
/// an RTMP tool like Larix) and a viewing link (HLS) the team is notified of. It doesn't rely on any
/// SDK inside the app (to avoid the Agora issue with AGP 9).
class Stream {
  static Future<void> goLive(BuildContext context, {int? incidentId, String? title}) async {
    // Prevent two streams at once: if there's an active stream, ask to return to it or stop it first
    if (LiveBroadcast.instance.isLive) {
      final c = await _activeStreamDialog(context);
      if (c == 'resume') {
        if (!context.mounted) return;
        Navigator.push(context, MaterialPageRoute(builder: (_) => SecurityBroadcastScreen(
            incidentId: LiveBroadcast.instance.incidentId, providerId: -1,
            cohost: LiveBroadcast.instance.cohost)));
        return;
      } else if (c == 'stop') {
        final api2 = context.read<AuthProvider>().api;
        final iid = LiveBroadcast.instance.incidentId, co = LiveBroadcast.instance.cohost;
        await LiveBroadcast.instance.end();
        try { if (co) { await api2.securityStreamCohostStop(iid); } else { await api2.securityStreamStop(iid); } } catch (_) {}
        // then proceed to start a new stream
      } else {
        return; // إلغاء
      }
    }
    if (!context.mounted) return;
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
    // Select the provider if there are several
    Map? provider = provs.first as Map;
    if (provs.length > 1 && context.mounted) {
      provider = await showModalBottomSheet<Map>(context: context, backgroundColor: const Color(0xFF152238),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => ListView(shrinkWrap: true, children: [
          Padding(padding: const EdgeInsets.all(14), child: Text(tr('اختر خدمة البث', 'Choose a streaming service'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
          for (final p in provs.cast<Map>()) ListTile(
            leading: const Icon(Icons.cast_rounded, color: Color(0xFFE5484D)),
            title: Text('${p['name']}', style: const TextStyle(color: Colors.white)),
            subtitle: Text('${p['type']}', style: const TextStyle(color: Color(0xFF9CB2CD))),
            onTap: () => Navigator.pop(_, p)),
        ]));
      if (provider == null) return;
    }
    // Select the audience: all (team + client) / client only / team only
    String? audience;
    if (context.mounted) {
      audience = await _pickAudience(context);
      if (audience == null) return; // ألغى
    }
    // If "team only": allow selecting specific members
    List<int>? viewerIds;
    if (audience == 'team' && context.mounted) {
      viewerIds = await _pickViewers(context);
      if (viewerIds == null) return;
    }
    if (!context.mounted) return;
    // The professional streaming screen handles session creation, publishing (WebRTC), viewers, and chat
    Navigator.push(context, MaterialPageRoute(builder: (_) => SecurityBroadcastScreen(
        incidentId: incidentId, providerId: provider!['id'] as int, audience: audience,
        viewerIds: (viewerIds != null && viewerIds.isNotEmpty) ? viewerIds : null)));
  }

  /// Select the stream audience. Returns 'all' | 'client' | 'team' or null if cancelled.
  static Future<String?> _pickAudience(BuildContext context) async {
    return showModalBottomSheet<String>(context: context, backgroundColor: const Color(0xFF152238),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.all(14), child: Text(tr('لمن يظهر البثّ؟', 'Who sees the broadcast?'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
        ListTile(leading: const Icon(Icons.public_rounded, color: Color(0xFF37C98A)),
            title: Text(tr('الكل (الفريق + العميل)', 'Everyone (team + client)'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            subtitle: Text(tr('يراه فريق الأمن وعميل الموقع', 'Seen by the security team and the site client'), style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
            onTap: () => Navigator.pop(_, 'all')),
        ListTile(leading: const Icon(Icons.business_rounded, color: Color(0xFF4AA8FF)),
            title: Text(tr('العميل فقط', 'Client only'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            subtitle: Text(tr('يراه عميل الموقع فقط', 'Seen by the site client only'), style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
            onTap: () => Navigator.pop(_, 'client')),
        ListTile(leading: const Icon(Icons.groups_rounded, color: Color(0xFFF7A23B)),
            title: Text(tr('الفريق فقط', 'Team only'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            subtitle: Text(tr('يراه فريق الأمن فقط (اختيار الأعضاء)', 'Seen by the security team only (pick members)'), style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
            onTap: () => Navigator.pop(_, 'team')),
        const SizedBox(height: 8),
      ])));
  }

  /// Select stream viewers: returns the list of selected user_ids, or [] for the whole team,
  /// or null if the user cancelled.
  static Future<List<int>?> _pickViewers(BuildContext context) async {
    // "Whole team" quickly, or open the member list to choose
    final choice = await showModalBottomSheet<String>(context: context, backgroundColor: const Color(0xFF152238),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.all(14), child: Text(tr('من يشاهد البث؟', 'Who watches the broadcast?'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        ListTile(leading: const Icon(Icons.groups_rounded, color: Color(0xFF37C98A)),
            title: Text(tr('الفريق كامل', 'Whole team'), style: const TextStyle(color: Colors.white)),
            onTap: () => Navigator.pop(_, 'all')),
        ListTile(leading: const Icon(Icons.person_search_rounded, color: Color(0xFF4AA8FF)),
            title: Text(tr('اختيار أعضاء محدّدين', 'Pick specific members'), style: const TextStyle(color: Colors.white)),
            onTap: () => Navigator.pop(_, 'pick')),
        const SizedBox(height: 8),
      ])));
    if (choice == null) return null;
    if (choice == 'all') return const [];
    // Fetch team members and pick those who have a user_id
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
        Padding(padding: const EdgeInsets.all(14), child: Text(tr('اختر المشاهدين', 'Choose viewers'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
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
                onPressed: () => Navigator.pop(_, true), child: Text(tr('بث للمحدّدين (${selected.length})', 'Broadcast to selected (${selected.length})'))))),
      ]))));
    if (ok != true) return null;
    return selected.toList();
  }

  /// Open the in-app live stream viewing screen (WebRTC). [isClient] uses the client's
  /// scope-restricted endpoint.
  static void watch(BuildContext context, int incidentId, {String? title, bool isClient = false}) {
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => StreamViewScreen(incidentId: incidentId, isClient: isClient)));
  }

  /// Dialog when an active stream exists: return to it / stop it and start a new one / cancel.
  static Future<String?> _activeStreamDialog(BuildContext context) {
    return showModalBottomSheet<String>(context: context, backgroundColor: const Color(0xFF152238),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.fromLTRB(14, 16, 14, 4),
            child: Text(tr('لديك بثّ مباشر نشط', 'You have an active live broadcast'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Text(tr('لا يمكن تشغيل بثّين معاً. اختر:', 'You cannot run two broadcasts at once. Choose:'), style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12.5))),
        const SizedBox(height: 8),
        ListTile(leading: const Icon(Icons.videocam_rounded, color: Color(0xFFE5484D)),
            title: Text(tr('العودة للبثّ الحالي', 'Return to the current broadcast'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            onTap: () => Navigator.pop(_, 'resume')),
        ListTile(leading: const Icon(Icons.stop_circle_rounded, color: Color(0xFFF7A23B)),
            title: Text(tr('إيقاف الحالي وبدء بثّ جديد', 'Stop the current one and start a new broadcast'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            onTap: () => Navigator.pop(_, 'stop')),
        ListTile(leading: const Icon(Icons.close_rounded, color: Color(0xFF9CB2CD)),
            title: Text(tr('إلغاء', 'Cancel'), style: const TextStyle(color: Color(0xFF9CB2CD))),
            onTap: () => Navigator.pop(_, null)),
        const SizedBox(height: 8),
      ])));
  }

  static void _err(BuildContext c, String m) => ScaffoldMessenger.of(c).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: const Color(0xFFE11D48)));
}
