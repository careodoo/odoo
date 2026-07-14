import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client-facing security suite: overview + incidents / patrols / gate passes /
/// visitors / inspections / guards / keys (scoped to the client's premises).
class ClientSecurityScreen extends StatefulWidget {
  const ClientSecurityScreen({super.key});
  @override
  State<ClientSecurityScreen> createState() => _ClientSecurityScreenState();
}

class _ClientSecurityScreenState extends State<ClientSecurityScreen> {
  Map<String, dynamic>? _summary;
  String _kind = 'incidents';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ['incidents', '🚨 البلاغات', 'Incidents'],
    ['patrols', '🥾 الجولات', 'Patrols'],
    ['gatepasses', '🎫 تصاريح الدخول', 'Gate passes'],
    ['visitors', '🚶 الزوّار', 'Visitors'],
    ['inspections', '🔍 التفتيش', 'Inspections'],
    ['guards', '👮 الحرّاس', 'Guards'],
    ['keys', '🔑 المفاتيح', 'Keys'],
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _loadKind('incidents');
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientSecuritySummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _loadKind(String k) => setState(() {
        _kind = k;
        _list = context.read<AuthProvider>().api.clientSecurity(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الأمن', 'Security'))),
      body: Column(children: [
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('🚨', '${s['incidents_open'] ?? 0}', tr('بلاغات مفتوحة', 'Open incidents'), const Color(0xFFE11D48)),
              _stat('🔍', '${s['inspections_open'] ?? 0}', tr('تفتيش قائم', 'Inspections'), const Color(0xFFF59E0B)),
              _stat('🎫', '${s['gatepasses_active'] ?? 0}', tr('تصاريح فعّالة', 'Active passes'), const Color(0xFF3B82F6)),
              _stat('🥾', '${s['patrols_ongoing'] ?? 0}', tr('جولات جارية', 'Patrols'), const Color(0xFF16A34A)),
              _stat('👮', '${s['guards_present'] ?? 0}', tr('حرّاس', 'Guards'), const Color(0xFF0891B2)),
              _stat('🔑', '${s['keys_out'] ?? 0}', tr('مفاتيح مُصرَفة', 'Keys out'), const Color(0xFF6366F1)),
            ]),
          ),
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
            for (final k in _kinds)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: ChoiceChip(
                  label: Text(gLang == 'en' ? k[2] : k[1]),
                  selected: _kind == k[0],
                  onSelected: (_) => _loadKind(k[0]),
                ),
              ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records')));
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 130,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );

  Widget _row(Map r) {
    // generic renderer across the different security kinds
    final title = r['name'] ?? r['visitor'] ?? r['guard'] ?? '—';
    final sub = [
      r['type'], r['premise'], r['route'], r['guard'], r['company'],
      r['inspector'], r['holder'], r['date'], r['state_label'],
    ].where((x) => x != null && '$x'.isNotEmpty).map((x) => '$x').take(3).join(' · ');
    final st = r['severity'] ?? r['state_label'];
    return ListTile(
      title: Text('$title', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: st != null
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: Colors.blueGrey.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
              child: Text('$st', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            )
          : null,
    );
  }
}
