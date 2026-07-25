import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'security_patrols_screen.dart' show PatrolSheetLauncher;

/// سجل الجولات لكامل مواقع الفريق: خطّ زمني احترافي يُظهر لكل جولة موعدها المجدول
/// مقابل البدء/الإنجاز الفعلي، ومدّتها، ونسبة إنجاز نقاطها، والحارس المنفّذ، وحالتها.
/// أفكار مضمّنة: شريط إحصائي علوي، فلاتر حالة، مؤشّر تأخّر/التزام بالموعد، ونقاط ممسوحة.
class SecurityPatrolLogScreen extends StatefulWidget {
  const SecurityPatrolLogScreen({super.key});
  @override
  State<SecurityPatrolLogScreen> createState() => _SecurityPatrolLogScreenState();
}

class _SecurityPatrolLogScreenState extends State<SecurityPatrolLogScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);
  static const _grey = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _status; // فلتر الحالة

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityPatrolLog(status: _status);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  static const _stColor = {'scheduled': _amber, 'in_progress': _blue, 'completed': _green, 'cancelled': _grey};
  static const _stIcon = {
    'scheduled': Icons.schedule_rounded, 'in_progress': Icons.directions_run_rounded,
    'completed': Icons.check_circle_rounded, 'cancelled': Icons.cancel_rounded,
  };

  @override
  Widget build(BuildContext context) {
    final items = (_data?['items'] as List?) ?? const [];
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: const Color(0xFF1E3A5F), foregroundColor: Colors.white,
          title: Text(tr('سجل الجولات', 'Patrol log')),
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: Column(children: [
        // شريط الإحصاء
        Container(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
          color: const Color(0xFF0F1B2E),
          child: Row(children: [
            _stat('${st['total'] ?? 0}', tr('الكل', 'Total'), _grey),
            _stat('${st['scheduled'] ?? 0}', tr('مجدولة', 'Scheduled'), _amber),
            _stat('${st['in_progress'] ?? 0}', tr('جارية', 'Ongoing'), _blue),
            _stat('${st['completed'] ?? 0}', tr('منجَزة', 'Done'), _green),
          ]),
        ),
        // فلاتر الحالة
        SizedBox(height: 46, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 10), children: [
          _chip(null, tr('الكل', 'All')),
          _chip('scheduled', tr('مجدولة', 'Scheduled')),
          _chip('in_progress', tr('جارية', 'Ongoing')),
          _chip('completed', tr('منجَزة', 'Completed')),
          _chip('cancelled', tr('ملغاة', 'Cancelled')),
        ])),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator(color: _blue))
            : items.isEmpty
                ? _empty()
                : RefreshIndicator(onRefresh: _load, color: _blue,
                    child: ListView.builder(padding: const EdgeInsets.all(12), itemCount: items.length,
                        itemBuilder: (_, i) => _tile(items[i] as Map)))),
      ]),
    );
  }

  Widget _stat(String n, String l, Color c) => Expanded(child: Column(children: [
        Text(n, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 20)),
        Text(l, style: const TextStyle(color: _grey, fontSize: 11)),
      ]));

  Widget _chip(String? v, String label) {
    final sel = _status == v;
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
      child: ChoiceChip(
        label: Text(label), selected: sel,
        onSelected: (_) { setState(() => _status = v); _load(); },
        backgroundColor: _card, selectedColor: _blue,
        labelStyle: TextStyle(color: sel ? Colors.white : _grey, fontWeight: FontWeight.w700, fontSize: 12.5),
        side: BorderSide(color: sel ? _blue : Colors.white.withValues(alpha: .08)),
      ));
  }

  Widget _empty() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.route_rounded, size: 60, color: _grey),
        const SizedBox(height: 10),
        Text(tr('لا جولات في هذا السجل', 'No patrols in this log'), style: const TextStyle(color: _grey, fontWeight: FontWeight.w700)),
      ]));

  Widget _tile(Map p) {
    final state = '${p['state']}';
    final c = _stColor[state] ?? _grey;
    final total = (p['points_total'] as int?) ?? 0;
    final done = (p['points_done'] as int?) ?? 0;
    final comp = (p['completion'] as num?)?.toDouble() ?? (total > 0 ? done / total * 100 : 0);
    final late = _isLate(p);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: .06))),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => PatrolSheetLauncher.open(context, p['id'] as int).then((_) => _load()),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // شريط الحالة العلوي
          Container(width: double.infinity, color: c.withValues(alpha: .16), padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(children: [
              Icon(_stIcon[state] ?? Icons.circle, color: c, size: 15), const SizedBox(width: 6),
              Text('${p['state_label'] ?? state}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
              const Spacer(),
              if ((p['patrol_type'] ?? '').toString().isNotEmpty)
                Text('${p['patrol_type']}', style: const TextStyle(color: _grey, fontSize: 11)),
              if (late) ...[const SizedBox(width: 8), const Icon(Icons.warning_amber_rounded, color: _red, size: 14),
                Text(tr(' متأخّرة', ' Late'), style: const TextStyle(color: _red, fontSize: 11, fontWeight: FontWeight.w800))],
            ])),
          Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.route_rounded, color: _blue, size: 16), const SizedBox(width: 6),
              Expanded(child: Text('${p['route'] ?? p['name'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14.5))),
            ]),
            const SizedBox(height: 6),
            Wrap(spacing: 14, runSpacing: 4, children: [
              if ((p['premise'] ?? '').toString().isNotEmpty) _meta(Icons.place_rounded, '${p['premise']}'),
              if ((p['guard'] ?? '').toString().isNotEmpty) _meta(Icons.person_rounded, '${p['guard']}'),
            ]),
            const SizedBox(height: 10),
            // الخطّ الزمني: مجدول → بدء فعلي → إنجاز فعلي
            _timeline(p),
            const SizedBox(height: 10),
            // شريط إنجاز النقاط
            Row(children: [
              Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(value: (comp / 100).clamp(0.0, 1.0), minHeight: 7,
                    backgroundColor: const Color(0xFF0E1A2E), color: comp >= 100 ? _green : _blue))),
              const SizedBox(width: 10),
              Text('${comp.round()}%  ·  $done/$total', style: const TextStyle(color: _grey, fontSize: 11.5, fontWeight: FontWeight.w700)),
            ]),
          ])),
        ]),
      ),
    );
  }

  Widget _meta(IconData i, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(i, color: _grey, size: 13), const SizedBox(width: 4),
        Text(t, style: const TextStyle(color: _grey, fontSize: 12)),
      ]);

  Widget _timeline(Map p) {
    final sched = '${p['scheduled_start'] ?? ''}';
    final aStart = '${p['actual_start'] ?? ''}';
    final aEnd = '${p['actual_end'] ?? ''}';
    final dur = (p['actual_duration'] as num?)?.toDouble() ?? 0;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: const Color(0xFF0E1A2E), borderRadius: BorderRadius.circular(10)),
      child: Column(children: [
        _tRow(Icons.event_rounded, _amber, tr('المجدول', 'Scheduled'), sched.isEmpty ? '—' : sched),
        _tRow(Icons.play_circle_fill_rounded, _blue, tr('بدأت', 'Started'), aStart.isEmpty ? tr('لم تبدأ', 'Not started') : aStart),
        _tRow(Icons.flag_circle_rounded, _green, tr('أُنجزت', 'Completed'),
            aEnd.isEmpty ? tr('قيد التنفيذ', 'In progress') : '$aEnd${dur > 0 ? '  ·  ${_hm(dur)}' : ''}'),
      ]),
    );
  }

  Widget _tRow(IconData i, Color c, String k, String v) => Padding(padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        Icon(i, color: c, size: 15), const SizedBox(width: 8),
        SizedBox(width: 66, child: Text(k, style: const TextStyle(color: _grey, fontSize: 11.5))),
        Expanded(child: Text(v, style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
      ]));

  String _hm(double hours) {
    final total = (hours * 60).round();
    final h = total ~/ 60, m = total % 60;
    return h > 0 ? tr('$h س $m د', '${h}h ${m}m') : tr('$m د', '${m}m');
  }

  // مؤشّر تأخّر: مجدولة وفات موعدها ولم تبدأ
  bool _isLate(Map p) {
    if (p['state'] != 'scheduled') return false;
    final s = '${p['scheduled_start'] ?? ''}';
    if (s.isEmpty) return false;
    final t = DateTime.tryParse(s.replaceFirst(' ', 'T'));
    return t != null && t.isBefore(DateTime.now());
  }
}
