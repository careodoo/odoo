import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import 'notifications_screen.dart';
import 'workorders_screen.dart';
import 'attendance_screen.dart';
import 'employee_attendance_screen.dart';

/// "إنجازاتي" — the worker's own professional dashboard: a performance score
/// ring, period filters, KPI cards (tasks / on-time / attendance hours /
/// materials / rounds), earned badges, and quick links to their files. Replaces
/// the plain notifications tab for every worker.
class MyProfileScreen extends StatefulWidget {
  const MyProfileScreen({super.key});
  @override
  State<MyProfileScreen> createState() => _MyProfileScreenState();
}

class _MyProfileScreenState extends State<MyProfileScreen> {
  String _period = 'month';
  Future<Map<String, dynamic>>? _future;

  static const _periods = [
    ('today', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'), ('all', 'الكل', 'All'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _future = context.read<AuthProvider>().api.meAchievements(period: _period));

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final st = ServiceTheme.of(p.role);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: RefreshIndicator(
        color: st.accent,
        onRefresh: () async => _load(),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.only(top: 120), child: CircularProgressIndicator()));
            final d = snap.data!;
            if (d['has_employee'] == false) {
              return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا يوجد ملف موظف مرتبط', 'No linked employee file'), style: TextStyle(color: Colors.grey.shade500)))]);
            }
            final t = (d['tasks'] as Map?) ?? {};
            final att = (d['attendance'] as Map?) ?? {};
            final mat = (d['materials'] as Map?) ?? {};
            final sch = (d['schedule'] as Map?) ?? {};
            final badges = (d['badges'] as List?) ?? [];
            final score = ((d['score'] as num?) ?? 0).toDouble();
            return ListView(padding: EdgeInsets.zero, children: [
              _header(context, p, st, d, score),
              Padding(padding: const EdgeInsets.fromLTRB(12, 12, 12, 4), child: _periodBar(st.accent)),
              Padding(padding: const EdgeInsets.all(12), child: Column(children: [
                GridView.count(
                  crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.92,
                  children: [
                    StatCard(label: tr('مهام منجزة', 'Done'), value: _i(t['done']), color: const Color(0xFF16A34A), icon: Icons.check_circle_rounded, onTap: _openTasks),
                    StatCard(label: tr('في الوقت', 'On time'), value: _i(t['on_time']), color: const Color(0xFF0891B2), icon: Icons.timer_rounded, onTap: _openTasks),
                    StatCard(label: tr('متأخرة', 'Overdue'), value: _i(t['overdue']), color: const Color(0xFFE11D48), icon: Icons.warning_amber_rounded, onTap: _openTasks),
                    StatCard(label: tr('ساعات العمل', 'Hours'), value: _i(att['hours']), color: const Color(0xFF7C3AED), icon: Icons.schedule_rounded, onTap: _openAttendance),
                    StatCard(label: tr('أيام حضور', 'Days'), value: _i(att['days']), color: const Color(0xFFF59E0B), icon: Icons.event_available_rounded, onTap: _openAttendance),
                    StatCard(label: tr('مواد مصروفة', 'Materials'), value: _i(mat['count']), color: const Color(0xFF0E7490), icon: Icons.inventory_2_rounded, onTap: null),
                  ],
                ),
                const SizedBox(height: 12),
                _bars(t, sch),
                if (badges.isNotEmpty) ...[const SizedBox(height: 14), _badges(badges)],
                const SizedBox(height: 14),
                _quickLinks(st.accent),
                const SizedBox(height: 24),
              ])),
            ]);
          },
        ),
      ),
    );
  }

  Widget _header(BuildContext context, dynamic p, ServiceTheme st, Map d, double score) {
    final emp = (d['employee'] as Map?) ?? {};
    final onTime = ((d['tasks'] as Map?)?['on_time_rate'] as num?)?.toDouble() ?? 0;
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 0, 12, 20),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [st.accent, Color.lerp(st.accent, Colors.black, 0.4)!], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: SafeArea(bottom: false, child: Column(children: [
          Row(children: [
            Expanded(child: Text(tr('إنجازاتي', 'My achievements'), style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900))),
            Stack(clipBehavior: Clip.none, children: [
              Material(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(13),
                child: InkWell(borderRadius: BorderRadius.circular(13),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen())),
                  child: Container(width: 40, height: 40, alignment: Alignment.center, child: const Icon(Icons.notifications_rounded, color: Colors.white, size: 20)))),
              if (p.unreadNotifications > 0) Positioned(right: -4, top: -4, child: Container(
                padding: const EdgeInsets.all(4), decoration: const BoxDecoration(color: Color(0xFFFBBF24), shape: BoxShape.circle),
                child: Text('${p.unreadNotifications}', style: const TextStyle(color: Color(0xFF7C2D12), fontSize: 9, fontWeight: FontWeight.w900)))),
            ]),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            _scoreRing(score),
            const SizedBox(width: 16),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${emp['name'] ?? p.name}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              const SizedBox(height: 3),
              if (emp['job'] != null) Text('${emp['job']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.verified_rounded, color: Colors.white, size: 13), const SizedBox(width: 5),
                  Text('${st.label} · ${onTime.toStringAsFixed(0)}% ${tr('التزام', 'on-time')}', style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
                ]),
              ),
            ])),
          ]),
        ])),
      ),
    );
  }

  Widget _scoreRing(double score) => SizedBox(
        width: 78, height: 78,
        child: Stack(alignment: Alignment.center, children: [
          SizedBox(width: 78, height: 78, child: CustomPaint(painter: _RingPainter(score / 100.0))),
          Column(mainAxisSize: MainAxisSize.min, children: [
            Text(score.toStringAsFixed(0), style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900, height: 1)),
            Text(tr('الأداء', 'Score'), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9, fontWeight: FontWeight.w700)),
          ]),
        ]),
      );

  Widget _periodBar(Color accent) => SizedBox(
        height: 38,
        child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final p in _periods) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: ChoiceChip(
              selected: _period == p.$1,
              label: Text(tr(p.$2, p.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _period == p.$1 ? Colors.white : const Color(0xFF0E3A5F))),
              selectedColor: accent, backgroundColor: Colors.white,
              side: BorderSide(color: _period == p.$1 ? accent : Colors.grey.shade300),
              onSelected: (_) { setState(() => _period = p.$1); _load(); },
            ),
          ),
        ]),
      );

  Widget _bars(Map t, Map sch) {
    final onTime = (t['on_time_rate'] as num?)?.toDouble() ?? 0;
    final comp = (sch['compliance'] as num?)?.toDouble() ?? 0;
    final schTotal = _i(sch['done']) + _i(sch['late']) + _i(sch['missed']);
    return Column(children: [
      _barRow(tr('الالتزام بالمواعيد', 'On-time completion'), onTime, const Color(0xFF16A34A)),
      if (schTotal > 0) ...[const SizedBox(height: 10), _barRow(tr('التزام الجولات المجدولة', 'Scheduled rounds'), comp, const Color(0xFF0891B2))],
    ]);
  }

  Widget _barRow(String label, double pct, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Color(0xFF0E3A5F)))),
            Text('${pct.toStringAsFixed(0)}%', style: TextStyle(fontWeight: FontWeight.w900, color: c)),
          ]),
          const SizedBox(height: 8),
          ClipRRect(borderRadius: BorderRadius.circular(6), child: LinearProgressIndicator(value: pct / 100.0, minHeight: 8, backgroundColor: Colors.grey.shade200, valueColor: AlwaysStoppedAnimation(c))),
        ]),
      );

  Widget _badges(List badges) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [const Icon(Icons.emoji_events_rounded, size: 17, color: Color(0xFFF59E0B)), const SizedBox(width: 7),
            Text(tr('أوسمة الإنجاز', 'Earned badges'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF0E3A5F)))]),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final b in badges) Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20), border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35))),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text('${(b as Map)['icon'] ?? '🏅'}', style: const TextStyle(fontSize: 15)), const SizedBox(width: 6),
                Text('${b['label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: Color(0xFF92400E))),
              ]),
            ),
          ]),
        ]),
      );

  Widget _quickLinks(Color accent) => Column(children: [
        _link(Icons.assignment_rounded, tr('مهامي وأوامر العمل', 'My tasks & work orders'), accent, _openTasks),
        _link(Icons.fingerprint_rounded, tr('سجل حضوري وانصرافي', 'My attendance record'), const Color(0xFF7C3AED), _openAttendance),
      ]);

  Widget _link(IconData ic, String label, Color c, VoidCallback onTap) => Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: ListTile(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          leading: Container(width: 40, height: 40, decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)), child: Icon(ic, color: c, size: 20)),
          title: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
          trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
          onTap: onTap,
        ),
      );

  void _openTasks() => Navigator.push(context, MaterialPageRoute(builder: (_) => const WorkOrdersScreen()));
  void _openAttendance() {
    final p = context.read<AuthProvider>().profile!;
    if (p.role != 'client' && p.employeeId != null) {
      Navigator.push(context, MaterialPageRoute(builder: (_) =>
          EmployeeAttendanceScreen(employeeId: p.employeeId!, name: p.name)));
    } else {
      Navigator.push(context, MaterialPageRoute(builder: (_) => const AttendanceScreen()));
    }
  }
}

int _i(dynamic v) => v is int ? v : (v is num ? v.round() : int.tryParse('$v') ?? 0);

class _RingPainter extends CustomPainter {
  _RingPainter(this.frac);
  final double frac;
  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2 - 5;
    final bg = Paint()..style = PaintingStyle.stroke..strokeWidth = 7..color = Colors.white24..strokeCap = StrokeCap.round;
    final fg = Paint()..style = PaintingStyle.stroke..strokeWidth = 7..color = Colors.white..strokeCap = StrokeCap.round;
    canvas.drawCircle(c, r, bg);
    canvas.drawArc(Rect.fromCircle(center: c, radius: r), -math.pi / 2, 2 * math.pi * frac.clamp(0.0, 1.0), false, fg);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.frac != frac;
}
