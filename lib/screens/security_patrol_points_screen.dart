import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «نقاط الدوريات» — احترافية: نقاط الفحص مجمّعة حسب المرفق، مع ترويسة إحصائيات
/// (إجمالي/مرافق/مفحوصة اليوم)، تصنيف حسب النوع، وحالة الفحص لكل نقطة (في الموعد/
/// متأخر/فائت) — مستوحاة من الموديل القديم ومطوّرة.
class SecurityPatrolPointsScreen extends StatefulWidget {
  const SecurityPatrolPointsScreen({super.key});
  @override
  State<SecurityPatrolPointsScreen> createState() => _SecurityPatrolPointsScreenState();
}

class _SecurityPatrolPointsScreenState extends State<SecurityPatrolPointsScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _typeFilter;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.securityPatrolPointsByFacility();
      if (mounted) setState(() { _data = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Color _typeColor(String? t) {
    switch (t) {
      case 'checkpoint': return _blue;
      case 'emergency': return _red;
      case 'entrance': return _green;
      case 'patrol': return _amber;
    }
    return _muted;
  }

  IconData _typeIcon(String? t) {
    switch (t) {
      case 'checkpoint': return Icons.qr_code_scanner_rounded;
      case 'emergency': return Icons.emergency_rounded;
      case 'entrance': return Icons.meeting_room_rounded;
      case 'patrol': return Icons.directions_walk_rounded;
    }
    return Icons.place_rounded;
  }

  @override
  Widget build(BuildContext context) {
    final facs = ((_data?['facilities'] as List?) ?? const []).cast<Map>();
    final totals = (_data?['totals'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('نقاط الدوريات', 'Patrol points')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : facs.isEmpty
              ? _empty()
              : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(12), children: [
                  _totalsHeader(totals),
                  const SizedBox(height: 12),
                  for (final f in facs) _facilityCard(f),
                ])),
    );
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 110),
        const Icon(Icons.place_rounded, size: 74, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا نقاط دوريات في مواقعك.', 'No patrol points in your sites.'), style: const TextStyle(color: _muted))),
      ]);

  Widget _totalsHeader(Map totals) {
    final byType = ((totals['by_type'] as List?) ?? const []).cast<Map>();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _tot('${totals['points'] ?? 0}', tr('النقاط', 'Points'), Colors.white),
          _sep(), _tot('${totals['facilities'] ?? 0}', tr('المرافق', 'Facilities'), _blue),
          _sep(), _tot('${totals['checked_today'] ?? 0}', tr('فُحصت اليوم', 'Checked today'), _green),
        ]),
        if (byType.isNotEmpty) ...[
          const SizedBox(height: 12),
          Wrap(spacing: 7, runSpacing: 7, children: [
            _typeChip(null, tr('الكل', 'All'), totals['points'] ?? 0),
            for (final b in byType) _typeChip('${b['type']}', '${b['label']}', b['count'] ?? 0),
          ]),
        ],
      ]),
    );
  }

  Widget _sep() => Container(width: 1, height: 32, color: const Color(0xFF2C4258));
  Widget _tot(String v, String l, Color c) => Expanded(child: Column(children: [
        Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 20)),
        const SizedBox(height: 2),
        Text(l, style: const TextStyle(color: _muted, fontSize: 10, fontWeight: FontWeight.w600)),
      ]));

  Widget _typeChip(String? type, String label, dynamic count) {
    final c = _typeColor(type);
    final active = _typeFilter == type;
    return InkWell(
      onTap: () => setState(() => _typeFilter = active ? null : type),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? c : c.withValues(alpha: 0.13),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: c.withValues(alpha: active ? 1 : 0.35)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (type != null) Icon(_typeIcon(type), size: 13, color: active ? Colors.white : c),
          if (type != null) const SizedBox(width: 4),
          Text('$label ($count)', style: TextStyle(color: active ? Colors.white : c, fontSize: 11, fontWeight: FontWeight.w800)),
        ]),
      ),
    );
  }

  Widget _facilityCard(Map f) {
    var points = ((f['points'] as List?) ?? const []).cast<Map>();
    if (_typeFilter != null) points = points.where((p) => '${p['type']}' == _typeFilter).toList();
    if (points.isEmpty) return const SizedBox.shrink();
    final byType = ((f['by_type'] as List?) ?? const []).cast<Map>();
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFF20344E))),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: true,
          iconColor: _muted, collapsedIconColor: _muted,
          tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
          leading: Container(width: 40, height: 40, decoration: BoxDecoration(color: _blue.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(11)),
              child: const Icon(Icons.business_rounded, color: _blue)),
          title: Text('${f['facility'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
          subtitle: Padding(padding: const EdgeInsets.only(top: 4),
              child: Wrap(spacing: 6, runSpacing: 4, children: [
                _miniTag('${points.length} ${tr('نقطة', 'points')}', _blue),
                for (final b in byType) if (_typeFilter == null || '${b['type']}' == _typeFilter) _miniTag('${b['label']}: ${b['count']}', _typeColor('${b['type']}')),
              ])),
          childrenPadding: const EdgeInsets.only(bottom: 8),
          children: [for (final p in points) _pointRow(p)],
        ),
      ),
    );
  }

  Widget _miniTag(String s, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(6)),
        child: Text(s, style: TextStyle(color: c, fontSize: 9.5, fontWeight: FontWeight.w700)),
      );

  /// وسم الحالة: مفحوصة مرّة واحدة → «تم ✓» أخضر؛ متكرّرة → عدّاد عكسي حتى الفحص
  /// التالي (يُعاد ضبطه مع كل سكان)؛ وإلا «بانتظار».
  (String, Color, IconData) _pointBadge(Map p) {
    final scanned = p['scanned'] == true;
    final recurring = p['recurring'] == true;
    if (recurring) {
      final nc = '${p['next_check'] ?? ''}';
      if (nc.isNotEmpty && nc != 'null') {
        try {
          final due = DateTime.parse(nc.replaceFirst(' ', 'T'));
          final diff = due.difference(DateTime.now());
          if (diff.isNegative) return (tr('مستحق الآن', 'Due now'), _red, Icons.timer_rounded);
          final h = diff.inHours, m = diff.inMinutes % 60;
          final s = h > 0 ? tr('${h}س ${m}د', '${h}h ${m}m') : tr('${m}د', '${m}m');
          return ('${tr('التالي بعد', 'Next in')} $s', _amber, Icons.timer_outlined);
        } catch (_) {}
      }
      if (scanned) return (tr('مفحوصة', 'Scanned'), _green, Icons.check_circle_rounded);
      return (tr('بانتظار', 'Pending'), const Color(0xFF64748B), Icons.timelapse_rounded);
    }
    // مرّة واحدة
    if (scanned) return (tr('تم', 'Done'), _green, Icons.check_circle_rounded);
    return (tr('بانتظار', 'Pending'), const Color(0xFF64748B), Icons.radio_button_unchecked_rounded);
  }

  Widget _pointRow(Map p) {
    final tc = _typeColor('${p['type']}');
    final scanned = p['scanned'] == true;
    final recurring = p['recurring'] == true;
    final badge = _pointBadge(p);
    final done = scanned && !recurring; // منجزة نهائياً (مرّة واحدة)
    final iconC = done ? _green : tc;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: done ? _green.withValues(alpha: 0.06) : const Color(0xFF0F1B2E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: done ? _green.withValues(alpha: 0.35) : const Color(0xFF1E3149)),
      ),
      child: Row(children: [
        Stack(children: [
          Container(width: 38, height: 38, decoration: BoxDecoration(color: iconC.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(10)),
              child: Icon(_typeIcon('${p['type']}'), color: iconC, size: 19)),
          if (scanned) Positioned(right: 0, bottom: 0, child: Container(
              decoration: BoxDecoration(color: _green, shape: BoxShape.circle, border: Border.all(color: const Color(0xFF0F1B2E), width: 1.5)),
              child: const Icon(Icons.check_rounded, size: 11, color: Colors.white))),
        ]),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${p['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13))),
            if (p['has_qr'] == true) const Icon(Icons.qr_code_2_rounded, size: 16, color: _muted),
          ]),
          const SizedBox(height: 3),
          Text([p['code'], p['type_label'], p['floor'], p['unit'], if (recurring && p['interval_h'] != null) tr('⟳ ${p['interval_h']}س', '⟳ ${p['interval_h']}h')]
                  .where((x) => x != null && '$x'.isNotEmpty).join(' · '),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
          const SizedBox(height: 6),
          Row(children: [
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: badge.$2.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(7)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(badge.$3, size: 12, color: badge.$2), const SizedBox(width: 4),
                  Text(badge.$1, style: TextStyle(color: badge.$2, fontSize: 9.5, fontWeight: FontWeight.w800)),
                ])),
            const SizedBox(width: 8),
            if (p['last_check'] != null) Expanded(child: Text('${tr('آخر فحص', 'Last')}: ${p['last_check']}',
                maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFF6B7F9A), fontSize: 9.5))),
          ]),
        ])),
      ]),
    );
  }
}
