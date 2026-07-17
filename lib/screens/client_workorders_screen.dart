import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'work_order_detail_screen.dart';
import 'client_workorder_create.dart';

/// Every work order across the client's facilities: the numbers first, then the
/// cuts that explain them (how late, whose, which role), then the records.
class ClientWorkOrdersScreen extends StatefulWidget {
  const ClientWorkOrdersScreen({super.key, this.initialFilter = 'all', this.serviceType});

  /// Lets the home cockpit deep-link straight into a cut ('overdue', 'urgent'…).
  final String initialFilter;

  /// Optional: open pre-filtered to one service type.
  final String? serviceType;

  @override
  State<ClientWorkOrdersScreen> createState() => _ClientWorkOrdersScreenState();
}

class _ClientWorkOrdersScreenState extends State<ClientWorkOrdersScreen> {
  late String _state = widget.initialFilter;
  String _period = 'all';
  late String _service = widget.serviceType ?? 'all';
  String _priority = 'all';
  int? _employeeId;
  int? _facilityId;
  String _q = '';
  Timer? _debounce;
  bool _showFilters = false;
  Future<Map<String, dynamic>>? _future;

  static const _navy = Color(0xFF0E3A5F);

  static const _states = [
    ('all', 'الكل', 'All'),
    ('open', 'مفتوحة', 'Open'),
    ('overdue', 'متأخرة', 'Overdue'),
    ('urgent', 'عاجلة', 'Urgent'),
    ('in_progress', 'جارية', 'Active'),
    ('done', 'للاعتماد', 'To approve'),
    ('verified', 'مُعتمدة', 'Approved'),
  ];

  static const _periods = [
    ('all', 'كل الفترات', 'All time'), ('day', 'اليوم', 'Today'),
    ('week', 'الأسبوع', 'Week'), ('month', 'الشهر', 'Month'), ('year', 'السنة', 'Year'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientWorkOrders(
        state: _state, period: _period, serviceType: _service, priority: _priority,
        employeeId: _employeeId, facilityId: _facilityId, q: _q,
      );

  void _apply() => setState(_load);

  /// Typing shouldn't fire a request per keystroke.
  void _search(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 420), () {
      if (mounted) setState(() { _q = v; _load(); });
    });
  }

  int get _activeFilters =>
      (_period != 'all' ? 1 : 0) + (_service != 'all' ? 1 : 0) + (_priority != 'all' ? 1 : 0) +
      (_employeeId != null ? 1 : 0) + (_facilityId != null ? 1 : 0);

