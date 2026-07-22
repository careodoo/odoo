import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;

/// Data-rich performance dashboard for a project: headline KPIs, a ranked
/// leaderboard, impact by source, a monthly trend, and the latest events.
class PerformanceScreen extends StatefulWidget {
  final int projectId;
  const PerformanceScreen({super.key, required this.projectId});
  @override
  State<PerformanceScreen> createState() => _PerformanceScreenState();
}

class _PerformanceScreenState extends State<PerformanceScreen> {
  Map<String, dynamic>? _d;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.pmsPerformance(widget.projectId);
      if (mounted) setState(() { _d = d; _error = null; });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  num _n(dynamic v) => v is num ? v : 0;

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(tr('الأداء', 'Performance'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
      ),
      body: d == null
          ? (_error != null
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('$_error', style: const TextStyle(color: Pms.red))))
              : const Center(child: CircularProgressIndicator()))
          : (d['empty'] == true
              ? _empty()
              : RefreshIndicator(onRefresh: _load, child: ListView(
                  padding: const EdgeInsets.fromLTRB(14, 14, 14, 30),
                  children: [
                    _kpiHero(d['kpis'] as Map),
                    const SizedBox(height: 16),
                    _sectionTitle(tr('المتصدّرون', 'Leaderboard'), Icons.emoji_events_rounded),
                    ..._leaderboard((d['leaderboard'] as List?) ?? const []),
                    const SizedBox(height: 16),
                    _sectionTitle(tr('الأثر حسب المصدر', 'Impact by source'), Icons.donut_large_rounded),
                    _bySource((d['by_source'] as List?) ?? const []),
                    const SizedBox(height: 16),
                    _sectionTitle(tr('الاتجاه الشهري', 'Monthly trend'), Icons.show_chart_rounded),
                    _byMonth((d['by_month'] as List?) ?? const []),
                    const SizedBox(height: 16),
                    _sectionTitle(tr('أحدث الأحداث', 'Recent events'), Icons.history_rounded),
                    ..._recent((d['recent'] as List?) ?? const []),
                  ],
                ))),
    );
  }

  Widget _empty() => Center(child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.insights_rounded, size: 60, color: Pms.slate),
          const SizedBox(height: 12),
          Text(tr('لا سجلّ أداء لهذا المشروع بعد', 'No performance records yet'),
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        ]),
      ));

  Widget _kpiHero(Map k) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: const LinearGradient(colors: [Pms.violet, Pms.deep],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Expanded(child: _bigKpi('${k['total_points']}', tr('إجمالي النقاط', 'Total points'))),
          Container(width: 1, height: 44, color: Colors.white24),
          Expanded(child: _bigKpi('${k['avg']}', tr('متوسط/عامل', 'Avg/worker'))),
          Container(width: 1, height: 44, color: Colors.white24),
          Expanded(child: _bigKpi('${k['events']}', tr('حدث', 'Events'))),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          _miniChip(Icons.trending_up_rounded, '${k['positive']} ${tr('إيجابي', 'positive')}', const Color(0xFF6EE7B7)),
          const SizedBox(width: 8),
          _miniChip(Icons.trending_down_rounded, '${k['negative']} ${tr('سلبي', 'negative')}', const Color(0xFFFCA5A5)),
          const SizedBox(width: 8),
          _miniChip(Icons.groups_rounded, '${k['evaluated']}/${k['workers']}', Colors.white),
        ]),
        if (k['top'] != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              const Text('🏆', style: TextStyle(fontSize: 18)),
              const SizedBox(width: 8),
              Expanded(child: Text('${tr('المتصدّر', 'Top')}: ${k['top']}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13))),
              Text('${k['top_points']} ${tr('نقطة', 'pts')}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
            ]),
          ),
        ],
      ]),
    );
  }

  Widget _bigKpi(String v, String l) => Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22)),
        const SizedBox(height: 2),
        Text(l, style: const TextStyle(color: Colors.white70, fontSize: 10.5, fontWeight: FontWeight.w600)),
      ]);

  Widget _miniChip(IconData ic, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 14, color: c),
          const SizedBox(width: 5),
          Text(t, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
        ]),
      );

  Widget _sectionTitle(String t, IconData ic) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 2),
        child: Row(children: [
          Icon(ic, size: 18, color: Pms.violet),
          const SizedBox(width: 8),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink)),
        ]),
      );

  List<Widget> _leaderboard(List rows) {
    final maxPts = rows.isEmpty ? 1.0 : rows.map((e) => _n((e as Map)['points']).abs()).fold<double>(1, (a, b) => b > a ? b.toDouble() : a);
    return [
      for (var i = 0; i < rows.length && i < 15; i++)
        _leaderRow(i, rows[i] as Map, maxPts),
    ];
  }

  Widget _leaderRow(int i, Map r, double maxPts) {
    final pts = _n(r['points']).toDouble();
    final medal = i == 0 ? '🥇' : i == 1 ? '🥈' : i == 2 ? '🥉' : '${i + 1}';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Row(children: [
        SizedBox(width: 30, child: Text(medal, textAlign: TextAlign.center,
            style: TextStyle(fontSize: i < 3 ? 20 : 14, fontWeight: FontWeight.w900, color: Pms.slate))),
        const SizedBox(width: 6),
        CircleAvatar(radius: 20, backgroundColor: Pms.bg,
            backgroundImage: r['image'] != null ? NetworkImage('${r['image']}') : null,
            child: r['image'] == null ? const Icon(Icons.person, color: Pms.slate, size: 20) : null),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${r['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
          const SizedBox(height: 4),
          ClipRRect(borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (pts.abs() / maxPts).clamp(0, 1).toDouble(), minHeight: 6,
              backgroundColor: Pms.bg,
              valueColor: AlwaysStoppedAnimation(pts >= 0 ? Pms.green : Pms.red))),
          const SizedBox(height: 3),
          Text('${r['events']} ${tr('حدث', 'events')} · ${r['pos']}+ / ${r['neg']}-',
              style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
        ])),
        const SizedBox(width: 8),
        Text('${pts >= 0 ? '+' : ''}${r['points']}',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: pts >= 0 ? Pms.green : Pms.red)),
      ]),
    );
  }

  Widget _bySource(List src) {
    final maxAbs = src.isEmpty ? 1.0 : src.map((e) => _n((e as Map)['points']).abs()).fold<double>(1, (a, b) => b > a ? b.toDouble() : a);
    const labelsAr = {'Task / Deadline': 'المهام', 'Attendance': 'الحضور', 'Penalty': 'الجزاءات',
        'Bonus': 'المكافآت', 'Manual': 'يدوي', 'Other': 'أخرى'};
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(children: [
        for (final s0 in src) ...[
          Builder(builder: (_) {
            final s = s0 as Map;
            final pts = _n(s['points']).toDouble();
            final label = labelsAr[s['label']] ?? '${s['label']}';
            return Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(children: [
              SizedBox(width: 78, child: Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700))),
              Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(5),
                child: LinearProgressIndicator(
                  value: (pts.abs() / maxAbs).clamp(0, 1).toDouble(), minHeight: 10,
                  backgroundColor: Pms.bg,
                  valueColor: AlwaysStoppedAnimation(pts >= 0 ? Pms.green : Pms.red)))),
              const SizedBox(width: 10),
              SizedBox(width: 52, child: Text('${pts >= 0 ? '+' : ''}${s['points']}',
                  textAlign: TextAlign.end,
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: pts >= 0 ? Pms.green : Pms.red))),
              SizedBox(width: 40, child: Text('${s['events']}',
                  textAlign: TextAlign.end, style: const TextStyle(fontSize: 11, color: Pms.slate))),
            ]));
          }),
        ],
      ]),
    );
  }

  Widget _byMonth(List months) {
    final maxAbs = months.isEmpty ? 1.0 : months.map((e) => _n((e as Map)['points']).abs()).fold<double>(1, (a, b) => b > a ? b.toDouble() : a);
    return Container(
      height: 150, padding: const EdgeInsets.fromLTRB(12, 14, 12, 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final m0 in months) ...[
            Expanded(child: Builder(builder: (_) {
              final m = m0 as Map;
              final pts = _n(m['points']).toDouble();
              final frac = (pts.abs() / maxAbs).clamp(0.0, 1.0);
              return Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                Text('${m['points']}', style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: Pms.slate)),
                const SizedBox(height: 3),
                Container(
                  height: 6 + frac * 74, margin: const EdgeInsets.symmetric(horizontal: 5),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: pts >= 0 ? [Pms.violet, Pms.deep] : [Pms.red, const Color(0xFF9B1C1C)],
                      begin: Alignment.topCenter, end: Alignment.bottomCenter),
                    borderRadius: BorderRadius.circular(6)),
                ),
                const SizedBox(height: 5),
                Text('${m['month']}'.substring(5), style: const TextStyle(fontSize: 10, color: Pms.slate)),
              ]);
            })),
          ],
        ]),
    );
  }

  List<Widget> _recent(List rows) {
    return [
      for (final r0 in rows.take(20))
        Builder(builder: (_) {
          final r = r0 as Map;
          final pts = _n(r['points']).toDouble();
          final pos = pts >= 0;
          return Container(
            margin: const EdgeInsets.only(bottom: 7),
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE5E7EB))),
            child: Row(children: [
              Container(width: 8, height: 40, decoration: BoxDecoration(
                  color: pos ? Pms.green : Pms.red, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['employee']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                const SizedBox(height: 2),
                Text('${r['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
                Text('${r['source_label']} · ${r['date']}',
                    style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
              ])),
              Text('${pos ? '+' : ''}${r['points']}',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: pos ? Pms.green : Pms.red)),
            ]),
          );
        }),
    ];
  }
}
