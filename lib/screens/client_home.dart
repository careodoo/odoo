import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/widgets.dart';
import 'facility_detail_screen.dart';

/// The client's cockpit — everything the module holds for this customer:
/// buildings, services, teams, live work-order activity. Fully data-driven, so
/// anything added in the backend appears here automatically.
class ClientHome extends StatefulWidget {
  const ClientHome({super.key});
  @override
  State<ClientHome> createState() => _ClientHomeState();
}

class _ClientHomeState extends State<ClientHome> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientOverview();

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('بوابة العميل'),
        actions: [
          NotifBell(unread: p.unreadNotifications),
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
              return ListView(children: [const SizedBox(height: 120), Center(child: Text('خطأ: ${snap.error}', style: TextStyle(color: cs.outline)))]);
            }
            final d = snap.data!;
            final k = (d['kpis'] as Map);
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _hero(d['client']?.toString() ?? '', cs),
                const SizedBox(height: 16),
                _kpiGrid(k),
                const SizedBox(height: 20),
                _section('مبانيي ومرافقي'),
                for (final f in (d['facilities'] as List)) _facilityCard(f as Map, cs),
                const SizedBox(height: 16),
                _section('الخدمات المقدَّمة'),
                _servicesWrap(d['services'] as List),
                const SizedBox(height: 16),
                _section('فِرَق العمل'),
                for (final t in (d['teams'] as List)) _teamCard(t as Map, cs),
                const SizedBox(height: 16),
                _section('آخر الأعمال'),
                for (final w in (d['recent_workorders'] as List)) _woCard(w as Map, cs),
                const SizedBox(height: 24),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _hero(String client, ColorScheme cs) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [cs.primary, cs.primary.withValues(alpha: 0.6)]),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          const CircleAvatar(radius: 24, backgroundColor: Colors.white24, child: Text('🏢', style: TextStyle(fontSize: 24))),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('مرحباً بك', style: TextStyle(color: Colors.white70, fontSize: 13)),
              Text(client, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
            ]),
          ),
        ]),
      );

  Widget _kpiGrid(Map k) {
    final items = [
      ('المرافق', k['facilities'] ?? 0, const Color(0xFF2F6DF6), Icons.location_city),
      ('المباني', k['buildings'] ?? 0, const Color(0xFF6366F1), Icons.apartment),
      ('المواقع', k['locations'] ?? 0, const Color(0xFF0EA5E9), Icons.qr_code),
      ('أعمال مفتوحة', k['open_workorders'] ?? 0, const Color(0xFFF7A23B), Icons.build),
      ('الخدمات', k['services'] ?? 0, const Color(0xFF37C98A), Icons.design_services),
      ('الفِرَق', k['teams'] ?? 0, const Color(0xFF14B8A6), Icons.groups),
    ];
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 0.95,
      children: [for (final it in items) StatCard(label: it.$1, value: it.$2 as int, color: it.$3, icon: it.$4)],
    );
  }

  Widget _section(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
      );

  Widget _facilityCard(Map f, ColorScheme cs) => Card(
        child: ListTile(
          leading: CircleAvatar(backgroundColor: cs.primaryContainer, child: const Icon(Icons.apartment)),
          title: Text('${f['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text('${f['address'] ?? ''}\nمباني: ${f['buildings']} · مواقع: ${f['locations']} · أعمال مفتوحة: ${f['open_workorders']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          isThreeLine: true,
          trailing: const Icon(Icons.chevron_left),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => FacilityDetailScreen(facilityId: f['id'] as int, name: '${f['name']}'))),
        ),
      );

  Widget _servicesWrap(List services) => Wrap(
        spacing: 8, runSpacing: 8,
        children: [
          for (final s in services)
            Chip(
              avatar: Text('${(s as Map)['icon'] ?? '•'}'),
              label: Text('${s['name']}'),
            ),
        ],
      );

  Widget _teamCard(Map t, ColorScheme cs) => Card(
        child: ListTile(
          dense: true,
          leading: const Icon(Icons.groups, color: Color(0xFF14B8A6)),
          title: Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${t['service'] ?? ''} · مشرف: ${t['supervisor'] ?? '—'} · أعضاء: ${t['members']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
        ),
      );

  Widget _woCard(Map w, ColorScheme cs) => Card(
        child: ListTile(
          dense: true,
          leading: const Icon(Icons.build_circle_outlined),
          title: Text('${w['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${w['service_type']} · ${w['facility']} · ${w['state']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
        ),
      );
}
