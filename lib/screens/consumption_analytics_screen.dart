import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'excel_export.dart';

/// Consumption analytics: period KPIs plus fully clickable breakdowns — by
/// material, facility, building, location and worker. Tapping any row drills
/// into the exact movement records behind it, with search, print and Excel.
class ConsumptionAnalyticsScreen extends StatefulWidget {
  const ConsumptionAnalyticsScreen({super.key});
  @override
  State<ConsumptionAnalyticsScreen> createState() => _ConsumptionAnalyticsScreenState();
}

class _ConsumptionAnalyticsScreenState extends State<ConsumptionAnalyticsScreen> {
  Future<Map<String, dynamic>>? _future;
  String _period = 'month';

  static const _navy = Color(0xFF0E3A5F);
  static const _accent = Color(0xFFC0392B);
  static const _periods = [
    ('day', 'اليوم', 'Today'), ('month', 'الشهر', 'Month'),
    ('year', 'السنة', 'Year'), ('all', 'الكل', 'All'),
  ];
  static const _sections = [
    ('top_materials', 'أكثر المواد استهلاكًا', 'Top materials', Icons.inventory_2_rounded, Color(0xFF0891B2), 'product_id'),
    ('by_facility', 'حسب المرفق', 'By facility', Icons.apartment_rounded, Color(0xFFC0392B), 'facility_id'),
    ('top_buildings', 'حسب المبنى', 'By building', Icons.business_rounded, Color(0xFF7C3AED), 'building_id'),
    ('top_locations', 'حسب الموقع/الدور', 'By location/floor', Icons.place_rounded, Color(0xFF16A34A), 'location_id'),
    ('top_employees', 'حسب المنفّذ', 'By worker', Icons.engineering_rounded, Color(0xFFF7A23B), 'employee_id'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientInvConsumption(period: _period);

  void _excel({String? filterKey, int? filterId, String? label}) {
    final buf = StringBuffer('/cafm/inv/consumption/export?type=issue&period=$_period');
    if (filterKey != null && filterId != null) buf.write('&$filterKey=$filterId');
    exportExcelFile(context,
        path: buf.toString(),
        fileName: 'consumption-$_period.xlsx',
        shareText: label ?? tr('تحليلات الاستهلاك', 'Consumption analytics'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(tr('تحليلات الاستهلاك', 'Consumption analytics')),
        backgroundColor: _accent, foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.grid_on_rounded), tooltip: tr('تصدير Excel', 'Export Excel'), onPressed: () => _excel()),
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
                selectedColor: _accent,
                labelStyle: TextStyle(color: _period == p.$1 ? Colors.white : _navy, fontWeight: FontWeight.w700),
                onSelected: (_) => setState(() { _period = p.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator(color: _accent));
            }
            final d = snap.data ?? const {};
            if (d['available'] == false) {
              return Center(child: Text(tr('المخزون غير مفعّل', 'Inventory not enabled'), style: const TextStyle(color: Colors.grey)));
            }
            return RefreshIndicator(
              color: _accent,
              onRefresh: () async => setState(_load),
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 24), children: [
                _kpis(d),
                for (final s in _sections) _section(s, ((d[s.$1] as List?) ?? const []).cast<Map>()),
                const SizedBox(height: 8),
              ]),
            );
          },
        )),
      ]),
    );
  }

  Widget _kpis(Map d) => CustomPaint(
        painter: const BrandPattern(opacity: 0.06),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [BoxShadow(color: _accent.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 6))],
          ),
          child: Row(children: [
            _kpi('${d['total_qty'] ?? 0}', tr('إجمالي المصروف', 'Total issued'), Icons.outbox_rounded),
            _kdiv(),
            _kpi('${d['total_value'] ?? 0}', tr('القيمة', 'Value'), Icons.payments_rounded),
            _kdiv(),
            _kpi('${d['issues'] ?? 0}', tr('عمليات', 'Issues'), Icons.receipt_long_rounded),
          ]),
        ),
      );

  Widget _kpi(String v, String l, IconData ic) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 18),
        const SizedBox(height: 4),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 10, fontWeight: FontWeight.w600)),
      ]));

  Widget _kdiv() => Container(width: 1, height: 34, color: Colors.white.withValues(alpha: 0.2));

  Widget _section((String, String, String, IconData, Color, String) s, List<Map> rows) {
    if (rows.isEmpty) return const SizedBox.shrink();
    final maxQty = rows.fold<double>(1, (m, r) => (r['qty'] as num?)?.toDouble() != null && numOf(r['qty']) > m ? numOf(r['qty']).toDouble() : m);
    return Container(
      margin: const EdgeInsets.only(top: 12),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 7, offset: const Offset(0, 3))],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(13, 11, 8, 11),
          color: s.$5.withValues(alpha: 0.07),
          child: Row(children: [
            Icon(s.$4, size: 18, color: s.$5),
            const SizedBox(width: 8),
            Expanded(child: Text(tr(s.$2, s.$3), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: s.$5))),
            Text(tr('${rows.length}', '${rows.length}'), style: TextStyle(fontSize: 11, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
          ]),
        ),
        for (var i = 0; i < rows.length && i < 8; i++) _row(rows[i], i, maxQty, s),
        if (rows.length > 8)
          TextButton(
            onPressed: () => _openRecords(s, null, tr(s.$2, s.$3)),
            child: Text(tr('عرض كل السجلات (${rows.length})', 'View all records (${rows.length})'),
                style: TextStyle(color: s.$5, fontWeight: FontWeight.w800, fontSize: 12.5)),
          ),
      ]),
    );
  }

  Widget _row(Map r, int i, double maxQty, (String, String, String, IconData, Color, String) s) {
    final qty = dblOf(r['qty'], 0.0);
    return InkWell(
      onTap: () => _openRecords(s, r['id'] as int?, '${r['label']}'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
        child: Row(children: [
          Container(
            width: 24, height: 24, alignment: Alignment.center,
            decoration: BoxDecoration(color: s.$5.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
            child: Text('${i + 1}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: s.$5)),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['label']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: maxQty > 0 ? (qty / maxQty).clamp(0.0, 1.0) : 0, minHeight: 4,
                backgroundColor: s.$5.withValues(alpha: 0.08),
                valueColor: AlwaysStoppedAnimation(s.$5),
              ),
            ),
          ])),
          const SizedBox(width: 10),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('$qty', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: s.$5)),
            if (r['value'] != null)
              Text('${r['value']}', style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
          ]),
          Icon(Icons.chevron_left_rounded, size: 18, color: Colors.grey.shade400),
        ]),
      ),
    );
  }

  void _openRecords((String, String, String, IconData, Color, String) s, int? id, String label) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => _ConsumptionRecordsScreen(
      title: label, filterKey: s.$6, filterId: id, period: _period, accent: s.$5,
      onExcel: () => _excel(filterKey: id != null ? s.$6 : null, filterId: id, label: label),
    )));
  }
}

