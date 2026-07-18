import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'observation_create.dart';
import 'observation_detail.dart';

/// Quality rounds / observations (الجولات والجودة): log an observation, track
/// its severity/state, and convert it into a corrective work order.
class QualityScreen extends StatefulWidget {
  const QualityScreen({super.key});
  @override
  State<QualityScreen> createState() => _QualityScreenState();
}

class _QualityScreenState extends State<QualityScreen> {
  late Future<List<dynamic>> _future;

  static const _sev = {
    'low': Color(0xFF94A3B8), 'medium': Color(0xFF3B82F6), 'high': Color(0xFFF59E0B), 'critical': Color(0xFFE11D48),
  };
  static const _stC = {
    'open': Color(0xFF3B82F6), 'assigned': Color(0xFF6366F1), 'fixing': Color(0xFFF59E0B),
    'reinspect': Color(0xFF7C3AED), 'closed': Color(0xFF16A34A), 'cancelled': Color(0xFF94A3B8),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientObservations();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الجودة والجولات', 'Quality & rounds'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _newObs, icon: const Icon(Icons.add), label: Text(tr('ملاحظة', 'Observation'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snap.hasError) return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)))]);
            final list = snap.data ?? const [];
            if (list.isEmpty) return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا ملاحظات', 'No observations'), style: TextStyle(color: cs.outline)))]);
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final o = list[i] as Map;
                final sv = _sev[o['severity']] ?? const Color(0xFF3B82F6);
                final oc = _stC[o['state']] ?? const Color(0xFF64748B);
                return Card(child: ListTile(
                  onTap: () => _openDetail(o['id'] as int),
                  title: Text('${o['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${o['name']} · ${o['facility'] ?? ''}${o['workorder'] != null ? ' · 🛠️ ${o['workorder']}' : ''}',
                      style: TextStyle(color: cs.outline, fontSize: 12)),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    _pill(o['severity_label'], sv),
                    const SizedBox(height: 4),
                    _pill(o['state_label'], oc),
                  ]),
                ));
              },
            );
          },
        ),
      ),
    );
  }

  Widget _pill(dynamic t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
        child: Text('${t ?? ''}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800)),
      );

  Future<void> _openDetail(int id) async {
    final changed = await ObservationDetailSheet.open(context, id);
    if (changed == true && mounted) setState(_load);
  }

  Future<void> _newObs() async {
    final created = await ObservationCreateSheet.open(context);
    if (created == true && mounted) setState(_load);
  }
}