  void _clearFilters() => setState(() {
        _period = 'all'; _service = 'all'; _priority = 'all';
        _employeeId = null; _facilityId = null;
        _load();
      });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFFC0392B), foregroundColor: Colors.white,
        icon: const Icon(Icons.add_task_rounded),
        label: Text(tr('أمر عمل', 'New order'), style: const TextStyle(fontWeight: FontWeight.w900)),
        onPressed: () async {
          final created = await ClientWorkorderCreateSheet.open(context,
              presetServiceType: _service == 'all' ? null : _service);
          if (created == true && mounted) setState(_load);
        },
      ),
      appBar: AppBar(
        title: Text(tr('أوامر العمل', 'Work orders')),
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
        // ---- search ----
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: TextField(
            onChanged: _search,
            decoration: InputDecoration(
              hintText: tr('ابحث برقم الأمر أو العنوان أو الوصف…', 'Search by number, title or description…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              isDense: true, filled: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        // ---- state chips ----
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Row(children: [
            for (final f in _states)
              Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
                label: Text(tr(f.$2, f.$3), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                selected: _state == f.$1,
                onSelected: (_) => setState(() { _state = f.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => _apply(),
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
              final d = snap.data ?? const {};
              final wos = (d['records'] as List?) ?? const [];
              final st = (d['stats'] as Map?) ?? const {};
              final facets = (d['facets'] as Map?) ?? const {};
              final count = (d['count'] ?? 0) as int;
              final shown = (d['shown'] ?? 0) as int;
              return ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20), children: [
                if (_showFilters) ...[_filterPanel(facets), const SizedBox(height: 10)],
                _statStrip(st),
                const SizedBox(height: 10),
                if (((st['overdue'] ?? 0) as int) > 0) ...[
                  _overdueBreakdown(st), const SizedBox(height: 10),
                ],
                _distribution(st),
                const SizedBox(height: 10),
                if (((st['by_employee'] as List?) ?? const []).isNotEmpty) ...[
                  _byEmployee(st['by_employee'] as List), const SizedBox(height: 10),
                ],
                if (((st['by_job'] as List?) ?? const []).isNotEmpty) ...[
                  _byJob(st['by_job'] as List), const SizedBox(height: 10),
                ],
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 6, 4, 6),
                  child: Row(children: [
                    Text(tr('السجلات', 'Records'),
                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                    const SizedBox(width: 6),
                    Text(
                        // Be explicit when the list is capped — a silent cut
                        // would read as "this is everything".
                        shown < count
                            ? tr('عرض $shown من $count', 'showing $shown of $count')
                            : '$count',
                        style: TextStyle(color: cs.outline, fontSize: 11.5, fontWeight: FontWeight.w700)),
                  ]),
                ),
                if (wos.isEmpty)
                  Padding(padding: const EdgeInsets.symmetric(vertical: 40), child: Center(
                      child: Column(children: [
                        Icon(Icons.inbox_rounded, size: 40, color: cs.outline.withValues(alpha: 0.4)),
                        const SizedBox(height: 8),
                        Text(tr('لا أوامر عمل مطابقة.', 'No matching work orders.'),
                            style: TextStyle(color: cs.outline)),
                      ]))),
                for (final w in wos) _woCard(w as Map, cs),
              ]);
            },
          ),
        )),
      ]),
    );
  }

  // ---------------- stats ----------------

  Widget _statStrip(Map st) {
    final sla = (st['sla_rate'] ?? 0) is num ? (st['sla_rate'] as num).toDouble() : 0.0;
    return Column(children: [
      Row(children: [
        _stat(tr('الإجمالي', 'Total'), '${st['total'] ?? 0}', const Color(0xFF64748B)),
        const SizedBox(width: 8),
        _stat(tr('مفتوحة', 'Open'), '${st['open'] ?? 0}', const Color(0xFFF7A23B)),
        const SizedBox(width: 8),
        _stat(tr('متأخرة', 'Overdue'), '${st['overdue'] ?? 0}', const Color(0xFFE5484D)),
        const SizedBox(width: 8),
        _stat(tr('أُنجزت', 'Done'), '${st['done'] ?? 0}', const Color(0xFF16A34A)),
      ]),
      const SizedBox(height: 8),
      Row(children: [
        _stat(tr('عاجلة', 'Urgent'), '${st['urgent'] ?? 0}', const Color(0xFFDC2626)),
        const SizedBox(width: 8),
        _stat(tr('غير مُسندة', 'Unassigned'), '${st['unassigned'] ?? 0}', const Color(0xFF8B5CF6)),
        const SizedBox(width: 8),
        _stat(tr('التزام SLA', 'SLA'), '${sla.round()}%',
            sla >= 90 ? const Color(0xFF16A34A) : (sla >= 70 ? const Color(0xFFF7A23B) : const Color(0xFFE5484D))),
        const SizedBox(width: 8),
        _stat(tr('نسبة الإنجاز', 'Completion'), '${((st['completion_rate'] ?? 0) as num).round()}%',
            const Color(0xFF2F6DF6)),
      ]),
    ]);
  }

  Widget _stat(String label, String v, Color c) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
          decoration: BoxDecoration(
            color: c.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(13),
            border: Border.all(color: c.withValues(alpha: 0.24)),
          ),
          child: Column(children: [
            Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 16)),
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                style: TextStyle(color: c.withValues(alpha: 0.85), fontSize: 8.5, fontWeight: FontWeight.w700)),
          ]),
        ),
      );

  /// How late is late — one pile of "overdue" tells a manager nothing.
  Widget _overdueBreakdown(Map st) {
    final b = (st['overdue_buckets'] as Map?) ?? const {};
    final items = <(String, String, int, Color)>[
      ('خلال يوم', '≤1d', (b['d1'] ?? 0) as int, const Color(0xFFFBBF24)),
      ('1–3 أيام', '1–3d', (b['d3'] ?? 0) as int, const Color(0xFFF59E0B)),
      ('3–7 أيام', '3–7d', (b['w1'] ?? 0) as int, const Color(0xFFEA580C)),
      ('أسبوع–شهر', '1w–1mo', (b['m1'] ?? 0) as int, const Color(0xFFDC2626)),
      ('أكثر من شهر', '>1mo', (b['m1p'] ?? 0) as int, const Color(0xFF7F1D1D)),
    ];
    final total = items.fold<int>(0, (a, e) => a + e.$3);
    if (total == 0) return const SizedBox.shrink();
    return _panel(tr('توزيع التأخير', 'How overdue'), Icons.running_with_errors_rounded, const Color(0xFFE5484D), [
      // proportional bar — the shape of the problem at a glance
      ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: SizedBox(height: 9, child: Row(children: [
          for (final it in items)
            if (it.$3 > 0) Expanded(flex: it.$3, child: Container(color: it.$4)),
        ])),
      ),
      const SizedBox(height: 9),
      Wrap(spacing: 7, runSpacing: 7, children: [
        for (final it in items)
          if (it.$3 > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                  color: it.$4.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: it.$4.withValues(alpha: 0.3))),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 7, height: 7, decoration: BoxDecoration(color: it.$4, shape: BoxShape.circle)),
                const SizedBox(width: 5),
                Text(tr(it.$1, it.$2), style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: it.$4)),
                const SizedBox(width: 5),
                Text('${it.$3}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: it.$4)),
              ]),
            ),
      ]),
    ]);
  }

  Widget _distribution(Map st) {
    final byState = (st['by_state'] as Map?) ?? const {};
    final byService = (st['by_service'] as Map?) ?? const {};
    final byPriority = (st['by_priority'] as Map?) ?? const {};
    Widget block(String ar, String en, Map m, Color c) {
      final entries = m.entries.where((e) => ((e.value ?? 0) as int) > 0).toList();
      if (entries.isEmpty) return const SizedBox.shrink();
      final max = entries.fold<int>(1, (a, e) => (e.value as int) > a ? e.value as int : a);
      return _panel(tr(ar, en), Icons.bar_chart_rounded, c, [
        for (final e in entries) Padding(
          padding: const EdgeInsets.only(bottom: 7),
          child: Row(children: [
            SizedBox(width: 84, child: Text('${e.key}',
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700))),
            Expanded(child: ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: LinearProgressIndicator(
                value: (e.value as int) / max, minHeight: 8,
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

    return Column(children: [
      block('حسب الحالة', 'By state', byState, const Color(0xFF2F6DF6)),
      const SizedBox(height: 10),
      block('حسب الخدمة', 'By service', byService, const Color(0xFF0891B2)),
      const SizedBox(height: 10),
      block('حسب الأولوية', 'By priority', byPriority, const Color(0xFF8B5CF6)),
    ]);
  }

  Widget _byEmployee(List rows) => _panel(
        tr('حسب العامل', 'By worker'), Icons.person_search_rounded, const Color(0xFF0D9488), [
          for (final r in rows.take(8))
            InkWell(
              borderRadius: BorderRadius.circular(9),
              onTap: () => setState(() { _employeeId = r['id'] as int; _showFilters = true; _load(); }),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(children: [
                  CircleAvatar(radius: 12, backgroundColor: const Color(0xFF0D9488).withValues(alpha: 0.15),
                      child: Text('${r['name']}'.characters.first,
                          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Color(0xFF0D9488)))),
                  const SizedBox(width: 8),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${r['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                    if (r['job'] != null)
                      Text('${r['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500)),
                  ])),
                  _pill('${r['open']}', tr('مفتوح', 'open'), const Color(0xFFF7A23B)),
                  const SizedBox(width: 5),
                  if (((r['overdue'] ?? 0) as int) > 0)
                    _pill('${r['overdue']}', tr('متأخر', 'late'), const Color(0xFFE5484D)),
                  const SizedBox(width: 5),
                  _pill('${r['total']}', tr('إجمالي', 'total'), const Color(0xFF64748B)),
                ]),
              ),
            ),
        ]);

  Widget _byJob(List rows) => _panel(
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

  Widget _pill(String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(7)),
        child: Text('$v $l', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: c)),
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

  // ---------------- filters ----------------

  Widget _filterPanel(Map facets) {
    final services = (facets['services'] as List?) ?? const [];
    final facilities = (facets['facilities'] as List?) ?? const [];
    final employees = (facets['employees'] as List?) ?? const [];
    final priorities = (facets['priorities'] as List?) ?? const [];
    return _panel(tr('الفلاتر', 'Filters'), Icons.tune_rounded, _navy, [
      _dropRow(tr('الفترة', 'Period'), _period,
          [for (final p in _periods) (p.$1, tr(p.$2, p.$3))], (v) => setState(() { _period = v; _load(); })),
      if (services.isNotEmpty)
        _dropRow(tr('الخدمة', 'Service'), _service,
            [('all', tr('الكل', 'All')), for (final s in services) ('${s['value']}', '${s['label']}')],
            (v) => setState(() { _service = v; _load(); })),
      if (priorities.isNotEmpty)
        _dropRow(tr('الأولوية', 'Priority'), _priority,
            [('all', tr('الكل', 'All')), for (final p in priorities) ('${p['value']}', '${p['label']}')],
            (v) => setState(() { _priority = v; _load(); })),
      if (facilities.isNotEmpty)
        _dropRow(tr('المرفق', 'Facility'), _facilityId?.toString() ?? 'all',
            [('all', tr('الكل', 'All')), for (final f in facilities) ('${f['value']}', '${f['label']}')],
            (v) => setState(() { _facilityId = v == 'all' ? null : int.parse(v); _load(); })),
      if (employees.isNotEmpty)
        _dropRow(tr('العامل', 'Worker'), _employeeId?.toString() ?? 'all',
            [('all', tr('الكل', 'All')), for (final e in employees) ('${e['value']}', '${e['label']}')],
            (v) => setState(() { _employeeId = v == 'all' ? null : int.parse(v); _load(); })),
      if (_activeFilters > 0)
        Align(alignment: Alignment.centerLeft, child: TextButton.icon(
          onPressed: _clearFilters,
          icon: const Icon(Icons.clear_all_rounded, size: 16),
          label: Text(tr('مسح الفلاتر', 'Clear filters'), style: const TextStyle(fontSize: 12)),
        )),
    ]);
  }

  Widget _dropRow(String label, String value, List<(String, String)> opts, ValueChanged<String> onChanged) {
    // A stale selection (e.g. a worker who dropped out of the facet list after
    // another filter narrowed it) would throw inside DropdownButton.
    final safe = opts.any((o) => o.$1 == value) ? value : opts.first.$1;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        SizedBox(width: 62, child: Text(label,
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800))),
        Expanded(child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
              color: _navy.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _navy.withValues(alpha: 0.14))),
          child: DropdownButtonHideUnderline(child: DropdownButton<String>(
            value: safe,
            isDense: true, isExpanded: true,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.black87),
            items: [for (final o in opts) DropdownMenuItem(value: o.$1,
                child: Text(o.$2, maxLines: 1, overflow: TextOverflow.ellipsis))],
            onChanged: (v) { if (v != null) onChanged(v); },
          )),
        )),
      ]),
    );
  }

  // ---------------- records ----------------

  Widget _woCard(Map w, ColorScheme cs) {
    final late = ((w['overdue_days'] ?? 0) as num).toDouble();
    final prio = '${w['priority']}';
    final prioColor = prio == '3' ? const Color(0xFFDC2626)
        : prio == '2' ? const Color(0xFFF7A23B) : Colors.transparent;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => WorkOrderDetailScreen(id: w['id'] as int, title: '${w['title']}'))),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: Row(children: [
            // priority stripe — state you can read without parsing a number
            Container(width: 3.5, height: 44,
                decoration: BoxDecoration(color: prioColor, borderRadius: BorderRadius.circular(3))),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${w['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
              const SizedBox(height: 3),
              Text('${w['name']} · ${w['facility']}${w['location'] != null ? ' · ${w['location']}' : ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: cs.outline, fontSize: 11)),
              const SizedBox(height: 5),
              Row(children: [
                if (w['employee'] != null) ...[
                  Icon(Icons.person_outline_rounded, size: 11, color: cs.outline),
                  const SizedBox(width: 2),
                  Flexible(child: Text('${w['employee']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10, color: cs.outline, fontWeight: FontWeight.w600))),
                  const SizedBox(width: 8),
                ] else
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    margin: const EdgeInsets.only(left: 6),
                    decoration: BoxDecoration(
                        color: const Color(0xFF8B5CF6).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(5)),
                    child: Text(tr('غير مُسند', 'Unassigned'),
                        style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, color: Color(0xFF8B5CF6))),
                  ),
                if (late > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                        color: const Color(0xFFE5484D).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6)),
                    child: Text(
                        late >= 1
                            ? tr('متأخر ${late.round()} يوم', '${late.round()}d late')
                            : tr('متأخر ${(late * 24).round()} ساعة', '${(late * 24).round()}h late'),
                        style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: Color(0xFFE5484D))),
                  ),
              ]),
            ])),
            const SizedBox(width: 8),
            WoStateBadge('${w['state']}'),
          ]),
        ),
      ),
    );
  }
}
