import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'client_workorders_screen.dart';

/// The services this client is provided, each with its live work-order data and
/// status — not the analytics dashboard. Tapping a service drills into its work
/// orders.
class ClientServicesScreen extends StatefulWidget {
  const ClientServicesScreen({super.key});
  @override
  State<ClientServicesScreen> createState() => _ClientServicesScreenState();
}

class _ClientServicesScreenState extends State<ClientServicesScreen> {
  Future<Map<String, dynamic>>? _f;

  static const _c = Color(0xFFC0392B);
  static const _svcStyle = {
    'security': (Color(0xFFE5484D), Icons.shield_rounded, 'الأمن'),
    'cleaning': (Color(0xFF0EA5E9), Icons.cleaning_services_rounded, 'النظافة'),
    'agriculture': (Color(0xFF16A34A), Icons.park_rounded, 'الزراعة'),
    'facade': (Color(0xFF7C3AED), Icons.location_city_rounded, 'الواجهات'),
    'maintenance': (Color(0xFFF7A23B), Icons.build_rounded, 'الصيانة'),
  };

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.clientAnalytics(period: 'all');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('الخدمات المقدَّمة', 'Services provided'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(() => _f = context.read<AuthProvider>().api.clientAnalytics(period: 'all')),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey)));
            }
            final d = snap.data ?? const {};
            final types = (d['service_types'] as List?) ?? const [];
            final byService = (d['by_service'] as Map?) ?? const {};
            // map label → its type so we can style + drill in
            final labelToType = {for (final t in types) '${t['l']}': '${t['v']}'};
            final rows = byService.entries.toList()
              ..sort((a, b) => ((b.value as Map)['total'] ?? 0).compareTo((a.value as Map)['total'] ?? 0));
            if (rows.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 120),
                Center(child: Text(tr('لا خدمات مسجّلة.', 'No services yet.'),
                    style: const TextStyle(color: Colors.grey))),
              ]);
            }
            return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
              for (final e in rows) _serviceCard('${e.key}', e.value as Map, labelToType['${e.key}']),
            ]);
          },
        ),
      ),
    );
  }

  Widget _serviceCard(String label, Map st, String? type) {
    final style = _svcStyle[type] ?? (const Color(0xFF64748B), Icons.design_services_rounded, label);
    final c = style.$1;
    final total = (st['total'] ?? 0) as int;
    final open = (st['open'] ?? 0) as int;
    final done = (st['done'] ?? 0) as int;
    final overdue = (st['overdue'] ?? 0) as int;
    final completion = total > 0 ? done * 100.0 / total : 0.0;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: c.withValues(alpha: 0.2)),
        boxShadow: [BoxShadow(color: c.withValues(alpha: 0.1), blurRadius: 10, offset: const Offset(0, 5))],
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: type == null ? null : () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => ClientWorkOrdersScreen(initialFilter: 'all', serviceType: type))),
        child: Column(children: [
          // header band
          Container(
            padding: const EdgeInsets.fromLTRB(13, 11, 13, 11),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.28)!],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
            ),
            child: Row(children: [
              Container(
                width: 40, height: 40, alignment: Alignment.center,
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                child: Icon(style.$2, color: Colors.white, size: 21),
              ),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
                Text(tr('$total أمر عمل', '$total work orders'),
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11)),
              ])),
              // status pill: healthy / attention
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                    color: (overdue > 0 ? const Color(0xFFDC2626) : const Color(0xFF16A34A)),
                    borderRadius: BorderRadius.circular(20)),
                child: Text(overdue > 0 ? tr('$overdue متأخر', '$overdue late') : tr('منتظم', 'On track'),
                    style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900)),
              ),
            ]),
          ),
          // body: stats + completion bar
          Padding(
            padding: const EdgeInsets.all(13),
            child: Column(children: [
              Row(children: [
                _stat(tr('مفتوحة', 'Open'), '$open', const Color(0xFFF7A23B)),
                _stat(tr('منجزة', 'Done'), '$done', const Color(0xFF16A34A)),
                _stat(tr('متأخرة', 'Overdue'), '$overdue', const Color(0xFFE5484D)),
                _stat(tr('الإجمالي', 'Total'), '$total', const Color(0xFF64748B)),
              ]),
              const SizedBox(height: 11),
              Row(children: [
                Expanded(child: ClipRRect(
                  borderRadius: BorderRadius.circular(5),
                  child: LinearProgressIndicator(
                    value: (completion / 100).clamp(0.0, 1.0), minHeight: 7,
                    backgroundColor: c.withValues(alpha: 0.1),
                    valueColor: AlwaysStoppedAnimation(c),
                  ),
                )),
                const SizedBox(width: 9),
                Text(tr('${completion.round()}% إنجاز', '${completion.round()}% done'),
                    style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: c)),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _stat(String label, String v, Color c) => Expanded(
        child: Column(children: [
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 9, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
        ]),
      );
}
