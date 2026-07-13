import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

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

  void _load() => _future = context.read<AuthProvider>().api.clientEmployee(widget.employeeId, period: _period);

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

  Widget _profileCard(Map p, ColorScheme cs) {
    Widget avatar;
    final photo = p['photo'] as String?;
    if (photo != null && photo.startsWith('data:image')) {
      try {
        avatar = CircleAvatar(radius: 34, backgroundImage: MemoryImage(base64Decode(photo.split(',').last)));
      } catch (_) {
        avatar = CircleAvatar(radius: 34, child: Text('${p['name'] ?? '?'}'.characters.first));
      }
    } else {
      avatar = CircleAvatar(radius: 34, child: Text('${p['name'] ?? '?'}'.characters.first));
    }
    Widget row(IconData i, String? v) => v == null || v.isEmpty ? const SizedBox.shrink() : Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(children: [Icon(i, size: 16, color: cs.outline), const SizedBox(width: 8), Expanded(child: Text(v))]),
        );
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        avatar,
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${p['name'] ?? ''}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          if (p['job'] != null) Text('${p['job']}', style: TextStyle(color: cs.outline)),
        ])),
      ]),
      const Divider(height: 20),
      row(Icons.apartment, p['department'] as String?),
      row(Icons.badge, p['work_location'] as String?),
      row(Icons.person, p['manager'] != null ? '${tr('المدير', 'Manager')}: ${p['manager']}' : null),
      row(Icons.phone, p['work_phone'] as String? ?? p['mobile'] as String?),
      row(Icons.email, p['work_email'] as String?),
      row(Icons.event, p['joining'] != null ? '${tr('التحاق', 'Joined')}: ${p['joining']}' : null),
    ])));
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
