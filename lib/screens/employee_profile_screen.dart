import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'employee_attendance_screen.dart';

/// Full worker profile (data sourced from the HR Employees module) plus rich
/// statistics for the client — filterable by day / month / year / all time.
class EmployeeProfileScreen extends StatefulWidget {
  const EmployeeProfileScreen({super.key, required this.employeeId, required this.name});
  final int employeeId;
  final String name;
  @override
  State<EmployeeProfileScreen> createState() => _EmployeeProfileScreenState();
}

class _EmployeeProfileScreenState extends State<EmployeeProfileScreen> {
  String _period = 'month';
  Future<Map<String, dynamic>>? _future;
  Future<Map<String, dynamic>>? _attFuture;

  static const _periods = [
    ('day', 'اليوم', 'Today'),
    ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'),
    ('year', 'السنة', 'Year'),
    ('all', 'الكل', 'All'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<AuthProvider>().api;
    _future = api.clientEmployee(widget.employeeId, period: _period);
    _attFuture = api.clientEmployeeAttendance(widget.employeeId, period: _period)
        .catchError((_) => <String, dynamic>{});
  }

  void _openAttendance() => Navigator.push(context, MaterialPageRoute(
      builder: (_) => EmployeeAttendanceScreen(employeeId: widget.employeeId, name: widget.name)));

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(widget.name)),
      body: Column(children: [
        // period selector
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final p in _periods)
              Padding(
                padding: const EdgeInsets.only(left: 6),
                child: ChoiceChip(
                  label: Text(tr(p.$2, p.$3)),
                  selected: _period == p.$1,
                  onSelected: (_) => setState(() { _period = p.$1; _load(); }),
                ),
              ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<Map<String, dynamic>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) return Center(child: Text('${snap.error}'));
              final d = snap.data ?? const {};
              final p = (d['profile'] as Map?) ?? const {};
              final k = (d['kpis'] as Map?) ?? const {};
              final daily = (d['daily'] as List?) ?? const [];
              final byService = (d['by_service'] as Map?) ?? const {};
              return ListView(padding: const EdgeInsets.all(16), children: [
                _profileCard(p, cs),
                const SizedBox(height: 14),
                _attendanceSummary(),
                const SizedBox(height: 14),
                Text(tr('إحصائيات — ${d['period'] ?? ''}', 'Statistics — ${d['period'] ?? ''}'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                const SizedBox(height: 8),
                _kpiGrid(k),
                const SizedBox(height: 14),
                if (daily.isNotEmpty) ...[
                  Text(tr('النشاط اليومي', 'Daily activity'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                  const SizedBox(height: 8),
                  _MiniBars(daily: daily.cast<Map>()),
                  const SizedBox(height: 14),
                ],
                if (byService.isNotEmpty) ...[
                  Text(tr('حسب الخدمة', 'By service'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                  const SizedBox(height: 8),
                  Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(
                    children: [for (final e in byService.entries) Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(children: [
                        Expanded(child: Text('${e.key}')),
                        Text('${e.value}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      ]),
                    )],
                  ))),
                ],
              ]);
            },
          ),
        ),
      ]),
    );
  }

