import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Buildings / floors / facilities statistics for the client, period-aware —
/// expandable tree: facility → building → floor, each with its work-order KPIs.
class ClientStructureScreen extends StatefulWidget {
  const ClientStructureScreen({super.key});
  @override
  State<ClientStructureScreen> createState() => _ClientStructureScreenState();
}

class _ClientStructureScreenState extends State<ClientStructureScreen> {
  String _period = 'month';
  Future<Map<String, dynamic>>? _future;

  static const _periods = [
    ('day', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'), ('year', 'السنة', 'Year'), ('all', 'الكل', 'All'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientStructure(period: _period);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('المباني والمرافق', 'Buildings & facilities'))),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final p in _periods)
              Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
                label: Text(tr(p.$2, p.$3)), selected: _period == p.$1,
                onSelected: (_) => setState(() { _period = p.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return Center(child: Text('${snap.error}'));
            final facs = ((snap.data ?? const {})['facilities'] as List?) ?? const [];
            return ListView(padding: const EdgeInsets.all(12), children: [
              for (final f in facs) _facilityCard(f as Map),
            ]);
          },
        )),
      ]),
    );
  }

  Widget _facilityCard(Map f) {
    final st = (f['stats'] as Map?) ?? const {};
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ExpansionTile(
        leading: const Icon(Icons.location_city, color: Color(0xFF0B6EA8)),
        title: Text('${f['name']}', style: const TextStyle(fontWeight: FontWeight.w900)),
        subtitle: _statsLine(st),
        childrenPadding: const EdgeInsets.only(bottom: 8),
        children: [
          for (final b in (f['buildings'] as List? ?? const []))
            _buildingTile(b as Map),
        ],
      ),
    );
  }

  Widget _buildingTile(Map b) {
    final st = (b['stats'] as Map?) ?? const {};
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 10),
        leading: const Icon(Icons.apartment, color: Color(0xFF2F6DF6)),
        title: Text('${b['name']} · ${b['floors_count']} ${tr('أدوار', 'floors')}'),
        subtitle: _statsLine(st),
        children: [
          for (final fl in (b['floors'] as List? ?? const []))
            ListTile(
              dense: true,
              leading: const Icon(Icons.layers, size: 18, color: Color(0xFF64748B)),
              title: Text('${(fl as Map)['name']} · ${fl['locations']} ${tr('موقع', 'locations')}'),
              subtitle: _statsLine((fl['stats'] as Map?) ?? const {}),
            ),
        ],
      ),
    );
  }

  Widget _statsLine(Map st) {
    Widget chip(String label, dynamic v, Color c) => Container(
          margin: const EdgeInsets.only(left: 6, top: 4),
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(10)),
          child: Text('$label $v', style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700)),
        );
    return Wrap(children: [
      chip(tr('الكل', 'Total'), st['total'] ?? 0, const Color(0xFF334155)),
      chip(tr('مفتوحة', 'Open'), st['open'] ?? 0, const Color(0xFF2F6DF6)),
      chip(tr('منجزة', 'Done'), st['done'] ?? 0, const Color(0xFF16A34A)),
      chip(tr('متأخرة', 'Overdue'), st['overdue'] ?? 0, const Color(0xFFE5484D)),
      chip('SLA', '${st['sla'] ?? 0}%', const Color(0xFF0EA5E9)),
    ]);
  }
}
