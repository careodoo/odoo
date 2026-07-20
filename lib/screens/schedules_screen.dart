import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'schedule_create.dart';

/// جدولة الأعمال — recurring task schedules with compliance. Each card opens a
/// professional detail sheet (its occurrence history), and the client can add
/// new schedules.
class SchedulesScreen extends StatefulWidget {
  const SchedulesScreen({super.key});
  @override
  State<SchedulesScreen> createState() => _SchedulesScreenState();
}

class _SchedulesScreenState extends State<SchedulesScreen> {
  late Future<List<dynamic>> _future;
  static const _accent = Color(0xFF0D9488);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientSchedules();

  Color _cc(num c) => c >= 90 ? const Color(0xFF16A34A) : c >= 70 ? const Color(0xFFF59E0B) : const Color(0xFFE11D48);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _accent, foregroundColor: Colors.white,
        icon: const Icon(Icons.add_rounded),
        label: Text(tr('جدول جديد', 'New schedule'), style: const TextStyle(fontWeight: FontWeight.w900)),
        onPressed: () async {
          final created = await ScheduleCreateSheet.open(context);
          if (created == true && mounted) setState(_load);
        },
      ),
      appBar: AppBar(title: Text(tr('جدولة الأعمال', 'Work schedules')),
          backgroundColor: _accent, foregroundColor: Colors.white),
      body: RefreshIndicator(
        color: _accent,
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _accent));
            final s = snap.data!;
            if (s.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 120),
                Icon(Icons.event_repeat_rounded, size: 60, color: Colors.grey.shade300),
                const SizedBox(height: 12),
                Center(child: Text(tr('لا جداول عمل بعد — أضف جدولاً', 'No schedules yet — add one'),
                    style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
              ]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
              itemCount: s.length,
              itemBuilder: (_, i) => _card(s[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map x) {
    final comp = numOf(x['compliance'], 0);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 7, offset: const Offset(0, 3))],
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openDetail(x['id'] as int, '${x['name']}'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${x['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy))),
              if ('${x['run_state']}' != 'running') ...[_runBadge('${x['run_state']}'), const SizedBox(width: 6)],
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(color: _cc(comp).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                child: Text('$comp%', style: TextStyle(color: _cc(comp), fontWeight: FontWeight.w900)),
              ),
            ]),
            const SizedBox(height: 4),
            Text('📍 ${x['location'] ?? '—'} · 👤 ${x['team'] ?? x['employee'] ?? '—'}',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
            const SizedBox(height: 8),
            _countdown(x),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(value: comp / 100, minHeight: 8, color: _cc(comp), backgroundColor: const Color(0xFFEEF2F7)),
            ),
            const SizedBox(height: 8),
            Row(children: [
              _chip('✅ ${x['done'] ?? 0}', const Color(0xFF16A34A)),
              const SizedBox(width: 6),
              _chip('⏰ ${x['late'] ?? 0}', const Color(0xFFF59E0B)),
              const SizedBox(width: 6),
              _chip('🚫 ${x['missed'] ?? 0}', const Color(0xFFE11D48)),
              const Spacer(),
              Text(_everyLabel(x), style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
              const Icon(Icons.chevron_left_rounded, size: 18, color: Colors.grey),
            ]),
          ]),
        ),
      ),
    );
  }


  /// How long until the next run — the one thing a supervisor opens this
  /// screen to find out, and the one thing it never showed.
  Widget _countdown(Map x) {
    if (x['run_state'] == 'paused' || x['run_state'] == 'stopped') {
      return _banner(Icons.pause_circle_filled_rounded, const Color(0xFF64748B),
          x['run_state'] == 'paused' ? tr('موقوف مؤقتًا', 'Paused') : tr('متوقف', 'Stopped'));
    }
    final due = x['is_due_now'] == true;
    final mins = (x['minutes_to_next'] as num?)?.toInt();
    if (due) {
      return _banner(Icons.notifications_active_rounded, const Color(0xFFE11D48),
          tr('مستحق الآن', 'Due now'));
    }
    if (mins == null) return const SizedBox(height: 2);
    final label = '${x['countdown'] ?? _humanise(mins)}';
    // amber inside the last hour: close enough that somebody should move
    final c = mins <= 60 ? const Color(0xFFF59E0B) : const Color(0xFF0D9488);
    return _banner(Icons.timer_outlined, c,
        '${tr('التالي بعد', 'Next in')} $label'
        '${x['next_run'] != null ? ' · ${x['next_run']}' : ''}');
  }

  Widget _banner(IconData ic, Color c, String t) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.09),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: c.withValues(alpha: 0.25))),
        child: Row(children: [
          Icon(ic, size: 15, color: c),
          const SizedBox(width: 7),
          Expanded(child: Text(t,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: c))),
        ]),
      );

  String _humanise(int mins) {
    if (mins < 60) return tr('$mins دقيقة', '$mins min');
    if (mins < 1440) return tr('${(mins / 60).floor()} ساعة', '${(mins / 60).floor()} h');
    return tr('${(mins / 1440).floor()} يوم', '${(mins / 1440).floor()} d');
  }

  /// The cycle in its own unit — "every 2 days" beats "every 2880m".
  String _everyLabel(Map x) {
    final v = (x['interval_value'] as num?)?.toInt();
    final u = '${x['interval_unit'] ?? ''}';
    if (v != null && v > 0 && u.isNotEmpty) {
      const ar = {'minute': 'دقيقة', 'hour': 'ساعة', 'day': 'يوم', 'week': 'أسبوع', 'month': 'شهر'};
      const en = {'minute': 'min', 'hour': 'h', 'day': 'd', 'week': 'w', 'month': 'mo'};
      return '${tr('كل', 'every')} $v ${tr(ar[u] ?? u, en[u] ?? u)}';
    }
    return '${tr('كل', 'every')} ${x['every_minutes']}${tr('د', 'm')}';
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w700)),
      );

  void _openDetail(int id, String name) {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.82, minChildSize: 0.5, maxChildSize: 0.96,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: context.read<AuthProvider>().api.clientScheduleDetail(id),
          builder: (_, snap) {
            final d = snap.data ?? const {};
            final occ = ((d['occurrences'] as List?) ?? const []).cast<Map>();
            return Container(
              decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
              clipBehavior: Clip.antiAlias,
              child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
                CustomPaint(
                  painter: const BrandPattern(opacity: 0.07),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
                    decoration: BoxDecoration(gradient: LinearGradient(
                        colors: [_accent, Color.lerp(_accent, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                      if (d.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text('${d['service'] ?? ''} · ${d['location'] ?? d['facility'] ?? ''} · 👤 ${d['employee'] ?? '—'}',
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12)),
                        const SizedBox(height: 12),
                        Row(children: [
                          _hStat('${d['compliance'] ?? 0}%', tr('الامتثال', 'Compliance')),
                          _hStat('${d['done'] ?? 0}', tr('منجزة', 'Done')),
                          _hStat('${d['late'] ?? 0}', tr('متأخرة', 'Late')),
                          _hStat('${d['missed'] ?? 0}', tr('فائتة', 'Missed')),
                        ]),
                      ],
                    ]),
                  ),
                ),
                if (snap.connectionState == ConnectionState.waiting)
                  const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: _accent)))
                else Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      _infoPill(Icons.repeat_rounded, tr('كل ${d['every_minutes']} د', 'every ${d['every_minutes']}m')),
                      const SizedBox(width: 8),
                      if (d['window'] != null) _infoPill(Icons.schedule_rounded, '${d['window']}'),
                    ]),
                    const SizedBox(height: 8),
                    Row(children: [
                      if (d['require_presence'] == true) _infoPill(Icons.qr_code_scanner_rounded, tr('إثبات حضور', 'Presence')),
                      const SizedBox(width: 8),
                      if (d['require_photo'] == true) _infoPill(Icons.photo_camera_rounded, tr('صورة إثبات', 'Photo proof')),
                    ]),
                    const SizedBox(height: 14),
                    _controlBar(id, '${d['run_state'] ?? 'running'}', d['pause_until'] as String?),
                    const SizedBox(height: 16),
                    Row(children: [
                      const Icon(Icons.history_rounded, size: 16, color: _accent),
                      const SizedBox(width: 6),
                      Text(tr('سجل التنفيذ (${occ.length})', 'Occurrences (${occ.length})'),
                          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                    ]),
                    const SizedBox(height: 8),
                    if (occ.isEmpty)
                      Padding(padding: const EdgeInsets.all(20), child: Center(
                          child: Text(tr('لا سجلات تنفيذ بعد', 'No occurrences yet'), style: TextStyle(color: Colors.grey.shade500)))),
                    ...occ.map(_occCard),
                  ]),
                ),
              ]),
            );
          },
        ),
      ),
    );
  }

  Widget _runBadge(String state) {
    final m = {
      'paused': (const Color(0xFFF59E0B), Icons.pause_circle_rounded, tr('موقوف مؤقتاً', 'Paused')),
      'stopped': (const Color(0xFF94A3B8), Icons.stop_circle_rounded, tr('موقوف', 'Stopped')),
    }[state];
    if (m == null) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: m.$1.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20), border: Border.all(color: m.$1.withValues(alpha: 0.4))),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(m.$2, size: 13, color: m.$1), const SizedBox(width: 3),
        Text(m.$3, style: TextStyle(color: m.$1, fontSize: 10.5, fontWeight: FontWeight.w900)),
      ]),
    );
  }

  /// Pause (temporarily/permanently), resume or reactivate a schedule.
  Widget _controlBar(int id, String state, String? pauseUntil) {
    final btns = <Widget>[];
    if (state == 'running') {
      btns.add(_ctlBtn(Icons.pause_rounded, tr('إيقاف مؤقت', 'Pause'), const Color(0xFFF59E0B), () => _pause(id)));
      btns.add(_ctlBtn(Icons.stop_rounded, tr('إيقاف نهائي', 'Stop'), const Color(0xFFE11D48), () => _act(id, 'stop', tr('إيقاف هذا الجدول نهائياً؟', 'Stop this schedule permanently?'))));
    } else if (state == 'paused') {
      btns.add(_ctlBtn(Icons.play_arrow_rounded, tr('استئناف', 'Resume'), const Color(0xFF16A34A), () => _act(id, 'resume', null)));
      btns.add(_ctlBtn(Icons.stop_rounded, tr('إيقاف نهائي', 'Stop'), const Color(0xFFE11D48), () => _act(id, 'stop', tr('إيقاف هذا الجدول نهائياً؟', 'Stop this schedule permanently?'))));
    } else {
      btns.add(_ctlBtn(Icons.restart_alt_rounded, tr('إعادة تفعيل', 'Reactivate'), const Color(0xFF16A34A), () => _act(id, 'reactivate', null)));
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (state == 'paused' && pauseUntil != null)
        Padding(padding: const EdgeInsets.only(bottom: 8),
            child: Text(tr('موقوف حتى $pauseUntil', 'Paused until $pauseUntil'),
                style: const TextStyle(color: Color(0xFFF59E0B), fontWeight: FontWeight.w800, fontSize: 12.5))),
      Row(children: [for (final b in btns) Expanded(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 3), child: b))]),
    ]);
  }

  Widget _ctlBtn(IconData ic, String label, Color c, VoidCallback onTap) => OutlinedButton.icon(
        style: OutlinedButton.styleFrom(foregroundColor: c, side: BorderSide(color: c), minimumSize: const Size.fromHeight(46)),
        onPressed: onTap, icon: Icon(ic, size: 18),
        label: Text(label, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
      );

  Future<void> _pause(int id) async {
    final choice = await showModalBottomSheet<String>(context: context, backgroundColor: Colors.transparent, builder: (_) => Container(
      decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      padding: const EdgeInsets.all(16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr('إيقاف الجدول مؤقتاً', 'Pause schedule'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy)),
        const SizedBox(height: 4),
        Text(tr('يتوقف توليد المهام والتنبيهات حتى الاستئناف.', 'Stops generating tasks & alerts until resumed.'),
            style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)),
        const SizedBox(height: 14),
        ListTile(leading: const Icon(Icons.pause_circle_rounded, color: Color(0xFFF59E0B)),
            title: Text(tr('إيقاف مفتوح (حتى الاستئناف يدوياً)', 'Open-ended (until resumed)')),
            onTap: () => Navigator.pop(context, 'open')),
        ListTile(leading: const Icon(Icons.event_rounded, color: Color(0xFF0891B2)),
            title: Text(tr('إيقاف حتى تاريخ محدّد', 'Pause until a date')),
            onTap: () => Navigator.pop(context, 'date')),
      ]),
    ));
    if (choice == null) return;
    String? until;
    if (choice == 'date') {
      final now = DateTime.now();
      final picked = await showDatePicker(context: context, initialDate: now.add(const Duration(days: 7)),
          firstDate: now, lastDate: now.add(const Duration(days: 365)));
      if (picked == null) return;
      until = '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
    }
    await _runAction(id, 'pause', until: until);
  }

  Future<void> _act(int id, String action, String? confirm) async {
    if (confirm != null) {
      final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: Text(tr('تأكيد', 'Confirm')), content: Text(confirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent), onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
        ]));
      if (ok != true) return;
    }
    await _runAction(id, action);
  }

  Future<void> _runAction(int id, String action, {String? until}) async {
    try {
      await context.read<AuthProvider>().api.scheduleAction(id, action, pauseUntil: until);
      if (!mounted) return;
      Navigator.pop(context); // close detail sheet
      setState(_load);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم تحديث حالة الجدول', 'Schedule updated')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Widget _hStat(String v, String l) => Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 9.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _infoPill(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: _accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 13, color: _accent),
          const SizedBox(width: 5),
          Text(t, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: _accent)),
        ]),
      );

  Widget _occCard(Map o) {
    final st = '${o['state']}';
    final c = st == 'done' ? const Color(0xFF16A34A)
        : st == 'late' ? const Color(0xFFF59E0B)
        : st == 'missed' ? const Color(0xFFE11D48) : const Color(0xFF64748B);
    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        Container(width: 4, height: 38, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${(o['planned'] ?? '—')}'.replaceFirst('T', ' '),
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          Text([
            if (o['employee'] != null) '👤 ${o['employee']}',
            if (o['location'] != null) '📍 ${o['location']}',
            if (o['presence'] == true) '✅ ${tr('حضور موثّق', 'presence ok')}',
          ].join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
            child: Text('${o['state_label'] ?? o['state']}', style: TextStyle(color: c, fontSize: 9.5, fontWeight: FontWeight.w900)),
          ),
          if ((o['delay'] ?? 0) != 0) ...[
            const SizedBox(height: 3),
            Text(tr('تأخّر ${o['delay']}د', '${o['delay']}m late'), style: TextStyle(fontSize: 9, color: Colors.grey.shade500)),
          ],
        ]),
      ]),
    );
  }
}
