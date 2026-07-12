import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// A big analytics tab for the client — KPIs, service/priority breakdowns, and
/// per-employee performance on their sites.
class ClientAnalyticsScreen extends StatefulWidget {
  const ClientAnalyticsScreen({super.key});
  @override
  State<ClientAnalyticsScreen> createState() => _ClientAnalyticsScreenState();
}

class _ClientAnalyticsScreenState extends State<ClientAnalyticsScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientAnalytics();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الإحصائيات', 'Analytics'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [const SizedBox(height: 120), Center(child: Text('خطأ: ${snap.error}', style: TextStyle(color: cs.outline)))]);
            }
            final d = snap.data!;
            final k = d['kpis'] as Map;
            final byService = (d['by_service'] as Map).cast<String, dynamic>();
            final byPriority = (d['by_priority'] as Map).cast<String, dynamic>();
            final employees = (d['employees'] as List);
            final maxSvc = byService.values.fold<int>(1, (m, v) => (v as Map)['total'] > m ? (v)['total'] as int : m);
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _big('نسبة الإنجاز', '${k['completion_pct']}%', const Color(0xFF16A34A), 'التزام SLA ${k['sla']}%'),
                const SizedBox(height: 14),
                GridView.count(
                  crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.92,
                  children: [
                    StatCard(label: tr('إجمالي', 'Total'), value: k['total'] ?? 0, color: const Color(0xFF475569), icon: Icons.workspaces),
                    StatCard(label: tr('مفتوحة', 'Open'), value: k['open'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.inbox),
                    StatCard(label: tr('قيد التنفيذ', 'In progress'), value: k['in_progress'] ?? 0, color: const Color(0xFFF59E0B), icon: Icons.timelapse),
                    StatCard(label: tr('منجزة', 'Done'), value: k['done'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.check_circle),
                    StatCard(label: tr('متأخرة', 'Overdue'), value: k['overdue'] ?? 0, color: const Color(0xFFE5484D), icon: Icons.timer_off),
                    StatCard(label: tr('غير مُسندة', 'Unassigned'), value: k['unassigned'] ?? 0, color: const Color(0xFFB45309), icon: Icons.person_off),
                    StatCard(label: tr('المرافق', 'Facilities'), value: k['facilities'] ?? 0, color: const Color(0xFF6366F1), icon: Icons.location_city),
                    StatCard(label: tr('المواقع', 'Locations'), value: k['locations'] ?? 0, color: const Color(0xFF0EA5E9), icon: Icons.qr_code),
                    StatCard(label: tr('الفِرَق', 'Teams'), value: k['teams'] ?? 0, color: const Color(0xFF14B8A6), icon: Icons.groups),
                  ],
                ),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: _mini('متوسط زمن الإنجاز', '${k['avg_duration_min']} د')),
                  const SizedBox(width: 10),
                  Expanded(child: _mini('متوسط زمن الاستجابة', '${k['avg_response_min']} د')),
                ]),
                const SizedBox(height: 18),
                _panel(tr('الأعمال حسب الخدمة', 'Work by service'), [
                  for (final e in byService.entries)
                    _bar('${e.key}  (منجز ${(e.value as Map)['done']} · متأخر ${(e.value)['overdue']})',
                        (e.value as Map)['total'] as int, maxSvc, const Color(0xFF0B6EA8)),
                ]),
                _panel(tr('حسب الأولوية', 'By priority'), [
                  for (final e in byPriority.entries)
                    _bar(e.key, e.value as int, byPriority.values.fold<int>(1, (m, v) => (v as int) > m ? v : m), const Color(0xFF6366F1)),
                ]),
                _panel(tr('أداء الموظفين على مواقعي', 'Staff performance'), [
                  for (final emp in employees) _empRow(emp as Map, cs),
                ]),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _big(String label, String value, Color c, String sub) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [c, c.withValues(alpha: 0.7)]),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label, style: const TextStyle(color: Colors.white70, fontSize: 14)),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.w900)),
            Text(sub, style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ])),
          const Icon(Icons.insights, color: Colors.white54, size: 56),
        ]),
      );

  Widget _mini(String l, String v) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Theme.of(context).cardColor, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0x22000000))),
        child: Column(children: [
          Text(v, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          Text(l, style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12), textAlign: TextAlign.center),
        ]),
      );

  Widget _panel(String title, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            const SizedBox(height: 8), ...children,
          ]),
        ),
      );

  Widget _bar(String label, int val, int max, Color color) {
    final pct = max > 0 ? val / max : 0.0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12.5))),
          Text('$val', style: const TextStyle(fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 4),
        ClipRRect(borderRadius: BorderRadius.circular(6), child: LinearProgressIndicator(value: pct, minHeight: 8, backgroundColor: const Color(0xFFEEF2F7), color: color)),
      ]),
    );
  }

  Widget _empRow(Map e, ColorScheme cs) {
    final pct = (e['completion_pct'] as num?)?.toDouble() ?? 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(children: [
        CircleAvatar(radius: 18, backgroundColor: cs.primaryContainer, child: Text('${e['name']}'.characters.first)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${e['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          Text('${e['job_title'] ?? ''} · منجز ${e['done']}/${e['total']} · متأخر ${e['overdue']}', style: TextStyle(color: cs.outline, fontSize: 12)),
        ])),
        Text('${pct.round()}%', style: TextStyle(fontWeight: FontWeight.w900, color: pct >= 70 ? const Color(0xFF16A34A) : (pct >= 40 ? const Color(0xFFF59E0B) : const Color(0xFFE5484D)))),
      ]),
    );
  }
}
