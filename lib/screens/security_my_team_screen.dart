import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:geolocator/geolocator.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'chat_screen.dart';

/// «فريقي» — الحارس يرى أعضاء فريقه فقط: بطاقات احترافية قابلة للضغط تفتح ملفّ
/// العضو (بياناته + حالته: وردية/دورية/مهمة + موقعه) مع شات مباشر واتصال، وترويسة
/// «موقعي الآن» من GPS الجهاز (تُرسَل أيضاً كنبضة موقع للخادم).
class SecurityMyTeamScreen extends StatefulWidget {
  const SecurityMyTeamScreen({super.key});
  @override
  State<SecurityMyTeamScreen> createState() => _SecurityMyTeamScreenState();
}

class _SecurityMyTeamScreenState extends State<SecurityMyTeamScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _data;
  bool _loading = true;
  Position? _myPos;
  String? _posErr;

  @override
  void initState() {
    super.initState();
    _load();
    _locate();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.securityMyTeam();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// موقعي الآن من GPS الجهاز، ونرسله كنبضة موقع للخادم (يظهر لبقية الفريق).
  Future<void> _locate() async {
    final api = context.read<AuthProvider>().api; // نلتقطه قبل أي await
    try {
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        if (mounted) setState(() => _posErr = tr('صلاحية الموقع مرفوضة', 'Location permission denied'));
        return;
      }
      final p = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(accuracy: LocationAccuracy.high));
      if (mounted) setState(() { _myPos = p; _posErr = null; });
      // نبضة موقع للخادم
      try {
        await api.securityGuardHeartbeat(lat: p.latitude, lng: p.longitude, moving: true);
      } catch (_) {}
    } catch (e) {
      if (mounted) setState(() => _posErr = tr('تعذّر تحديد الموقع', 'Could not get location'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final teams = ((_data?['teams'] as List?) ?? const []).cast<Map>();
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(
        title: Text(tr('فريقي', 'My team')),
        backgroundColor: _navy,
        actions: [IconButton(onPressed: () { _load(); _locate(); }, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () async { await _load(); await _locate(); },
              child: ListView(padding: const EdgeInsets.all(12), children: [
                _myLocationCard(),
                const SizedBox(height: 12),
                if (teams.isEmpty) _empty() else for (final t in teams) _teamCard(t),
              ]),
            ),
    );
  }

  Widget _myLocationCard() {
    final has = _myPos != null;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF12324E), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF25405F)),
      ),
      child: Row(children: [
        Container(width: 42, height: 42, decoration: BoxDecoration(color: _blue.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.my_location_rounded, color: _blue)),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('موقعي الآن', 'My location'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13)),
          const SizedBox(height: 2),
          Text(has ? '${_myPos!.latitude.toStringAsFixed(5)}, ${_myPos!.longitude.toStringAsFixed(5)}'
                   : (_posErr ?? tr('جارٍ التحديد…', 'Locating…')),
              style: const TextStyle(color: _muted, fontSize: 12, fontFeatures: [])),
        ])),
        if (has)
          IconButton(
            onPressed: () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=${_myPos!.latitude},${_myPos!.longitude}'),
                mode: LaunchMode.externalApplication),
            icon: const Icon(Icons.map_rounded, color: _green)),
      ]),
    );
  }

  Widget _empty() => Padding(
        padding: const EdgeInsets.only(top: 90),
        child: Column(children: [
          const Icon(Icons.groups_rounded, size: 80, color: Color(0xFF2A3B54)),
          const SizedBox(height: 12),
          Text(tr('لست عضواً في أي فريق أمني.', 'You are not a member of any security team.'),
              textAlign: TextAlign.center, style: const TextStyle(color: _muted)),
        ]),
      );

  Widget _teamCard(Map t) {
    final members = ((t['members'] as List?) ?? const []).cast<Map>();
    final st = (t['stats'] as Map?) ?? const {};
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFF20344E))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Text('🛡️', style: TextStyle(fontSize: 22)),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${t['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
                Text([t['premise'], t['client'], t['shift_type']].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
              ])),
              Text('${t['member_count'] ?? members.length}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
            ]),
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 6, children: [
              _stat('${st['online'] ?? 0}', tr('متاح', 'Online'), _green),
              _stat('${st['on_shift'] ?? 0}', tr('في وردية', 'On shift'), _blue),
              _stat('${st['on_patrol'] ?? 0}', tr('دورية', 'Patrol'), _amber),
              _stat('${st['busy'] ?? 0}', tr('مشغول', 'Busy'), _red),
            ]),
          ]),
        ),
        for (final m in members) _memberRow(m),
        const SizedBox(height: 6),
      ]),
    );
  }

  Widget _stat(String v, String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(10), border: Border.all(color: c.withValues(alpha: 0.35))),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 13)),
          const SizedBox(width: 5),
          Text(label, style: TextStyle(color: c.withValues(alpha: 0.9), fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      );

  Color _presenceColor(Map m) {
    if (m['busy'] == true) return _amber;
    switch ('${m['presence'] ?? ''}') {
      case 'active': return _green;
      case 'idle': return _amber;
      case 'sleep': return const Color(0xFF8B5CF6);
      case 'offline': return const Color(0xFF64748B);
    }
    return m['available'] == true ? _green : const Color(0xFF64748B);
  }

  Widget _avatar(Map m, double r) {
    final b64 = '${m['photo_b64'] ?? ''}';
    Widget fallback() => CircleAvatar(radius: r, backgroundColor: const Color(0xFF2A3B54),
        child: Text('${m['name'] ?? '?'}'.characters.first, style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: r * 0.8)));
    if (b64.isEmpty) return fallback();
    try {
      return CircleAvatar(radius: r, backgroundColor: const Color(0xFF2A3B54), backgroundImage: MemoryImage(base64Decode(b64)));
    } catch (_) { return fallback(); }
  }

  Widget _memberRow(Map m) {
    final chips = <Widget>[];
    if (m['on_shift'] == true) chips.add(_miniChip(tr('وردية', 'Shift'), _blue));
    if (m['on_patrol'] == true) chips.add(_miniChip(tr('دورية', 'Patrol'), _amber));
    if (m['active_task'] != null) chips.add(_miniChip(tr('مهمة', 'Task'), _red));
    return InkWell(
      onTap: () => _openMember(m),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(children: [
          Stack(children: [
            _avatar(m, 23),
            Positioned(right: 0, bottom: 0, child: Container(width: 13, height: 13,
                decoration: BoxDecoration(color: _presenceColor(m), shape: BoxShape.circle, border: Border.all(color: _card, width: 2)))),
          ]),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(child: Text('${m['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5))),
              if (m['is_leader'] == true) _tag(tr('قائد', 'Lead'), _amber),
              if (m['is_me'] == true) _tag(tr('أنا', 'Me'), _blue),
            ]),
            const SizedBox(height: 3),
            Row(children: [
              Flexible(child: Text([m['role'], m['rank'], if (m['badge'] != null) '#${m['badge']}'].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11))),
              ...chips.map((c) => Padding(padding: const EdgeInsets.only(right: 4), child: c)),
            ]),
          ])),
          const Icon(Icons.chevron_left_rounded, color: Color(0xFF3A5170)),
        ]),
      ),
    );
  }

  Widget _tag(String s, Color c) => Container(
        margin: const EdgeInsetsDirectional.only(start: 6),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(6)),
        child: Text(s, style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w800)),
      );

  Widget _miniChip(String s, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(6)),
        child: Text(s, style: TextStyle(color: c, fontSize: 9.5, fontWeight: FontWeight.w800)),
      );

  void _openMember(Map m) {
    showModalBottomSheet(
      context: context, backgroundColor: _card, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _MemberSheet(m: m, self: m['is_me'] == true),
    );
  }
}

