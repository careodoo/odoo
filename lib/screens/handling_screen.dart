import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Material-handling board — moves, their cargo, weight and state. Shows the
/// real care.handling.job records (not generic work orders).
class HandlingScreen extends StatefulWidget {
  const HandlingScreen({super.key});
  @override
  State<HandlingScreen> createState() => _HandlingScreenState();
}

class _HandlingScreenState extends State<HandlingScreen> {
  static const _accent = Color(0xFF0D9488);
  Future<Map<String, dynamic>>? _f;
  String _filter = 'all';

  static const _stateColor = {
    'draft': Color(0xFF94A3B8), 'scheduled': Color(0xFF0D9488),
    'in_progress': Color(0xFF2563EB), 'delivered': Color(0xFF16A34A),
    'verified': Color(0xFF16A34A), 'cancelled': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.handlingJobs();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('المناولة', 'Material handling'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.black54)));
          }
          final d = snap.data ?? const {};
          final stats = (d['stats'] as Map?) ?? const {};
          var jobs = ((d['jobs'] as List?) ?? const []).cast<Map>();
          if (_filter == 'open') {
            jobs = jobs.where((j) => ['draft', 'scheduled', 'in_progress'].contains(j['state'])).toList();
          } else if (_filter == 'done') {
            jobs = jobs.where((j) => ['delivered', 'verified'].contains(j['state'])).toList();
          }
          return RefreshIndicator(
            color: _accent,
            onRefresh: () async => setState(_load),
            child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              _statsHeader(stats),
              const SizedBox(height: 12),
              Row(children: [
                _chip('all', tr('الكل', 'All')),
                _chip('open', tr('جارية', 'Open')),
                _chip('done', tr('منجزة', 'Delivered')),
              ]),
              const SizedBox(height: 10),
              if (jobs.isEmpty)
                Padding(padding: const EdgeInsets.all(30),
                    child: Center(child: Text(tr('لا مهام مناولة', 'No handling jobs'),
                        style: const TextStyle(color: Colors.black45)))),
              for (final j in jobs) _jobCard(j),
            ]),
          );
        },
      ),
    );
  }

  Widget _statsHeader(Map s) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [_accent, Color(0xFF0B6E63)],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          _stat('${s['total'] ?? 0}', tr('إجمالي', 'Total')),
          _stat('${s['open'] ?? 0}', tr('جارية', 'Open')),
          _stat('${s['delivered'] ?? 0}', tr('منجزة', 'Done')),
          _stat('${s['weight'] ?? 0}', tr('كجم', 'kg')),
          _stat('${s['pieces'] ?? 0}', tr('قطعة', 'pcs')),
        ]),
      );

  Widget _stat(String v, String l) => Expanded(
        child: Column(children: [
          Text(v, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
          Text(l, style: const TextStyle(color: Colors.white70, fontSize: 10.5)),
        ]),
      );

  Widget _chip(String v, String label) {
    final on = _filter == v;
    return Padding(padding: const EdgeInsets.only(left: 6),
        child: ChoiceChip(label: Text(label), selected: on,
            selectedColor: _accent.withOpacity(0.18),
            onSelected: (_) => setState(() => _filter = v)));
  }

  Widget _jobCard(Map j) {
    final sc = _stateColor[j['state']] ?? const Color(0xFF94A3B8);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE3E7EE))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${j['cargo'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14))),
          if (j['fragile'] == true)
            Padding(padding: const EdgeInsets.only(left: 6),
                child: Text(tr('⚠ قابل للكسر', '⚠ Fragile'), style: const TextStyle(fontSize: 10, color: Color(0xFFE11D48)))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: sc.withOpacity(0.14), borderRadius: BorderRadius.circular(20)),
              child: Text('${j['state_label'] ?? ''}',
                  style: TextStyle(color: sc, fontWeight: FontWeight.w900, fontSize: 11))),
        ]),
        const SizedBox(height: 6),
        Text('${j['name'] ?? ''} · ${j['facility'] ?? ''}',
            style: const TextStyle(fontSize: 11.5, color: Colors.black45)),
        const SizedBox(height: 6),
        Row(children: [
          if (j['from'] != null || j['to'] != null)
            Expanded(child: Text('${j['from'] ?? '—'}  ←  ${j['to'] ?? '—'}',
                style: const TextStyle(fontSize: 12, color: Colors.black87, fontWeight: FontWeight.w600))),
        ]),
        const SizedBox(height: 4),
        Text([
          if (j['move_type'] != null) '🚚 ${j['move_type']}',
          tr('⚖ ${j['weight'] ?? 0} كجم', '⚖ ${j['weight'] ?? 0} kg'),
          '📦 ${j['quantity'] ?? 0}',
          if (j['crew'] != null) '👷 ${j['crew']}',
          if (j['scheduled_at'] != null) '🕒 ${j['scheduled_at']}',
        ].join(' · '), style: const TextStyle(fontSize: 11, color: Colors.black54)),
      ]),
    );
  }
}
