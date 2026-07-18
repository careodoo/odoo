import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'client_workorders_screen.dart';
import 'client_structure_screen.dart';
import 'client_assets_screen.dart';
import 'client_team_screen.dart';
import 'client_services_screen.dart';
import 'requests_screen.dart';
import 'attendance_screen.dart';

/// The client's analytics tab: every number the module holds for this customer
/// — tickets, timing, people, estate — under one set of filters that applies to
/// all of it.
class ClientAnalyticsScreen extends StatefulWidget {
  const ClientAnalyticsScreen({super.key});
  @override
  State<ClientAnalyticsScreen> createState() => _ClientAnalyticsScreenState();
}

class _ClientAnalyticsScreenState extends State<ClientAnalyticsScreen> {
  Future<Map<String, dynamic>>? _future;
  String _period = 'month';
  String _service = 'all';
  String _priority = 'all';
  String _state = 'all';
  int? _facilityId;
  int? _employeeId;
  bool _showFilters = false;

  static const _navy = Color(0xFF0E3A5F);
  static const _periods = [
    ('day', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'), ('year', 'السنة', 'Year'), ('all', 'الكل', 'All'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientAnalytics(
      period: _period, serviceType: _service, priority: _priority,
      state: _state, facilityId: _facilityId, employeeId: _employeeId);

  int get _activeFilters =>
      (_service != 'all' ? 1 : 0) + (_priority != 'all' ? 1 : 0) + (_state != 'all' ? 1 : 0) +
      (_facilityId != null ? 1 : 0) + (_employeeId != null ? 1 : 0);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الإحصائيات', 'Analytics')),
        actions: [
          Stack(alignment: Alignment.center, children: [
            IconButton(
              icon: Icon(_showFilters ? Icons.filter_alt : Icons.filter_alt_outlined),
              tooltip: tr('الفلاتر', 'Filters'),
              onPressed: () => setState(() => _showFilters = !_showFilters),
            ),
            if (_activeFilters > 0)
              Positioned(top: 8, right: 8, child: Container(
                padding: const EdgeInsets.all(3),
                decoration: const BoxDecoration(color: Color(0xFFE5484D), shape: BoxShape.circle),
                child: Text('$_activeFilters',
                    style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.w900)),
              )),
          ]),
        ],
      ),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final p in _periods)
              Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
                label: Text(tr(p.$2, p.$3), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                selected: _period == p.$1,
                onSelected: (_) => setState(() { _period = p.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => setState(_load),
          child: FutureBuilder<Map<String, dynamic>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) {
                return ListView(children: [
                  const SizedBox(height: 120),
                  Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline))),
                ]);
              }
              final d = snap.data!;
              final k = d['kpis'] as Map;
              return ListView(padding: const EdgeInsets.fromLTRB(14, 4, 14, 26), children: [
                if (_showFilters) ...[_filterPanel(d), const SizedBox(height: 12)],
                _headline(k),
                const SizedBox(height: 12),
                _trend((d['daily'] as List?) ?? const []),
                const SizedBox(height: 12),
                _section(tr('أوامر العمل', 'Work orders')),
                _ticketGrid(k),
                const SizedBox(height: 12),
                _section(tr('الزمن', 'Timing')),
                Row(children: [
                  Expanded(child: _mini(tr('متوسط الاستجابة', 'Avg. response'), _dur(k['avg_response_min']), Icons.bolt_rounded, const Color(0xFFF7A23B))),
                  const SizedBox(width: 9),
                  Expanded(child: _mini(tr('متوسط الإنجاز', 'Avg. duration'), _dur(k['avg_duration_min']), Icons.timer_outlined, const Color(0xFF0891B2))),
                  const SizedBox(width: 9),
                  Expanded(child: _mini(tr('ساعات العمل', 'Work hours'), '${k['work_hours'] ?? 0}', Icons.schedule_rounded, const Color(0xFF6366F1))),
                ]),
                if (((k['overdue'] ?? 0) as int) > 0) ...[
                  const SizedBox(height: 12),
                  _buckets((d['overdue_buckets'] as Map?) ?? const {}),
                ],
                const SizedBox(height: 12),
                _section(tr('القوى العاملة', 'Workforce')),
                _workforce((d['workforce'] as Map?) ?? const {}, k),
                const SizedBox(height: 12),
                _section(tr('العهدة والأصول', 'Assets & estate')),
                _estateGrid(k),
                const SizedBox(height: 14),
                _bars(tr('حسب الخدمة', 'By service'), _totals(d['by_service']), const Color(0xFF0891B2)),
                const SizedBox(height: 10),
                _bars(tr('حسب الحالة', 'By state'), (d['by_state'] as Map).cast<String, dynamic>(), const Color(0xFF2F6DF6)),
                const SizedBox(height: 10),
                _bars(tr('حسب الأولوية', 'By priority'), (d['by_priority'] as Map).cast<String, dynamic>(), const Color(0xFF8B5CF6)),
                if (((d['by_job'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _jobs(d['by_job'] as List),
                ],
                if (((d['top_locations'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _locations(d['top_locations'] as List),
                ],
                if (((d['employees'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _employees(d['employees'] as List),
                ],
                if (((d['facilities'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _facilities(d['facilities'] as List),
                ],
              ]);
            },
          ),
        )),
      ]),
    );
  }

  /// by_service values are {total, open, done, overdue} — flatten to totals.
  Map<String, dynamic> _totals(dynamic m) => {
        for (final e in (m as Map).entries) '${e.key}': (e.value as Map)['total'],
      };

  String _dur(dynamic minutes) {
    final m = (minutes ?? 0) is num ? (minutes as num).toDouble() : 0.0;
    if (m < 60) return tr('${m.round()} د', '${m.round()}m');
    if (m < 1440) return tr('${(m / 60).toStringAsFixed(1)} س', '${(m / 60).toStringAsFixed(1)}h');
    return tr('${(m / 1440).toStringAsFixed(1)} يوم', '${(m / 1440).toStringAsFixed(1)}d');
  }

  Widget _section(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 7, top: 2),
        child: Row(children: [
          Container(width: 3, height: 13,
              decoration: BoxDecoration(color: _navy, borderRadius: BorderRadius.circular(2))),
          const SizedBox(width: 6),
          Text(t, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: _navy)),
        ]),
      );

  Widget _headline(Map k) {
    final done = (k['completion_pct'] ?? 0) is num ? (k['completion_pct'] as num).toDouble() : 0.0;
    final sla = (k['sla'] ?? 0) is num ? (k['sla'] as num).toDouble() : 0.0;
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF17547F), _navy],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(children: [
        _ring(tr('نسبة الإنجاز', 'Completion'), done, const Color(0xFF4ADE80)),
        const SizedBox(width: 14),
        _ring(tr('التزام SLA', 'SLA'), sla,
            sla >= 90 ? const Color(0xFF4ADE80) : (sla >= 70 ? const Color(0xFFFBBF24) : const Color(0xFFFCA5A5))),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _line(tr('إجمالي الأوامر', 'Total orders'), '${k['total'] ?? 0}'),
          _line(tr('مفتوحة', 'Open'), '${k['open'] ?? 0}'),
          _line(tr('متأخرة', 'Overdue'), '${k['overdue'] ?? 0}', danger: ((k['overdue'] ?? 0) as int) > 0),
          _line(tr('غير مُسندة', 'Unassigned'), '${k['unassigned'] ?? 0}'),
        ])),
      ]),
    );
  }

  Widget _ring(String l, double pct, Color c) => Column(children: [
        SizedBox(width: 58, height: 58, child: Stack(alignment: Alignment.center, children: [
          CircularProgressIndicator(
            value: (pct / 100).clamp(0.0, 1.0), strokeWidth: 5.5,
            backgroundColor: Colors.white.withValues(alpha: 0.15),
            valueColor: AlwaysStoppedAnimation(c),
          ),
          Text('${pct.round()}%',
              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w900)),
        ])),
        const SizedBox(height: 5),
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.7),
            fontSize: 8.5, fontWeight: FontWeight.w700)),
      ]);

  Widget _line(String l, String v, {bool danger = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          Expanded(child: Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 10.5, fontWeight: FontWeight.w600))),
          Text(v, style: TextStyle(
              color: danger ? const Color(0xFFFCA5A5) : Colors.white,
              fontSize: 13, fontWeight: FontWeight.w900)),
        ]),
      );

  /// Created vs done over the period — the one chart that says whether the
  /// backlog is growing or shrinking.
  Widget _trend(List daily) {
    if (daily.isEmpty) return const SizedBox.shrink();
    final maxV = daily.fold<int>(1, (m, e) {
      final d = e as Map;
      final v = ((d['created'] ?? 0) as int) > ((d['done'] ?? 0) as int)
          ? (d['created'] ?? 0) as int : (d['done'] ?? 0) as int;
      return v > m ? v : m;
    });
    final created = daily.fold<int>(0, (a, e) => a + ((e as Map)['created'] ?? 0) as int);
    final done = daily.fold<int>(0, (a, e) => a + ((e as Map)['done'] ?? 0) as int);
    return _panel(tr('الاتجاه اليومي', 'Daily trend'), Icons.show_chart_rounded, const Color(0xFF0891B2), [
      Row(children: [
        _legend(tr('واردة', 'Created'), const Color(0xFF0EA5E9), created),
        const SizedBox(width: 12),
        _legend(tr('مُنجزة', 'Done'), const Color(0xFF16A34A), done),
        const Spacer(),
        // The honest read of the two bars: is the pile growing?
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
          decoration: BoxDecoration(
              color: (created > done ? const Color(0xFFE5484D) : const Color(0xFF16A34A))
                  .withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(7)),
          child: Text(
              created > done
                  ? tr('المتراكم يزيد +${created - done}', 'Backlog +${created - done}')
                  : tr('المتراكم ينخفض ${done - created}', 'Backlog −${done - created}'),
              style: TextStyle(fontSize: 9, fontWeight: FontWeight.w900,
                  color: created > done ? const Color(0xFFE5484D) : const Color(0xFF16A34A))),
        ),
      ]),
      const SizedBox(height: 10),
      SizedBox(height: 62, child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        for (final e in daily)
          Expanded(child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 0.7),
            child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
              Container(
                height: 2 + 28 * (((e as Map)['created'] ?? 0) as int) / maxV,
                decoration: BoxDecoration(
                    color: const Color(0xFF0EA5E9),
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(2))),
              ),
              const SizedBox(height: 1.5),
              Container(
                height: 2 + 28 * (((e)['done'] ?? 0) as int) / maxV,
                decoration: BoxDecoration(
                    color: const Color(0xFF16A34A),
                    borderRadius: const BorderRadius.vertical(bottom: Radius.circular(2))),
              ),
            ]),
          )),
      ])),
      const SizedBox(height: 4),
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text('${(daily.first as Map)['date']}'.substring(5),
            style: TextStyle(fontSize: 8, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
        Text('${(daily.last as Map)['date']}'.substring(5),
            style: TextStyle(fontSize: 8, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
      ]),
    ]);
  }

  Widget _legend(String l, Color c, int v) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 4),
        Text('$l $v', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: c)),
      ]);

  void _wo(String filter) => Navigator.push(context, MaterialPageRoute(
      builder: (_) => ClientWorkOrdersScreen(initialFilter: filter)));

  Widget _ticketGrid(Map k) => GridView.count(
        crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 0.9,
        children: [
          StatCard(label: tr('إجمالي', 'Total'), value: k['total'] ?? 0, color: const Color(0xFF475569), icon: Icons.workspaces, onTap: () => _wo('all')),
          StatCard(label: tr('مفتوحة', 'Open'), value: k['open'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.inbox, onTap: () => _wo('open')),
          StatCard(label: tr('قيد التنفيذ', 'Active'), value: k['in_progress'] ?? 0, color: const Color(0xFFF59E0B), icon: Icons.timelapse, onTap: () => _wo('in_progress')),
          StatCard(label: tr('مُسنَدة', 'Assigned'), value: k['assigned'] ?? 0, color: const Color(0xFF0891B2), icon: Icons.assignment_ind, onTap: () => _wo('open')),
          StatCard(label: tr('منجزة', 'Done'), value: k['done'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.check_circle, onTap: () => _wo('done')),
          StatCard(label: tr('مُعتمدة', 'Verified'), value: k['verified'] ?? 0, color: const Color(0xFF15803D), icon: Icons.verified, onTap: () => _wo('verified')),
          StatCard(label: tr('متأخرة', 'Overdue'), value: k['overdue'] ?? 0, color: const Color(0xFFE5484D), icon: Icons.timer_off, onTap: () => _wo('overdue')),
          StatCard(label: tr('غير مُسندة', 'Unassigned'), value: k['unassigned'] ?? 0, color: const Color(0xFFB45309), icon: Icons.person_off, onTap: () => _wo('open')),
        ],
      );

  Widget _workforce(Map w, Map k) => GridView.count(
        crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 0.9,
        children: [
          StatCard(label: tr('بالموقع الآن', 'On site'), value: (w['present_now'] ?? 0) as int, color: const Color(0xFF16A34A), icon: Icons.person_pin_circle,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AttendanceScreen()))),
          StatCard(label: tr('الفِرَق', 'Teams'), value: (w['teams'] ?? k['teams'] ?? 0) as int, color: const Color(0xFF14B8A6), icon: Icons.groups,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientTeamScreen()))),
          StatCard(label: tr('الأعضاء', 'Members'), value: (k['members'] ?? 0) as int, color: const Color(0xFF0D9488), icon: Icons.badge,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientTeamScreen()))),
          StatCard(label: tr('ساعات الشهر', 'Hours (mo.)'), value: ((w['hours_month'] ?? 0) as num).round(), color: const Color(0xFF6366F1), icon: Icons.schedule,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AttendanceScreen()))),
        ],
      );

  Widget _estateGrid(Map k) => GridView.count(
        crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 0.9,
        children: [
          StatCard(label: tr('المرافق', 'Facilities'), value: k['facilities'] ?? 0, color: const Color(0xFF6366F1), icon: Icons.location_city,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientStructureScreen(focus: 'facilities')))),
          StatCard(label: tr('المباني', 'Buildings'), value: k['buildings'] ?? 0, color: const Color(0xFF8B5CF6), icon: Icons.apartment,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientStructureScreen(focus: 'buildings')))),
          StatCard(label: tr('المواقع', 'Locations'), value: k['locations'] ?? 0, color: const Color(0xFF0EA5E9), icon: Icons.qr_code,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientStructureScreen(focus: 'locations')))),
          StatCard(label: tr('الأصول', 'Assets'), value: k['assets'] ?? 0, color: const Color(0xFF0891B2), icon: Icons.precision_manufacturing,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientAssetsScreen()))),
          StatCard(label: tr('الصيانة الوقائية', 'PPM'), value: k['ppm'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.event_repeat),
          StatCard(label: tr('طلبات جديدة', 'New requests'), value: k['requests_new'] ?? 0, color: const Color(0xFFF59E0B), icon: Icons.mark_email_unread,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RequestsScreen()))),
          StatCard(label: tr('الخدمات', 'Services'), value: k['services'] ?? 0, color: const Color(0xFF37C98A), icon: Icons.design_services,
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ClientServicesScreen()))),
        ],
      );

  Widget _buckets(Map b) {
    final items = <(String, String, int, Color)>[
      ('خلال يوم', '≤1d', (b['d1'] ?? 0) as int, const Color(0xFFFBBF24)),
      ('1–3 أيام', '1–3d', (b['d3'] ?? 0) as int, const Color(0xFFF59E0B)),
      ('3–7 أيام', '3–7d', (b['w1'] ?? 0) as int, const Color(0xFFEA580C)),
      ('أسبوع–شهر', '1w–1mo', (b['m1'] ?? 0) as int, const Color(0xFFDC2626)),
      ('أكثر من شهر', '>1mo', (b['m1p'] ?? 0) as int, const Color(0xFF7F1D1D)),
    ];
    if (items.every((e) => e.$3 == 0)) return const SizedBox.shrink();
    return _panel(tr('توزيع التأخير', 'How overdue'), Icons.running_with_errors_rounded, const Color(0xFFE5484D), [
      ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: SizedBox(height: 9, child: Row(children: [
          for (final it in items) if (it.$3 > 0) Expanded(flex: it.$3, child: Container(color: it.$4)),
        ])),
      ),
      const SizedBox(height: 9),
      Wrap(spacing: 7, runSpacing: 7, children: [
        for (final it in items) if (it.$3 > 0)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
                color: it.$4.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8),
                border: Border.all(color: it.$4.withValues(alpha: 0.3))),
            child: Text('${tr(it.$1, it.$2)} · ${it.$3}',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: it.$4)),
          ),
      ]),
    ]);
  }

  Widget _bars(String title, Map<String, dynamic> m, Color c) {
    final entries = m.entries.where((e) => ((e.value ?? 0) as num) > 0).toList();
    if (entries.isEmpty) return const SizedBox.shrink();
    final max = entries.fold<num>(1, (a, e) => (e.value as num) > a ? e.value as num : a);
    return _panel(title, Icons.bar_chart_rounded, c, [
      for (final e in entries) Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(children: [
          SizedBox(width: 92, child: Text('${e.key}',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700))),
          Expanded(child: ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: LinearProgressIndicator(
              value: (e.value as num) / max, minHeight: 8,
              backgroundColor: c.withValues(alpha: 0.10),
              valueColor: AlwaysStoppedAnimation(c),
            ),
          )),
          const SizedBox(width: 7),
          SizedBox(width: 26, child: Text('${e.value}', textAlign: TextAlign.end,
              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: c))),
        ]),
      ),
    ]);
  }

  Widget _jobs(List rows) => _panel(
        tr('حسب الدور', 'By role'), Icons.badge_rounded, const Color(0xFF6366F1), [
          Wrap(spacing: 7, runSpacing: 7, children: [
            for (final r in rows)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                decoration: BoxDecoration(
                    color: const Color(0xFF6366F1).withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(color: const Color(0xFF6366F1).withValues(alpha: 0.22))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('${r['name']}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
                  const SizedBox(width: 6),
                  Text('${r['total']}',
                      style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: Color(0xFF6366F1))),
                  if (((r['overdue'] ?? 0) as int) > 0) ...[
                    const SizedBox(width: 4),
                    Text('(${r['overdue']} ${tr('متأخر', 'late')})',
                        style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFFE5484D))),
                  ],
                ]),
              ),
          ]),
        ]);

  Widget _locations(List rows) => _panel(
        tr('أكثر المواقع عملًا', 'Busiest locations'), Icons.place_rounded, const Color(0xFF0EA5E9), [
          for (final r in rows.take(8)) Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
                if (r['building'] != null)
                  Text('${r['building']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 9, color: Colors.grey.shade500)),
              ])),
              _tag('${r['total']}', tr('إجمالي', 'total'), Colors.grey.shade600),
              const SizedBox(width: 5),
              _tag('${r['open']}', tr('مفتوح', 'open'), const Color(0xFFF7A23B)),
              if (((r['overdue'] ?? 0) as int) > 0) ...[
                const SizedBox(width: 5),
                _tag('${r['overdue']}', tr('متأخر', 'late'), const Color(0xFFE5484D)),
              ],
            ]),
          ),
        ]);

  Widget _employees(List rows) => _panel(
        tr('أداء العاملين', 'Worker performance'), Icons.people_alt_rounded, const Color(0xFF0D9488), [
          for (final e in rows.take(12)) Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              CircleAvatar(radius: 11, backgroundColor: const Color(0xFF0D9488).withValues(alpha: 0.14),
                  child: Text('${e['name']}'.characters.first,
                      style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: Color(0xFF0D9488)))),
              const SizedBox(width: 8),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${e['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
                if (e['job_title'] != null)
                  Text('${e['job_title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 9, color: Colors.grey.shade500)),
              ])),
              _tag('${e['completion_pct']}%', tr('إنجاز', 'done'),
                  ((e['completion_pct'] ?? 0) as num) >= 70 ? const Color(0xFF16A34A) : const Color(0xFFF7A23B)),
              const SizedBox(width: 5),
              _tag('${e['open']}', tr('مفتوح', 'open'), const Color(0xFF2F6DF6)),
              if (((e['overdue'] ?? 0) as int) > 0) ...[
                const SizedBox(width: 5),
                _tag('${e['overdue']}', tr('متأخر', 'late'), const Color(0xFFE5484D)),
              ],
            ]),
          ),
        ]);

  Widget _facilities(List rows) => _panel(
        tr('حسب المرفق', 'By facility'), Icons.location_city_rounded, const Color(0xFF6366F1), [
          for (final f in rows) Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              Expanded(child: Text('${f['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800))),
              _tag('${f['open']}', tr('مفتوح', 'open'), const Color(0xFFF7A23B)),
              const SizedBox(width: 5),
              _tag('${f['done']}', tr('منجز', 'done'), const Color(0xFF16A34A)),
              const SizedBox(width: 5),
              _tag('${f['overdue']}', tr('متأخر', 'late'), const Color(0xFFE5484D)),
            ]),
          ),
        ]);

  Widget _tag(String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(6)),
        child: Text('$v $l', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: c)),
      );

  Widget _mini(String l, String v, IconData ic, Color c) => Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(13),
            border: Border.all(color: c.withValues(alpha: 0.2))),
        child: Column(children: [
          Icon(ic, size: 15, color: c),
          const SizedBox(height: 3),
          Text(v, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: c)),
          Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
        ]),
      );

  Widget _panel(String title, IconData ic, Color c, List<Widget> children) => Container(
        padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(ic, size: 15, color: c),
            const SizedBox(width: 6),
            Text(title, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: c)),
          ]),
          const SizedBox(height: 10),
          ...children,
        ]),
      );

  Widget _filterPanel(Map d) {
    final facets = (d['facets'] as Map?) ?? const {};
    final services = (d['service_types'] as List?) ?? const [];
    final facilities = (facets['facilities'] as List?) ?? const [];
    final employees = (facets['employees'] as List?) ?? const [];
    final states = (facets['states'] as List?) ?? const [];
    final priorities = (facets['priorities'] as List?) ?? const [];
    return _panel(tr('الفلاتر', 'Filters'), Icons.tune_rounded, _navy, [
      if (services.isNotEmpty)
        _drop(tr('الخدمة', 'Service'), _service,
            [('all', tr('الكل', 'All')), for (final s in services) ('${s['v']}', '${s['l']}')],
            (v) => setState(() { _service = v; _load(); })),
      if (states.isNotEmpty)
        _drop(tr('الحالة', 'State'), _state,
            [('all', tr('الكل', 'All')), for (final s in states) ('${s['value']}', '${s['label']}')],
            (v) => setState(() { _state = v; _load(); })),
      if (priorities.isNotEmpty)
        _drop(tr('الأولوية', 'Priority'), _priority,
            [('all', tr('الكل', 'All')), for (final p in priorities) ('${p['value']}', '${p['label']}')],
            (v) => setState(() { _priority = v; _load(); })),
      if (facilities.isNotEmpty)
        _drop(tr('المرفق', 'Facility'), _facilityId?.toString() ?? 'all',
            [('all', tr('الكل', 'All')), for (final f in facilities) ('${f['value']}', '${f['label']}')],
            (v) => setState(() { _facilityId = v == 'all' ? null : int.parse(v); _load(); })),
      if (employees.isNotEmpty)
        _drop(tr('العامل', 'Worker'), _employeeId?.toString() ?? 'all',
            [('all', tr('الكل', 'All')), for (final e in employees) ('${e['value']}', '${e['label']}')],
            (v) => setState(() { _employeeId = v == 'all' ? null : int.parse(v); _load(); })),
      if (_activeFilters > 0)
        Align(alignment: Alignment.centerLeft, child: TextButton.icon(
          onPressed: () => setState(() {
            _service = 'all'; _priority = 'all'; _state = 'all';
            _facilityId = null; _employeeId = null;
            _load();
          }),
          icon: const Icon(Icons.clear_all_rounded, size: 16),
          label: Text(tr('مسح الفلاتر', 'Clear filters'), style: const TextStyle(fontSize: 12)),
        )),
    ]);
  }

  Widget _drop(String label, String value, List<(String, String)> opts, ValueChanged<String> onChanged) {
    // A stale selection (a worker who left the facet list once another filter
    // narrowed it) would throw inside DropdownButton.
    final safe = opts.any((o) => o.$1 == value) ? value : opts.first.$1;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        SizedBox(width: 58, child: Text(label,
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800))),
        Expanded(child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
              color: _navy.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _navy.withValues(alpha: 0.14))),
          child: DropdownButtonHideUnderline(child: DropdownButton<String>(
            value: safe, isDense: true, isExpanded: true,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.black87),
            items: [for (final o in opts) DropdownMenuItem(value: o.$1,
                child: Text(o.$2, maxLines: 1, overflow: TextOverflow.ellipsis))],
            onChanged: (v) { if (v != null) onChanged(v); },
          )),
        )),
      ]),
    );
  }
}
