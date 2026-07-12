import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/widgets.dart';
import 'notifications_screen.dart';

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
    final p = context.watch<AuthProvider>().profile!;
    return Scaffold(
      appBar: AppBar(
        title: const Text('🏢 لوحة الشركة'),
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
              return ListView(children: [const SizedBox(height: 120), Center(child: Text('خطأ: ${snap.error}'))]);
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
                    StatCard(label: 'العملاء', value: k['clients'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.business_center),
                    StatCard(label: 'المرافق', value: k['facilities'] ?? 0, color: const Color(0xFF6366F1), icon: Icons.location_city),
                    StatCard(label: 'المباني', value: k['buildings'] ?? 0, color: const Color(0xFF0891B2), icon: Icons.apartment),
                    StatCard(label: 'الفِرَق', value: k['teams'] ?? 0, color: const Color(0xFF14B8A6), icon: Icons.groups),
                    StatCard(label: 'الموظفون', value: k['employees'] ?? 0, color: const Color(0xFF7C3AED), icon: Icons.engineering),
                    StatCard(label: 'مفتوحة', value: k['open'] ?? 0, color: const Color(0xFFF7A23B), icon: Icons.build),
                    StatCard(label: 'متأخرة', value: k['overdue'] ?? 0, color: const Color(0xFFE5484D), icon: Icons.timer_off),
                    StatCard(label: 'غير مُسندة', value: k['unassigned'] ?? 0, color: const Color(0xFFB45309), icon: Icons.inbox),
                    StatCard(label: 'منجزة', value: k['done'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.check_circle),
                  ],
                ),
                const SizedBox(height: 20),
                _panel('الأعمال حسب الحالة', [
                  for (final e in byState.entries) _bar(e.key, e.value as int, maxState, const Color(0xFF0B6EA8)),
                ]),
                _panel('الأعمال حسب الخدمة', [
                  for (final e in byService.entries)
                    _bar('${e.key} (مفتوحة ${(e.value as Map)['open']})', (e.value as Map)['total'] as int,
                        byService.values.fold<int>(1, (m, v) => (v as Map)['total'] > m ? (v)['total'] as int : m),
                        const Color(0xFF14B8A6)),
                ]),
                _panel('أكثر المرافق ضغطاً', [
                  for (final f in (d['top_facilities'] as List))
                    ListTile(
                      dense: true,
                      leading: const Icon(Icons.apartment),
                      title: Text('${(f as Map)['name']}'),
                      trailing: Text('مفتوحة ${f['open']}${(f['overdue'] ?? 0) > 0 ? ' · متأخرة ${f['overdue']}' : ''}',
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