  /// Compact attendance snapshot inside the profile, with a button through to
  /// the full filterable/printable/exportable records page.
  Widget _attendanceSummary() {
    const navy = Color(0xFF0E3A5F);
    return FutureBuilder<Map<String, dynamic>>(
      future: _attFuture,
      builder: (_, snap) {
        final d = snap.data ?? const {};
        final t = (d['totals'] as Map?) ?? const {};
        final workers = ((d['workers'] as List?) ?? const []).cast<Map>();
        final w = workers.isNotEmpty ? workers.first : const {};
        final records = ((d['records'] as List?) ?? const []).cast<Map>();
        return Container(
          decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(16),
            border: Border.all(color: navy.withValues(alpha: 0.1)),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 6, offset: const Offset(0, 3))],
          ),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
              child: Row(children: [
                const Icon(Icons.fingerprint_rounded, size: 18, color: navy),
                const SizedBox(width: 7),
                Text(tr('الحضور والانصراف', 'Attendance'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: navy)),
                const Spacer(),
                if (snap.connectionState == ConnectionState.waiting)
                  const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(children: [
                _aStat('${w['days'] ?? t['days_covered'] ?? 0}', tr('يوم', 'Days'), const Color(0xFF6366F1)),
                _aStat('${w['shifts'] ?? t['records'] ?? 0}', tr('وردية', 'Shifts'), const Color(0xFF0891B2)),
                _aStat('${w['hours'] ?? t['total_hours'] ?? 0}', tr('ساعة', 'Hours'), const Color(0xFF16A34A)),
                _aStat('${w['avg_hours'] ?? t['avg_hours'] ?? 0}', tr('متوسط', 'Avg'), const Color(0xFFF7A23B)),
              ]),
            ),
            if (records.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 8),
                child: Column(children: [
                  for (final r in records.take(3)) Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(children: [
                      Container(width: 6, height: 6, decoration: BoxDecoration(
                          color: r['open'] == true ? const Color(0xFF16A34A) : Colors.grey.shade400, shape: BoxShape.circle)),
                      const SizedBox(width: 7),
                      Text('${r['date'] ?? '—'}', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
                      const Spacer(),
                      Text('${_hm(r['check_in'])} → ${_hm(r['check_out'])}',
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                      const SizedBox(width: 8),
                      Text(tr('${r['hours'] ?? 0}س', '${r['hours'] ?? 0}h'),
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Color(0xFF0891B2))),
                    ]),
                  ),
                ]),
              ),
            const Divider(height: 1),
            InkWell(
              onTap: _openAttendance,
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 11),
                child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  const Icon(Icons.list_alt_rounded, size: 16, color: Color(0xFFC0392B)),
                  const SizedBox(width: 7),
                  Text(tr('عرض كل سجلات الحضور', 'View all attendance records'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: Color(0xFFC0392B))),
                  const Icon(Icons.chevron_left_rounded, size: 18, color: Color(0xFFC0392B)),
                ]),
              ),
            ),
          ]),
        );
      },
    );
  }

  Widget _aStat(String v, String l, Color c) => Expanded(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(11)),
          child: Column(children: [
            Text(v, style: TextStyle(color: c, fontSize: 16, fontWeight: FontWeight.w900)),
            Text(l, style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
          ]),
        ),
      );

  String _hm(dynamic v) {
    final s = '${v ?? ''}';
    if (s.length < 16) return '—';
    return s.substring(11, 16);
  }

  static const _navy = Color(0xFF0E3A5F);
  static const _brand = Color(0xFF1D6FA3);

  Future<void> _launch(String uri) async {
    try {
      await launchUrl(Uri.parse(uri), mode: LaunchMode.externalApplication);
    } catch (_) {}
  }

  ImageProvider? _avatarOf(Map p) {
    final photo = p['photo'] as String?;
    if (photo != null && photo.startsWith('data:image')) {
      try {
        return MemoryImage(base64Decode(photo.split(',').last));
      } catch (_) {}
    }
    return avatarImage(photo);
  }

  Widget _profileCard(Map p, ColorScheme cs) {
    final name = '${p['name'] ?? ''}';
    final phone = (p['mobile'] as String?) ?? (p['work_phone'] as String?);
    final email = p['work_email'] as String?;
    final img = _avatarOf(p);
    return Column(children: [
      // professional gradient hero
      Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              colors: [_brand, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: _navy.withValues(alpha: 0.3), blurRadius: 14, offset: const Offset(0, 6))],
        ),
        child: Column(children: [
          CircleAvatar(
            radius: 42, backgroundColor: Colors.white24, backgroundImage: img,
            child: img == null
                ? Text(name.isEmpty ? '?' : name.characters.first,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 30))
                : null,
          ),
          const SizedBox(height: 12),
          Text(name, textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
          if (p['job'] != null) ...[
            const SizedBox(height: 3),
            Text('${p['job']}', textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13, fontWeight: FontWeight.w600)),
          ],
          if (p['department'] != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
              child: Text('${p['department']}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 11.5)),
            ),
          ],
          const SizedBox(height: 16),
          // contact quick-actions
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            if (phone != null && phone.isNotEmpty) ...[
              _quick(Icons.call_rounded, tr('اتصال', 'Call'), () => _launch('tel:$phone')),
              const SizedBox(width: 10),
              _quick(Icons.chat_rounded, 'واتساب', () => _launch('https://wa.me/${phone.replaceAll(RegExp(r'[^0-9]'), '')}')),
            ],
            if (email != null && email.isNotEmpty) ...[
              const SizedBox(width: 10),
              _quick(Icons.email_rounded, tr('بريد', 'Email'), () => _launch('mailto:$email')),
            ],
            const SizedBox(width: 10),
            _quick(Icons.fingerprint_rounded, tr('الحضور', 'Attend.'), _openAttendance),
          ]),
        ]),
      ),
      const SizedBox(height: 14),
      // full details card
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Column(children: [
          _detail(Icons.badge_rounded, tr('المسمّى الوظيفي', 'Job title'), p['job'] as String?),
          _detail(Icons.apartment_rounded, tr('القسم', 'Department'), p['department'] as String?),
          _detail(Icons.place_rounded, tr('موقع العمل', 'Work location'), p['work_location'] as String?),
          _detail(Icons.supervisor_account_rounded, tr('المدير المباشر', 'Manager'), p['manager'] as String?),
          _detail(Icons.phone_rounded, tr('هاتف العمل', 'Work phone'), p['work_phone'] as String?),
          _detail(Icons.smartphone_rounded, tr('الجوال', 'Mobile'), p['mobile'] as String?),
          _detail(Icons.email_rounded, tr('البريد', 'Email'), p['work_email'] as String?),
          _detail(Icons.event_available_rounded, tr('تاريخ الالتحاق', 'Joined'), p['joining'] as String?),
        ]),
      ),
    ]);
  }

  Widget _quick(IconData i, String label, VoidCallback onTap) => Column(children: [
        Material(
          color: Colors.white.withValues(alpha: 0.2),
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: onTap,
            child: Padding(padding: const EdgeInsets.all(11), child: Icon(i, color: Colors.white, size: 20)),
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
      ]);

  Widget _detail(IconData i, String label, String? value) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(i, size: 17, color: _brand),
        const SizedBox(width: 10),
        SizedBox(width: 108, child: Text(label, style: const TextStyle(color: Color(0xFF64748B), fontSize: 12))),
        Expanded(child: Text(value,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Color(0xFF14202B)))),
      ]),
    );
  }

  Widget _kpiGrid(Map k) {
    final items = [
      (tr('إجمالي', 'Total'), k['total'], const Color(0xFF334155), Icons.assignment),
      (tr('مفتوحة', 'Open'), k['open'], const Color(0xFF2F6DF6), Icons.inbox),
      (tr('جارية', 'Active'), k['in_progress'], const Color(0xFFF7A23B), Icons.timelapse),
      (tr('منجزة', 'Done'), k['done'], const Color(0xFF16A34A), Icons.check_circle),
      (tr('متأخرة', 'Overdue'), k['overdue'], const Color(0xFFE5484D), Icons.warning_amber),
      (tr('نسبة الإنجاز', 'Completion'), '${k['completion_pct'] ?? 0}%', const Color(0xFF16794A), Icons.percent),
      (tr('التزام SLA', 'SLA'), '${k['sla'] ?? 0}%', const Color(0xFF0EA5E9), Icons.verified),
      (tr('متوسط الإنجاز', 'Avg mins'), '${k['avg_duration_min'] ?? 0}د', const Color(0xFF7C3AED), Icons.timer),
      (tr('ساعات العمل', 'Work hours'), '${k['work_hours'] ?? 0}س', const Color(0xFF0891B2), Icons.schedule),
    ];
    return GridView.count(
      crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 2.3,
      children: [for (final it in items) _stat(it.$1, '${it.$2}', it.$3, it.$4)],
    );
  }

  Widget _stat(String label, String value, Color color, IconData icon) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(value, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.w900)),
            Text(label, style: const TextStyle(fontSize: 11), overflow: TextOverflow.ellipsis),
          ])),
        ]),
      );
}

