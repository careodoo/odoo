import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

class AppraisalScreen extends StatefulWidget {
  const AppraisalScreen({super.key});
  @override
  State<AppraisalScreen> createState() => _AppraisalScreenState();
}

class _AppraisalScreenState extends State<AppraisalScreen> {
  late Future<Map<String, dynamic>> _me;
  Future<List<dynamic>>? _team;

  @override
  void initState() {
    super.initState();
    final api = context.read<AuthProvider>().api;
    _me = api.appraisalMe();
    final p = context.read<AuthProvider>().profile!;
    if (p.isSupervisor || p.isAdmin) _team = api.appraisalTeam();
  }

  Color _c(num v) => v >= 85 ? const Color(0xFF16A34A) : v >= 70 ? const Color(0xFF0B6EA8)
      : v >= 50 ? const Color(0xFFF59E0B) : const Color(0xFFE5484D);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('تقييم الأداء', 'Performance'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        FutureBuilder<Map<String, dynamic>>(
          future: _me,
          builder: (context, snap) {
            if (!snap.hasData) {
              return snap.hasError
                  ? Text('${snap.error}', textAlign: TextAlign.center)
                  : const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator()));
            }
            return _scoreCard(snap.data!, mine: true);
          },
        ),
        if (_team != null) ...[
          const SizedBox(height: 18),
          Text(tr('ترتيب الفريق', 'Team ranking'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 8),
          FutureBuilder<List<dynamic>>(
            future: _team,
            builder: (context, snap) {
              if (!snap.hasData) return const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator()));
              final list = snap.data!;
              return Column(children: [
                for (var i = 0; i < list.length; i++) _teamRow(i + 1, list[i] as Map),
              ]);
            },
          ),
        ],
      ]),
    );
  }

  Widget _scoreCard(Map d, {bool mine = false}) {
    final overall = (d['overall'] as num?) ?? 0;
    final axes = (d['axes'] as Map);
    final c = _c(overall);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(children: [
          if (mine) Text('${d['employee']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 8),
          Stack(alignment: Alignment.center, children: [
            SizedBox(width: 120, height: 120, child: CircularProgressIndicator(
              value: overall / 100, strokeWidth: 12, backgroundColor: const Color(0xFFEEF2F7), color: c)),
            Column(mainAxisSize: MainAxisSize.min, children: [
              Text('$overall', style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: c)),
              Text('${d['rating']}', style: TextStyle(color: c, fontWeight: FontWeight.w700)),
            ]),
          ]),
          const SizedBox(height: 16),
          _axis(tr('حجم المهام', 'Volume'), axes['volume'] as int),
          _axis(tr('نسبة الإنجاز', 'Completion'), axes['completion'] as int),
          _axis(tr('سرعة الإنجاز', 'Speed'), axes['speed'] as int),
          _axis(tr('جودة الإنجاز', 'Quality'), axes['quality'] as int),
          const SizedBox(height: 6),
          Text('${tr('منجزة', 'Done')}: ${d['done']}/${d['total']} · ${tr('معتمدة', 'Approved')}: ${d['verified']}',
              style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
        ]),
      ),
    );
  }

  Widget _axis(String label, int v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(label, style: const TextStyle(fontSize: 13)),
            Text('$v%', style: TextStyle(fontWeight: FontWeight.w800, color: _c(v))),
          ]),
          const SizedBox(height: 3),
          ClipRRect(borderRadius: BorderRadius.circular(6), child: LinearProgressIndicator(
              value: v / 100, minHeight: 7, backgroundColor: const Color(0xFFEEF2F7), color: _c(v))),
        ]),
      );

  Widget _teamRow(int rank, Map d) {
    final overall = (d['overall'] as num?) ?? 0;
    return Card(child: ListTile(
      leading: CircleAvatar(backgroundColor: _c(overall).withValues(alpha: 0.15),
          child: Text('$rank', style: TextStyle(color: _c(overall), fontWeight: FontWeight.w900))),
      title: Text('${d['employee']}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text('${d['rating']} · ${tr('منجزة', 'Done')} ${d['done']}/${d['total']}',
          style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
      trailing: Text('$overall', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: _c(overall))),
    ));
  }
}