/// The movement records behind a consumption breakdown row (or a whole section),
/// with search and Excel export.
class _ConsumptionRecordsScreen extends StatefulWidget {
  const _ConsumptionRecordsScreen({
    required this.title, required this.filterKey, required this.filterId,
    required this.period, required this.accent, required this.onExcel,
  });
  final String title;
  final String filterKey;
  final int? filterId;
  final String period;
  final Color accent;
  final VoidCallback onExcel;
  @override
  State<_ConsumptionRecordsScreen> createState() => _ConsumptionRecordsScreenState();
}

class _ConsumptionRecordsScreenState extends State<_ConsumptionRecordsScreen> {
  Future<List<dynamic>>? _future;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<AuthProvider>().api;
    _future = api.clientInvMoves(
      type: 'issue', period: widget.period, q: _q.isEmpty ? null : _q,
      facilityId: widget.filterKey == 'facility_id' ? widget.filterId : null,
      buildingId: widget.filterKey == 'building_id' ? widget.filterId : null,
      locationId: widget.filterKey == 'location_id' ? widget.filterId : null,
      productId: widget.filterKey == 'product_id' ? widget.filterId : null,
      employeeId: widget.filterKey == 'employee_id' ? widget.filterId : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
        backgroundColor: widget.accent, foregroundColor: Colors.white,
        actions: [IconButton(icon: const Icon(Icons.grid_on_rounded), tooltip: tr('تصدير Excel', 'Export Excel'), onPressed: widget.onExcel)],
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
          child: TextField(
            onChanged: (v) => setState(() { _q = v; _load(); }),
            decoration: InputDecoration(
              hintText: tr('ابحث بالمادة أو الموقع…', 'Search material or location…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              isDense: true, filled: true, fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            ),
          ),
        ),
        Expanded(child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = (snap.data ?? const []).cast<Map>();
            if (rows.isEmpty) {
              return Center(child: Text(tr('لا حركات مطابقة', 'No matching movements'), style: const TextStyle(color: Colors.grey)));
            }
            final totQty = rows.fold<double>(0, (s, m) => s + (dblOf(m['quantity'], 0.0)));
            final totVal = rows.fold<double>(0, (s, m) => s + (dblOf(m['total_cost'], 0.0)));
            return ListView(padding: const EdgeInsets.fromLTRB(12, 0, 12, 20), children: [
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
                child: Row(children: [
                  Text(tr('${rows.length} حركة', '${rows.length} moves'), style: TextStyle(fontWeight: FontWeight.w800, color: widget.accent)),
                  const Spacer(),
                  Text(tr('الكمية: ${totQty.toStringAsFixed(1)} · القيمة: ${totVal.toStringAsFixed(1)}',
                          'Qty: ${totQty.toStringAsFixed(1)} · Val: ${totVal.toStringAsFixed(1)}'),
                      style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: widget.accent)),
                ]),
              ),
              ...rows.map(_moveCard),
            ]);
          },
        )),
      ]),
    );
  }

  Widget _moveCard(Map m) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(13),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 5, offset: const Offset(0, 2))],
        ),
        child: Row(children: [
          Container(
            width: 40, height: 40, alignment: Alignment.center,
            decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(11)),
            child: Icon(Icons.outbox_rounded, size: 20, color: widget.accent),
          ),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${m['product']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Color(0xFF0E3A5F))),
            const SizedBox(height: 3),
            Text([
              if (m['date'] != null) '${m['date']}',
              if (m['location'] != null) '${m['location']}',
              if (m['employee'] != null) '${m['employee']}',
            ].join(' · '), maxLines: 2, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${m['quantity']} ${m['uom'] ?? ''}',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
            if (m['total_cost'] != null)
              Text('${m['total_cost']}', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
          ]),
        ]),
      );
}
