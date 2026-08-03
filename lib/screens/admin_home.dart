import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'notifications_screen.dart';
import 'workorders_screen.dart';
import 'supervisor_screen.dart';
import 'client_team_screen.dart';
import 'client_structure_screen.dart';

/// Company-wide admin dashboard for CARE — the whole operation at a glance.
class AdminHome extends StatefulWidget {
  const AdminHome({super.key});
  @override
  State<AdminHome> createState() => _AdminHomeState();
}

class _AdminHomeState extends State<AdminHome> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.adminDashboard();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('🏢 لوحة الشركة', '🏢 Company board')),
        actions: [
          IconButton(icon: const Icon(Icons.notifications_outlined),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()))),
          IconButton(icon: const Icon(Icons.logout), onPressed: () => context.read<AuthProvider>().logout()),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [const SizedBox(height: 120), Center(child: Text(tr('خطأ: ${snap.error}', 'Error: ${snap.error}')))]);
            }
            final d = snap.data!;
            final k = d['kpis'] as Map;
            final byState = (d['by_state'] as Map).cast<String, dynamic>();
            final byService = (d['by_service'] as Map).cast<String, dynamic>();
            final maxState = byState.values.fold<int>(1, (m, v) => (v as int) > m ? v : m);
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(d['company']?.toString() ?? '', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                const SizedBox(height: 12),
                GridView.count(
                  crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.92,
                  children: [
                    StatCard(label: tr('العملاء', 'Clients'), value: k['clients'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.business_center, onTap: () => _go(context, const ClientStructureScreen())),
                    StatCard(label: tr('المرافق', 'Facilities'), value: k['facilities'] ?? 0, color: const Color(0xFF6366F1), icon: Icons.location_city, onTap: () => _go(context, const ClientStructureScreen())),
                    StatCard(label: tr('المباني', 'Buildings'), value: k['buildings'] ?? 0, color: const Color(0xFF0891B2), icon: Icons.apartment, onTap: () => _go(context, const ClientStructureScreen())),
                    StatCard(label: tr('الفِرَق', 'Teams'), value: k['teams'] ?? 0, color: const Color(0xFF14B8A6), icon: Icons.groups, onTap: () => _go(context, const ClientTeamScreen())),
                    StatCard(label: tr('الموظفون', 'Employees'), value: k['employees'] ?? 0, color: const Color(0xFF7C3AED), icon: Icons.engineering, onTap: () => _go(context, const ClientTeamScreen())),
                    StatCard(label: tr('مفتوحة', 'Open'), value: k['open'] ?? 0, color: const Color(0xFFF7A23B), icon: Icons.build, onTap: () => _go(context, const WorkOrdersScreen())),
                    StatCard(label: tr('متأخرة', 'Overdue'), value: k['overdue'] ?? 0, color: const Color(0xFFE5484D), icon: Icons.timer_off, onTap: () => _go(context, const WorkOrdersScreen())),
                    StatCard(label: tr('غير مُسندة', 'Unassigned'), value: k['unassigned'] ?? 0, color: const Color(0xFFB45309), icon: Icons.inbox, onTap: () => _go(context, const SupervisorScreen())),
                    StatCard(label: tr('منجزة', 'Done'), value: k['done'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.check_circle, onTap: () => _go(context, const WorkOrdersScreen())),
                  ],
                ),
                const SizedBox(height: 20),
                _panel(tr('الأعمال حسب الحالة', 'Work by status'), [
                  for (final e in byState.entries) _bar(e.key, e.value as int, maxState, const Color(0xFF0B6EA8)),
                ]),
                _panel(tr('الأعمال حسب الخدمة', 'Work by service'), [
                  for (final e in byService.entries)
                    _bar(tr('${e.key} (مفتوحة ${(e.value as Map)['open']})', '${e.key} (Open ${(e.value as Map)['open']})'), (e.value as Map)['total'] as int,
                        byService.values.fold<int>(1, (m, v) => (v as Map)['total'] > m ? (v)['total'] as int : m),
                        const Color(0xFF14B8A6)),
                ]),
                _panel(tr('أكثر المرافق ضغطاً', 'Busiest facilities'), [
                  for (final f in (d['top_facilities'] as List))
                    ListTile(
                      dense: true,
                      leading: const Icon(Icons.apartment),
                      title: Text('${(f as Map)['name']}'),
                      trailing: Text(tr('مفتوحة ${f['open']}${(f['overdue'] ?? 0) > 0 ? ' · متأخرة ${f['overdue']}' : ''}', 'Open ${f['open']}${(f['overdue'] ?? 0) > 0 ? ' · Overdue ${f['overdue']}' : ''}'),
                          style: const TextStyle(color: Color(0xFFE5484D), fontWeight: FontWeight.w700)),
                    ),
                ]),
              ],
            );
          },
        ),
      ),
    );
  }

  void _go(BuildContext context, Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

  Widget _panel(String title, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 8),
            ...children,
          ]),
        ),
      );

  Widget _bar(String label, int val, int max, Color color) {
    final pct = max > 0 ? val / max : 0.0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
          Text('$val', style: const TextStyle(fontWeight: FontWeight.w800)),
        ]),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(value: pct, minHeight: 8, backgroundColor: const Color(0xFFEEF2F7), color: color),
        ),
      ]),
    );
  }
}
