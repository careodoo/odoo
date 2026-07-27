import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «الأوامر الدائمة / تعليمات الموقع» (Post Orders / SOP) — التعليمات الثابتة لكل
/// موقع يقرؤها الحارس ويُقرّ بالاطلاع عليها. مصنّفة (بوابة/دوريات/طوارئ/إبلاغ).
class SecurityPostOrdersScreen extends StatefulWidget {
  const SecurityPostOrdersScreen({super.key});
  @override
  State<SecurityPostOrdersScreen> createState() => _SecurityPostOrdersScreenState();
}

class _SecurityPostOrdersScreenState extends State<SecurityPostOrdersScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);

  Map<String, dynamic>? _d;
  bool _loading = true;
  String _cat = 'all';

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.securityPostOrders(category: _cat);
      if (mounted) setState(() { _d = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _ack(int id) async {
    try {
      await context.read<AuthProvider>().api.securityPostOrderAck(id);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _green,
          content: Text(tr('تم الإقرار بالاطلاع', 'Acknowledged'))));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e')));
    }
  }

  String _strip(String html) => html.replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
      .replaceAll(RegExp(r'</p>', caseSensitive: false), '\n')
      .replaceAll(RegExp(r'<[^>]*>'), '').replaceAll('&nbsp;', ' ').trim();

  Color _catColor(String? c) {
    switch (c) {
      case 'emergency': return _red;
      case 'access': return _blue;
      case 'patrol': return _amber;
      case 'reporting': return const Color(0xFF7C3AED);
      case 'safety': return _green;
    }
    return _muted;
  }
  IconData _catIcon(String? c) {
    switch (c) {
      case 'emergency': return Icons.emergency_rounded;
      case 'access': return Icons.meeting_room_rounded;
      case 'patrol': return Icons.directions_walk_rounded;
      case 'reporting': return Icons.assignment_rounded;
      case 'safety': return Icons.health_and_safety_rounded;
    }
    return Icons.article_rounded;
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_d?['items'] as List?) ?? const []).cast<Map>();
    final cats = ((_d?['categories'] as List?) ?? const []).cast<Map>();
    final unacked = (_d?['unacked'] ?? 0) as int;
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('الأوامر الدائمة', 'Post orders')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              if (unacked > 0) Container(
                margin: const EdgeInsets.fromLTRB(12, 10, 12, 0), padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: _amber.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(12), border: Border.all(color: _amber.withValues(alpha: 0.4))),
                child: Row(children: [
                  const Icon(Icons.priority_high_rounded, color: _amber, size: 20), const SizedBox(width: 8),
                  Expanded(child: Text('${tr('لديك', 'You have')} $unacked ${tr('تعليمات لم تُقرّ بها بعد', 'un-acknowledged orders')}',
                      style: const TextStyle(color: _amber, fontWeight: FontWeight.w700, fontSize: 12.5))),
                ])),
              if (cats.isNotEmpty) SizedBox(height: 44, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 10), children: [
                _chip(tr('الكل', 'All'), null, _cat == 'all', () => setState(() { _cat = 'all'; _load(); })),
                for (final c in cats) _chip('${c['label']} (${c['count']})', '${c['key']}', _cat == '${c['key']}', () => setState(() { _cat = '${c['key']}'; _load(); })),
              ])),
              Expanded(child: items.isEmpty
                  ? _empty()
                  : RefreshIndicator(onRefresh: _load,
                      child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20), children: [for (final o in items) _orderCard(o)]))),
            ]),
    );
  }

  Widget _chip(String label, String? key, bool active, VoidCallback onTap) {
    final c = key == null ? _blue : _catColor(key);
    return Padding(padding: const EdgeInsets.only(left: 8, top: 6, bottom: 6),
      child: InkWell(onTap: onTap, borderRadius: BorderRadius.circular(20),
        child: Container(padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
          decoration: BoxDecoration(color: active ? c : _card, borderRadius: BorderRadius.circular(20), border: Border.all(color: active ? c : const Color(0xFF2A3B54))),
          child: Text(label, style: TextStyle(color: active ? Colors.white : _muted, fontSize: 12, fontWeight: FontWeight.w700)))));
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100), const Icon(Icons.menu_book_rounded, size: 74, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا أوامر دائمة لموقعك.', 'No post orders for your site.'), style: const TextStyle(color: _muted))),
      ]);

  Widget _orderCard(Map o) {
    final c = _catColor('${o['category']}');
    final acked = o['acknowledged'] == true;
    final crit = '${o['priority']}' == '2';
    final body = _strip('${o['body'] ?? ''}');
    return Container(
      margin: const EdgeInsets.only(bottom: 10), padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: crit ? _red.withValues(alpha: 0.4) : const Color(0xFF20344E))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 38, height: 38, decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(11)),
              child: Icon(_catIcon('${o['category']}'), color: c, size: 19)),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${o['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14)),
            const SizedBox(height: 3),
            Wrap(spacing: 6, children: [
              _tag('${o['category_label']}', c),
              if (crit) _tag(tr('حرِج', 'Critical'), _red),
              if (o['premise'] != null) _tag('${o['premise']}', _muted),
            ]),
          ])),
        ]),
        if (body.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 10),
            child: Text(body, style: const TextStyle(color: Color(0xFFCBD6E6), fontSize: 12.5, height: 1.5))),
        const SizedBox(height: 10),
        Row(children: [
          Icon(Icons.groups_rounded, size: 14, color: _muted), const SizedBox(width: 4),
          Text('${o['ack_count'] ?? 0} ${tr('أقرّوا', 'acked')}', style: const TextStyle(color: _muted, fontSize: 11)),
          const Spacer(),
          if (acked) Row(children: const [Icon(Icons.check_circle_rounded, color: _green, size: 16), SizedBox(width: 4)])
          else ElevatedButton.icon(
            onPressed: () => _ack(o['id'] as int), icon: const Icon(Icons.done_rounded, size: 16),
            label: Text(tr('أقرّ بالاطلاع', 'Acknowledge'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
            style: ElevatedButton.styleFrom(backgroundColor: _blue, foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
          ),
          if (acked) Text(tr('تم الإقرار', 'Acknowledged'), style: const TextStyle(color: _green, fontSize: 11.5, fontWeight: FontWeight.w700)),
        ]),
      ]),
    );
  }

  Widget _tag(String s, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(6)),
        child: Text(s, style: TextStyle(color: c, fontSize: 9.5, fontWeight: FontWeight.w800)),
      );
}
