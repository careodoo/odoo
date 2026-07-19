import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Renders a service-specific list (cleaning audits / agri zones / facade
/// permits) with a tailored card per kind.
class ServiceScreen extends StatefulWidget {
  const ServiceScreen({super.key, required this.kind, required this.title});
  final String kind; // cleaning | agri | facade
  final String title;
  @override
  State<ServiceScreen> createState() => _ServiceScreenState();
}

class _ServiceScreenState extends State<ServiceScreen> {
  late Future<List<dynamic>> _future;

  static const _paths = {'cleaning': 'cleaning/audits', 'agri': 'agri/zones', 'facade': 'facade/permits'};

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.serviceList(_paths[widget.kind]!);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return _msg('خطأ: ${snap.error}');
            final items = snap.data ?? const [];
            if (items.isEmpty) return _msg(tr('لا سجلات بعد.', 'No records yet.'));
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              itemBuilder: (_, i) => _card(items[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _msg(String t) => ListView(children: [
        const SizedBox(height: 130),
        Center(child: Text(t, style: TextStyle(color: Theme.of(context).colorScheme.outline))),
      ]);

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
      );

  Widget _card(Map m) {
    final cs = Theme.of(context).colorScheme;
    switch (widget.kind) {
      case 'cleaning':
        final score = (m['score'] as num?)?.toDouble() ?? 0;
        final col = score >= 85 ? const Color(0xFF16A34A) : (score >= 60 ? const Color(0xFFF59E0B) : const Color(0xFFE5484D));
        return Card(child: ListTile(
          leading: CircleAvatar(backgroundColor: col.withValues(alpha: 0.15), child: Text('${score.round()}', style: TextStyle(color: col, fontWeight: FontWeight.w900))),
          title: Text('${m['name']} — ${m['location'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${m['facility'] ?? ''} · إخفاقات: ${m['fail_count']} · ${m['date'] ?? ''}', style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: _pill('${m['rating'] ?? m['state']}', col),
        ));
      case 'agri':
        final due = m['is_due'] == true;
        return Card(child: ListTile(
          leading: Icon(Icons.grass, color: due ? const Color(0xFFF59E0B) : const Color(0xFF37C98A)),
          title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${m['facility'] ?? ''} · ريّ: ${m['method'] ?? ''} · ${m['frequency'] ?? ''}${m['weather_based'] == true ? tr(' · حسب الطقس', '· weather-based') : ''}\nالتالي: ${m['next_run'] ?? '—'}', style: TextStyle(color: cs.outline, fontSize: 12)),
          isThreeLine: true,
          trailing: due ? _pill(tr('مستحق', 'Due'), const Color(0xFFF59E0B)) : _pill(tr('منتظم', 'Regular'), const Color(0xFF37C98A)),
        ));
      case 'facade':
        final safe = m['is_safe'] == true;
        return Card(child: ListTile(
          leading: Icon(safe ? Icons.check_circle : Icons.dangerous, color: safe ? const Color(0xFF16A34A) : const Color(0xFFE5484D)),
          title: Text('${m['name']} — ${m['zone'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${m['facility'] ?? ''} · طريقة: ${m['method'] ?? ''} · رياح ${m['wind_speed']}/${m['wind_limit']} كم/س · ${m['date'] ?? ''}', style: TextStyle(color: cs.outline, fontSize: 12)),
          isThreeLine: true,
          trailing: _pill(safe ? tr('آمن', 'Safe') : '⛔ رياح', safe ? const Color(0xFF16A34A) : const Color(0xFFE5484D)),
        ));
      default:
        return Card(child: ListTile(title: Text('${m['name']}')));
    }
  }
}
