import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «فريقي / الحرّاس» — a guard sees ONLY the members of the team(s) they belong
/// to, each with photo, role, presence and contact. (Chat + live location land
/// in the real-time phase.)
class SecurityMyTeamScreen extends StatefulWidget {
  const SecurityMyTeamScreen({super.key});
  @override
  State<SecurityMyTeamScreen> createState() => _SecurityMyTeamScreenState();
}

class _SecurityMyTeamScreenState extends State<SecurityMyTeamScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.securityMyTeam();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final teams = ((_data?['teams'] as List?) ?? const []).cast<Map>();
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('فريقي', 'My team')), backgroundColor: _navy),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : teams.isEmpty
              ? _empty()
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(12), children: [
                    for (final t in teams) _teamCard(t),
                  ]),
                ),
    );
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 120),
        const Icon(Icons.groups_rounded, size: 80, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لست عضواً في أي فريق أمني.', 'You are not a member of any security team.'),
            textAlign: TextAlign.center, style: const TextStyle(color: _muted))),
      ]);

  Widget _teamCard(Map t) {
    final members = ((t['members'] as List?) ?? const []).cast<Map>();
    final online = members.where((m) => m['available'] == true).length;
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // team header
        Container(
          padding: const EdgeInsets.all(14),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          ),
          child: Row(children: [
            const Text('🛡️', style: TextStyle(fontSize: 22)),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${t['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
              Text([t['premise'], t['client'], t['shift_type']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
            ])),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text('${t['member_count'] ?? members.length}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
              Text('$online ${tr('متاح', 'online')}', style: const TextStyle(color: Color(0xFF37C98A), fontSize: 10, fontWeight: FontWeight.w700)),
            ]),
          ]),
        ),
        for (final m in members) _memberRow(m),
        const SizedBox(height: 6),
      ]),
    );
  }

  Widget _memberRow(Map m) {
    final avail = m['available'] == true;
    final b64 = '${m['photo_b64'] ?? ''}';
    Widget avatar() {
      Widget fallback() => CircleAvatar(radius: 22, backgroundColor: const Color(0xFF2A3B54),
          child: Text('${m['name'] ?? '?'}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)));
      if (b64.isEmpty) return fallback();
      try {
        return CircleAvatar(radius: 22, backgroundColor: const Color(0xFF2A3B54), backgroundImage: MemoryImage(base64Decode(b64)));
      } catch (_) { return fallback(); }
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      child: Row(children: [
        Stack(children: [
          avatar(),
          Positioned(right: 0, bottom: 0, child: Container(width: 12, height: 12,
              decoration: BoxDecoration(color: avail ? const Color(0xFF37C98A) : const Color(0xFF64748B),
                  shape: BoxShape.circle, border: Border.all(color: _card, width: 2)))),
        ]),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Flexible(child: Text('${m['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13))),
            if (m['is_leader'] == true) Container(margin: const EdgeInsetsDirectional.only(start: 6),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(color: const Color(0xFFF7A23B).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(6)),
                child: Text(tr('قائد', 'Lead'), style: const TextStyle(color: Color(0xFFF7A23B), fontSize: 9, fontWeight: FontWeight.w800))),
            if (m['is_me'] == true) Container(margin: const EdgeInsetsDirectional.only(start: 6),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(color: const Color(0xFF4AA8FF).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(6)),
                child: Text(tr('أنا', 'Me'), style: const TextStyle(color: Color(0xFF4AA8FF), fontSize: 9, fontWeight: FontWeight.w800))),
          ]),
          Text([m['role'], if (m['shift'] != null) m['shift'], if (m['badge'] != null) '#${m['badge']}'].where((x) => x != null).join(' · '),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
        ])),
        if (m['phone'] != null && m['is_me'] != true)
          IconButton(
            icon: const Icon(Icons.call_rounded, color: Color(0xFF37C98A), size: 20),
            onPressed: () => launchUrl(Uri.parse('tel:${m['phone']}')),
          ),
      ]),
    );
  }
}
