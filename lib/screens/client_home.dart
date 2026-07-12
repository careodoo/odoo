import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'facility_detail_screen.dart';
import 'work_order_detail_screen.dart';
import 'client_team_screen.dart';
import 'client_activity_screen.dart';
import 'client_structure_screen.dart';
import 'client_analytics_screen.dart';

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
        title: Text(tr('بوابة العميل', 'Client portal')),
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
                const SizedBox(height: 14),
                _quickAccess(cs),
                const SizedBox(height: 16),
                _kpiGrid(k),
                const SizedBox(height: 20),
                _section(tr('مبانيي ومرافقي', 'My buildings & facilities')),
                for (final f in (d['facilities'] as List)) _facilityCard(f as Map, cs),
                const SizedBox(height: 16),
                _section(tr('الخدمات المقدَّمة', 'Services provided')),
                _servicesWrap(d['services'] as List),
                const SizedBox(height: 16),
                _section(tr('فِرَق العمل', 'Teams')),
                for (final t in (d['teams'] as List)) _teamCard(t as Map, cs),
                const SizedBox(height: 16),
                _section(tr('آخر الأعمال', 'Recent work')),
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
              Text(tr('مرحباً بك', 'Welcome'), style: TextStyle(color: Colors.white70, fontSize: 13)),
              Text(client, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
            ]),
          ),
        ]),
      );

  void _go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

  Widget _quickAccess(ColorScheme cs) {
    Widget btn(String emoji, String label, Color c, VoidCallback onTap) => Expanded(
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(16)),
              child: Column(children: [
                Text(emoji, style: const TextStyle(fontSize: 24)),
                const SizedBox(height: 6),
                Text(label, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12), textAlign: TextAlign.center),
              ]),
            ),
          ),
        );
    return Row(children: [
      btn('👷', tr('الفريق', 'Team'), const Color(0xFF2F6DF6), () => _go(const ClientTeamScreen())),
      const SizedBox(width: 10),
      btn('📡', tr('النشاط', 'Live'), const Color(0xFF16A34A), () => _go(const ClientActivityScreen())),
      const SizedBox(width: 10),
      btn('🏢', tr('المباني', 'Buildings'), const Color(0xFF6366F1), () => _go(const ClientStructureScreen())),
      const SizedBox(width: 10),
      btn('📊', tr('التحليلات', 'Analytics'), const Color(0xFFF59E0B), () => _go(const ClientAnalyticsScreen())),
    ]);
  }

  Widget _kpiGrid(Map k) {
    final items = [
      (tr('المرافق', 'Facilities'), k['facilities'] ?? 0, const Color(0xFF2F6DF6), Icons.location_city, () => _go(const ClientStructureScreen())),
      (tr('المباني', 'Buildings'), k['buildings'] ?? 0, const Color(0xFF6366F1), Icons.apartment, () => _go(const ClientStructureScreen())),
      (tr('المواقع', 'Locations'), k['locations'] ?? 0, const Color(0xFF0EA5E9), Icons.qr_code, () => _go(const ClientStructureScreen())),
      (tr('أعمال مفتوحة', 'Open work'), k['open_workorders'] ?? 0, const Color(0xFFF7A23B), Icons.build, () => _go(const ClientAnalyticsScreen())),
      (tr('الخدمات', 'Services'), k['services'] ?? 0, const Color(0xFF37C98A), Icons.design_services, () => _go(const ClientAnalyticsScreen())),
      (tr('الفِرَق', 'Teams'), k['teams'] ?? 0, const Color(0xFF14B8A6), Icons.groups, () => _go(const ClientTeamScreen())),
    ];
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 0.95,
      children: [for (final it in items) StatCard(label: it.$1, value: it.$2 as int, color: it.$3, icon: it.$4, onTap: it.$5)],
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

  static const _svcStyle = {
    'security': (Color(0xFFE5484D), '🛡️'),
    'cleaning': (Color(0xFF0EA5E9), '🧹'),
    'agriculture': (Color(0xFF16A34A), '🌿'),
    'facade': (Color(0xFF7C3AED), '🏙️'),
    'maintenance': (Color(0xFFF59E0B), '🔧'),
  };

  Widget _servicesWrap(List services) {
    if (services.isEmpty) return const SizedBox.shrink();
    return GridView.count(
      crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 2.6,
      children: [
        for (final s in services)
          Builder(builder: (_) {
            final m = s as Map;
            final style = _svcStyle[m['type']] ?? (const Color(0xFF334155), '•');
            final c = style.$1;
            return InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => _go(const ClientAnalyticsScreen()),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [c.withValues(alpha: 0.16), c.withValues(alpha: 0.04)],
                      begin: Alignment.topLeft, end: Alignment.bottomRight),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: c.withValues(alpha: 0.3)),
                ),
                child: Row(children: [
                  Container(
                    width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(12)),
                    child: Text('${m['icon'] ?? style.$2}', style: const TextStyle(fontSize: 22)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${m['name']}',
                      style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 13.5), maxLines: 2, overflow: TextOverflow.ellipsis)),
                ]),
              ),
            );
          }),
      ],
    );
  }

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
          subtitle: Text('${w['service_type']} · ${w['facility']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: WoStateBadge('${w['state']}'),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => WorkOrderDetailScreen(id: w['id'] as int, title: '${w['title']}'))),
        ),
      );
}