class _MiniBars extends StatelessWidget {
  const _MiniBars({required this.daily});
  final List<Map> daily;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final maxV = daily.fold<int>(1, (m, d) => [m, (d['created'] ?? 0) as int, (d['done'] ?? 0) as int].reduce((a, b) => a > b ? a : b));
    return Card(child: Padding(padding: const EdgeInsets.fromLTRB(12, 14, 12, 8), child: Column(children: [
      SizedBox(height: 90, child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        for (final d in daily) Expanded(child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 1),
          child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
            Container(height: 84 * ((d['created'] ?? 0) as int) / maxV, decoration: BoxDecoration(
                color: const Color(0xFF2F6DF6), borderRadius: BorderRadius.circular(2))),
            Container(height: 84 * ((d['done'] ?? 0) as int) / maxV, decoration: BoxDecoration(
                color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(2))),
          ]),
        )),
      ])),
      const SizedBox(height: 6),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        _legend(const Color(0xFF2F6DF6), tr('واردة', 'Created'), cs),
        const SizedBox(width: 16),
        _legend(const Color(0xFF16A34A), tr('منجزة', 'Done'), cs),
      ]),
    ])));
  }

  Widget _legend(Color c, String t, ColorScheme cs) => Row(children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 4),
        Text(t, style: TextStyle(color: cs.outline, fontSize: 11)),
      ]);
}