// ============ ورقة تفاصيل العضو ============
class _MemberSheet extends StatelessWidget {
  final Map m;
  final bool self;
  const _MemberSheet({required this.m, required this.self});

  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);

  @override
  Widget build(BuildContext context) {
    final b64 = '${m['photo_b64'] ?? ''}';
    ImageProvider? img;
    if (b64.isNotEmpty) { try { img = MemoryImage(base64Decode(b64)); } catch (_) {} }
    final hasLoc = (m['lat'] != null && m['lng'] != null &&
        '${m['lat']}' != '0.0' && '${m['lng']}' != '0.0');
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(height: 10),
          Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFF34506F), borderRadius: BorderRadius.circular(3))),
          const SizedBox(height: 16),
          CircleAvatar(radius: 42, backgroundColor: const Color(0xFF2A3B54), backgroundImage: img,
              child: img == null ? Text('${m['name'] ?? '?'}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 30)) : null),
          const SizedBox(height: 10),
          Text('${m['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          if (m['role'] != null || m['rank'] != null)
            Padding(padding: const EdgeInsets.only(top: 3),
                child: Text([m['role'], m['rank']].where((x) => x != null).join(' · '), style: const TextStyle(color: _muted, fontSize: 12.5))),
          const SizedBox(height: 12),
          // شرائح الحالة
          Wrap(spacing: 7, runSpacing: 7, alignment: WrapAlignment.center, children: [
            if (m['on_shift'] == true) _pill(tr('في وردية', 'On shift'), _blue, Icons.badge_rounded),
            if (m['on_patrol'] == true) _pill(tr('في دورية', 'On patrol'), const Color(0xFFF7A23B), Icons.directions_walk_rounded),
            if (m['active_task'] != null) _pill('${tr('مهمة', 'Task')}: ${m['active_task']}', const Color(0xFFE5484D), Icons.assignment_rounded),
            if (m['presence'] != null) _pill(_presenceLabel('${m['presence']}'), _green, Icons.circle),
            if (m['on_shift'] != true && m['on_patrol'] != true && m['active_task'] == null)
              _pill(tr('متفرّغ', 'Available'), _green, Icons.check_circle_rounded),
          ]),
          const SizedBox(height: 16),
          _row(Icons.badge_outlined, tr('رقم الشارة', 'Badge'), m['badge']),
          _row(Icons.work_outline_rounded, tr('المسمى', 'Job'), m['job_title']),
          _row(Icons.credit_card_rounded, tr('الرقم المدني', 'Civil ID'), m['civil_id']),
          _row(Icons.flag_outlined, tr('الجنسية', 'Nationality'), m['nationality']),
          _row(Icons.phone_outlined, tr('الهاتف', 'Phone'), m['phone']),
          _row(Icons.email_outlined, tr('البريد', 'Email'), m['email']),
          _row(Icons.verified_user_outlined, tr('الترخيص', 'License'), m['license']),
          _row(Icons.schedule_rounded, tr('آخر ظهور', 'Last seen'), m['last_seen']),
          if (hasLoc) _row(Icons.location_on_outlined, tr('الموقع', 'Location'), '${m['lat']}, ${m['lng']}'),
          const SizedBox(height: 14),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
            child: Row(children: [
              if (!self && m['user_id'] != null)
                Expanded(child: _btn(tr('مراسلة', 'Chat'), Icons.chat_bubble_rounded, _blue, () {
                  Navigator.pop(context);
                  Navigator.push(context, MaterialPageRoute(builder: (_) =>
                      ChatScreen(peerUid: m['user_id'] as int, peerName: '${m['name'] ?? ''}')));
                })),
              if (!self && m['phone'] != null) ...[
                const SizedBox(width: 10),
                Expanded(child: _btn(tr('اتصال', 'Call'), Icons.call_rounded, _green,
                    () => launchUrl(Uri.parse('tel:${m['phone']}')))),
              ],
              if (hasLoc) ...[
                const SizedBox(width: 10),
                Expanded(child: _btn(tr('الخريطة', 'Map'), Icons.map_rounded, const Color(0xFFF7A23B),
                    () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=${m['lat']},${m['lng']}'), mode: LaunchMode.externalApplication))),
              ],
            ]),
          ),
        ]),
      ),
    );
  }

  String _presenceLabel(String s) {
    switch (s) {
      case 'active': return tr('نشط', 'Active');
      case 'idle': return tr('خامل', 'Idle');
      case 'sleep': return tr('نائم', 'Asleep');
      case 'offline': return tr('غير متصل', 'Offline');
    }
    return s;
  }

  Widget _pill(String s, Color c, IconData ic) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.4))),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, color: c, size: 13), const SizedBox(width: 5),
          Text(s, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
        ]),
      );

  Widget _row(IconData ic, String label, dynamic val) {
    if (val == null || '$val'.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
      child: Row(children: [
        Icon(ic, size: 17, color: _muted),
        const SizedBox(width: 12),
        Text(label, style: const TextStyle(color: _muted, fontSize: 12.5)),
        const Spacer(),
        Flexible(child: Text('$val', textAlign: TextAlign.end, maxLines: 2, overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
      ]),
    );
  }

  Widget _btn(String s, IconData ic, Color c, VoidCallback onTap) => ElevatedButton.icon(
        onPressed: onTap,
        icon: Icon(ic, size: 17),
        label: Text(s, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
        style: ElevatedButton.styleFrom(backgroundColor: c, foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
      );
}
