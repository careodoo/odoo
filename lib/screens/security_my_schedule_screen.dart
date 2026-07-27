import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «جدولي / ورديّاتي» — روستر الحارس: الورديات القادمة والسابقة، بأوقاتها وموقعها
/// وحالتها، مع تسجيل حضور/انصراف مباشر على الوردية.
class SecurityMyScheduleScreen extends StatefulWidget {
  const SecurityMyScheduleScreen({super.key});
  @override
  State<SecurityMyScheduleScreen> createState() => _SecurityMyScheduleScreenState();
}

class _SecurityMyScheduleScreenState extends State<SecurityMyScheduleScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);

  Map<String, dynamic>? _d;
  bool _loading = true, _busy = false;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.securityMySchedule();
      if (mounted) setState(() { _d = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _act(int id, String action) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.securityShiftAction(id, action);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _green,
          content: Text(action == 'checkin' ? tr('تم تسجيل الحضور', 'Checked in') : tr('تم تسجيل الانصراف', 'Checked out'))));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e')));
    } finally { if (mounted) setState(() => _busy = false); }
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_d?['items'] as List?) ?? const []).cast<Map>();
    final st = (_d?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('جدولي', 'My schedule')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              _stats(st),
              Expanded(child: items.isEmpty
                  ? _empty()
                  : RefreshIndicator(onRefresh: _load,
                      child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                          children: [for (final a in items) _card_(a)]))),
            ]),
    );
  }

  Widget _stats(Map st) => Container(
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 6), padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          _s('${st['today'] ?? 0}', tr('اليوم', 'Today'), _green),
          _sep(), _s('${st['upcoming'] ?? 0}', tr('قادمة', 'Upcoming'), _blue),
          _sep(), _s('${st['missed'] ?? 0}', tr('فائتة', 'Missed'), _red),
          _sep(), _s('${st['total'] ?? 0}', tr('الإجمالي', 'Total'), Colors.white),
        ]));
  Widget _sep() => Container(width: 1, height: 30, color: const Color(0xFF2C4258));
  Widget _s(String v, String l, Color c) => Expanded(child: Column(children: [
        Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 19)),
        const SizedBox(height: 2), Text(l, style: const TextStyle(color: _muted, fontSize: 10, fontWeight: FontWeight.w600)),
      ]));

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100),
        const Icon(Icons.event_note_rounded, size: 74, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا ورديّات مجدولة.', 'No scheduled shifts.'), style: const TextStyle(color: _muted))),
      ]);

  Color _stColor(String? s) => s == 'checked_in' ? _green : s == 'checked_out' || s == 'completed' ? _blue
      : s == 'missed' ? _red : s == 'cancelled' ? const Color(0xFF64748B) : _amber;

  Widget _card_(Map a) {
    final col = _stColor('${a['state']}');
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFF20344E))),
      child: Column(children: [
        Padding(padding: const EdgeInsets.all(12), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(width: 4, height: 46, margin: const EdgeInsetsDirectional.only(end: 11),
              decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(3))),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text([a['shift'], a['type']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5))),
              Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: col.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
                  child: Text('${a['state_label'] ?? a['state'] ?? ''}', style: TextStyle(color: col, fontSize: 10, fontWeight: FontWeight.w800))),
            ]),
            const SizedBox(height: 5),
            Row(children: [
              const Icon(Icons.event_rounded, size: 13, color: _muted), const SizedBox(width: 4),
              Text('${a['date'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 11.5)),
              if (a['start'] != null) ...[
                const SizedBox(width: 10), const Icon(Icons.schedule_rounded, size: 13, color: _muted), const SizedBox(width: 4),
                Text('${a['start']} - ${a['end'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 11.5)),
              ],
            ]),
            if (a['premise'] != null) Padding(padding: const EdgeInsets.only(top: 4), child: Row(children: [
              const Icon(Icons.location_on_outlined, size: 13, color: _muted), const SizedBox(width: 4),
              Flexible(child: Text('${a['premise']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11.5))),
            ])),
            if (a['check_in'] != null || a['check_out'] != null || (a['worked_hours'] ?? 0) > 0)
              Padding(padding: const EdgeInsets.only(top: 6), child: Wrap(spacing: 8, runSpacing: 4, children: [
                if (a['check_in'] != null) _mini('${tr('حضور', 'In')}: ${a['check_in']}', _green),
                if (a['check_out'] != null) _mini('${tr('انصراف', 'Out')}: ${a['check_out']}', _blue),
                if ((a['worked_hours'] ?? 0) > 0) _mini('${a['worked_hours']}${tr('س', 'h')}', _amber),
              ])),
          ])),
        ])),
        if (a['can_checkin'] == true || a['can_checkout'] == true)
          Container(
            decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFF20344E)))),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Row(children: [
              if (a['can_checkin'] == true) Expanded(child: _btn(tr('تسجيل حضور', 'Check in'), Icons.login_rounded, _green, () => _act(a['id'] as int, 'checkin'))),
              if (a['can_checkout'] == true) Expanded(child: _btn(tr('تسجيل انصراف', 'Check out'), Icons.logout_rounded, _amber, () => _act(a['id'] as int, 'checkout'))),
            ]),
          ),
      ]),
    );
  }

  Widget _mini(String s, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(6)),
        child: Text(s, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w700)),
      );

  Widget _btn(String s, IconData ic, Color c, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: TextButton.icon(
          onPressed: _busy ? null : onTap, icon: Icon(ic, size: 17, color: c),
          label: Text(s, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
          style: TextButton.styleFrom(backgroundColor: c.withValues(alpha: 0.12), padding: const EdgeInsets.symmetric(vertical: 10),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
        ),
      );
}
