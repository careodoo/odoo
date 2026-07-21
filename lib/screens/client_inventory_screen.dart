import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'scan_screen.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';
import 'consumption_analytics_screen.dart';

/// Client internal inventory — a professional console: KPI header (clickable),
/// store + kind + movement-type + period filters, live search, and every stock
/// item / movement opening a rich detail sheet. Keeps the scan-to-issue flow.
class ClientInventoryScreen extends StatefulWidget {
  const ClientInventoryScreen({super.key});
  @override
  State<ClientInventoryScreen> createState() => _ClientInventoryScreenState();
}

const _navy = Color(0xFF0E3A5F);
const _accent = Color(0xFF0E3A5F);

class _ClientInventoryScreenState extends State<ClientInventoryScreen> {
  Map<String, dynamic>? _summary;
  List<dynamic> _stores = [];
  List<dynamic> _locations = [];
  int? _storeId;
  String _kind = 'items'; // items | low | moves
  String _moveType = 'all';
  String _period = 'all';
  String _q = '';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ('items', '📦', 'الأرصدة', 'Stock'),
    ('low', '⚠️', 'منخفض', 'Low'),
    ('moves', '🔄', 'الحركات', 'Moves'),
  ];
  static const _moveTypes = [
    ('all', 'الكل', 'All'), ('receipt', 'استلام', 'Receipt'), ('issue', 'صرف', 'Issue'),
    ('transfer', 'تحويل', 'Transfer'), ('adjust', 'تسوية', 'Adjust'), ('return', 'مرتجع', 'Return'),
  ];
  static const _periods = [
    ('all', 'كل الفترات', 'All time'), ('day', 'اليوم', 'Today'),
    ('month', 'هذا الشهر', 'Month'), ('year', 'هذه السنة', 'Year'),
  ];
  static const _moveColors = {
    'receipt': Color(0xFF16A34A), 'issue': Color(0xFFE11D48), 'transfer': Color(0xFF6366F1),
    'adjust': Color(0xFFF59E0B), 'return': Color(0xFF0891B2),
  };

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    final api = context.read<AuthProvider>().api;
    try {
      final s = await api.clientInvSummary();
      final st = await api.clientInvStores();
      List<dynamic> locs = [];
      try { locs = await api.clientInvLocations(); } catch (_) {}
      // pre-select the first store, otherwise "issue materials" has nothing to
      // issue from and reports "pick a store first" even when there is only one.
      if (mounted) setState(() {
        _summary = s; _stores = st; _locations = locs;
        _storeId ??= st.isNotEmpty ? st.first['id'] as int? : null;
      });
    } catch (_) {}
    _load();
  }

  void _load() => setState(() {
        final api = context.read<AuthProvider>().api;
        _list = _kind == 'moves'
            ? api.clientInvMoves(type: _moveType == 'all' ? null : _moveType,
                period: _period == 'all' ? null : _period, q: _q.isEmpty ? null : _q)
            : api.clientInvItems(storeId: _storeId, low: _kind == 'low');
      });

  List<dynamic> _applySearch(List<dynamic> rows) {
    if (_q.isEmpty || _kind == 'moves') return rows; // moves search server-side
    final q = _q.toLowerCase();
    return rows.where((r) {
      final m = r as Map;
      return '${m['product']} ${m['barcode'] ?? ''} ${m['store'] ?? ''}'.toLowerCase().contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        title: Text(tr('المخزون الداخلي', 'Inventory')),
        backgroundColor: _navy, foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.insights_rounded), tooltip: tr('تحليلات الاستهلاك', 'Consumption'),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ConsumptionAnalyticsScreen()))),
        ],
      ),
      floatingActionButton: _issueButton(),
      body: Column(children: [
        if (s != null && s['available'] == true) _statHeader(s),
        _searchBar(),
        _kindBar(),
        if (_kind == 'moves') _movesFilters() else if (_stores.length > 1) _storeBar(),
        Expanded(child: FutureBuilder<List<dynamic>>(
          future: _list,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _accent));
            final rows = _applySearch(snap.data!);
            if (rows.isEmpty) return _empty();
            return RefreshIndicator(
              color: _accent,
              onRefresh: () async { _load(); await _list; },
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(10, 6, 10, 90),
                itemCount: rows.length,
                itemBuilder: (_, i) => _kind == 'moves' ? _moveCard(rows[i] as Map) : _itemCard(rows[i] as Map),
              ),
            );
          },
        )),
      ]),
    );
  }

  // ---------------------------------------------------------------- header ---
  Widget _statHeader(Map s) => SizedBox(
        height: 92,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(10, 10, 10, 4), children: [
          _kpi('🏬', '${s['stores'] ?? 0}', tr('المخازن', 'Stores'), const Color(0xFF6366F1), () { setState(() => _kind = 'items'); _load(); }),
          _kpi('📦', '${s['items'] ?? 0}', tr('الأصناف', 'Items'), const Color(0xFF0891B2), () { setState(() => _kind = 'items'); _load(); }),
          _kpi('⚠️', '${s['low_stock'] ?? 0}', tr('منخفض', 'Low'), const Color(0xFFE11D48), () { setState(() => _kind = 'low'); _load(); }),
          _kpi('💰', '${s['stock_value'] ?? 0}', tr('قيمة المخزون', 'Value'), const Color(0xFF16A34A), null),
          _kpi('🔄', '${s['moves_month'] ?? 0}', tr('حركات الشهر', 'Moves'), const Color(0xFFF59E0B), () { setState(() { _kind = 'moves'; _period = 'month'; }); _load(); }),
        ]),
      );

  Widget _kpi(String ic, String v, String l, Color c, VoidCallback? onTap) => Container(
        width: 120, margin: const EdgeInsets.symmetric(horizontal: 4),
        child: Material(
          color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14), onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                Text(ic, style: const TextStyle(fontSize: 18)),
                const SizedBox(height: 4),
                FittedBox(fit: BoxFit.scaleDown, child: Text(v, style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: c))),
                Text(l, style: TextStyle(fontSize: 10.5, color: Colors.grey.shade700, fontWeight: FontWeight.w600), maxLines: 1, overflow: TextOverflow.ellipsis),
              ]),
            ),
          ),
        ),
      );

  Widget _searchBar() => Padding(
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 4),
        child: TextField(
          onChanged: (v) => setState(() => _q = v),
          onSubmitted: (_) { if (_kind == 'moves') _load(); },
          decoration: InputDecoration(
            hintText: tr('بحث بالصنف أو الباركود…', 'Search item or barcode…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            suffixIcon: _kind == 'moves' ? IconButton(icon: const Icon(Icons.arrow_forward_rounded, size: 18), onPressed: _load) : null,
            filled: true, fillColor: Colors.white, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          ),
        ),
      );

  Widget _kindBar() => SizedBox(
        height: 42,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final k in _kinds) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
            child: ChoiceChip(
              selected: _kind == k.$1,
              label: Text('${k.$2} ${tr(k.$3, k.$4)}', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _kind == k.$1 ? Colors.white : _navy)),
              selectedColor: _navy, backgroundColor: Colors.white,
              side: BorderSide(color: _kind == k.$1 ? _navy : Colors.grey.shade300),
              onSelected: (_) { setState(() => _kind = k.$1); _load(); },
            ),
          ),
        ]),
      );

  Widget _storeBar() => Padding(
        padding: const EdgeInsets.fromLTRB(10, 2, 10, 6),
        child: SearchableField(
          label: tr('المخزن', 'Store'), icon: Icons.warehouse_rounded, value: _storeId, accent: _navy,
          options: [for (final st in _stores) PickOption(value: st['id'], label: '${st['name']}', sublabel: st['facility'] == null ? null : '${st['facility']}')],
          onChanged: (v) { setState(() => _storeId = v as int?); _load(); },
        ),
      );

  Widget _movesFilters() => Column(children: [
        SizedBox(height: 40, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final t in _moveTypes) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 3),
            child: ChoiceChip(
              selected: _moveType == t.$1,
              label: Text(tr(t.$2, t.$3), style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: _moveType == t.$1 ? Colors.white : _navy)),
              selectedColor: _moveColors[t.$1] ?? _navy, backgroundColor: Colors.white,
              side: BorderSide(color: _moveType == t.$1 ? (_moveColors[t.$1] ?? _navy) : Colors.grey.shade300),
              onSelected: (_) { setState(() => _moveType = t.$1); _load(); },
            ),
          ),
        ])),
        SizedBox(height: 38, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final p in _periods) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3),
            child: ChoiceChip(
              selected: _period == p.$1,
              label: Text(tr(p.$2, p.$3), style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: _period == p.$1 ? Colors.white : _navy)),
              selectedColor: const Color(0xFF6366F1), backgroundColor: Colors.white,
              side: BorderSide(color: _period == p.$1 ? const Color(0xFF6366F1) : Colors.grey.shade300),
              onSelected: (_) { setState(() => _period = p.$1); _load(); },
            ),
          ),
        ])),
      ]);

  // ------------------------------------------------------------------ cards --
  Widget _itemCard(Map r) {
    final low = r['low_stock'] == true;
    final onHand = numOf(r['on_hand']);
    final reorder = numOf(r['min_qty'] ?? r['to_reorder']);
    // a visual fill: how healthy is the stock vs its reorder level
    final ratio = reorder > 0 ? (onHand / (reorder * 2)).clamp(0.05, 1.0) : (onHand > 0 ? 1.0 : 0.05);
    final barColor = low ? const Color(0xFFE11D48) : (onHand <= 0 ? Colors.grey : const Color(0xFF16A34A));
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      elevation: 0,
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: low ? const Color(0xFFF5C2C7) : const Color(0xFFE7EAF0))),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openItem(r),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _thumb(r, size: 62),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['product']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                const SizedBox(height: 4),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (r['store'] != null) _tag('🏬 ${r['store']}', const Color(0xFF6366F1)),
                  if (r['barcode'] != null) _tag('${r['barcode']}', const Color(0xFF64748B)),
                  if (low) _tag(tr('منخفض', 'Low'), const Color(0xFFE11D48)),
                ]),
              ])),
              const SizedBox(width: 8),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text('${r['on_hand']}',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 19,
                        color: low ? const Color(0xFFE11D48) : const Color(0xFF16A34A))),
                Text('${r['uom'] ?? ''}', style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
              ]),
            ]),
            const SizedBox(height: 9),
            // stock-health bar
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: ratio, minHeight: 5,
                color: barColor, backgroundColor: barColor.withValues(alpha: 0.12),
              ),
            ),
            const SizedBox(height: 8),
            Row(children: [
              if (low)
                Expanded(child: Text('${tr('يُعاد الطلب عند', 'Reorder at')} ${r['to_reorder'] ?? reorder}',
                    style: const TextStyle(fontSize: 10.5, color: Color(0xFFE11D48), fontWeight: FontWeight.w700)))
              else
                const Spacer(),
              // quick actions right on the card
              _miniAct(Icons.north_east_rounded, tr('صرف', 'Issue'), const Color(0xFFB45309), () => _openItem(r)),
              const SizedBox(width: 6),
              _miniAct(Icons.history_rounded, tr('الحركات', 'History'), const Color(0xFF2563EB), () => _openItem(r)),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _miniAct(IconData icon, String label, Color c, VoidCallback onTap) => InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
          decoration: BoxDecoration(
              color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 14, color: c),
            const SizedBox(width: 4),
            Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: c)),
          ]),
        ),
      );

  Widget _moveCard(Map r) {
    final t = '${r['type_raw']}';
    final c = _moveColors[t] ?? Colors.grey;
    final sign = (t == 'receipt' || t == 'return' || t == 'adjust') ? '+' : '−';
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openMove(r),
        child: Padding(
          padding: const EdgeInsets.all(11),
          child: Row(children: [
            Container(width: 40, height: 40, alignment: Alignment.center,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: Icon(_moveIcon(t), color: c, size: 20)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r['product']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy)),
              const SizedBox(height: 2),
              Text([r['type'], r['location'] ?? r['facility'], r['date']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
            ])),
            const SizedBox(width: 8),
            Text('$sign${r['quantity']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c)),
          ]),
        ),
      ),
    );
  }

  IconData _moveIcon(String t) => {
        'receipt': Icons.call_received_rounded, 'issue': Icons.call_made_rounded,
        'transfer': Icons.swap_horiz_rounded, 'adjust': Icons.tune_rounded, 'return': Icons.undo_rounded,
      }[t] ?? Icons.inventory_2_rounded;

  Widget _thumb(Map r, {double size = 46}) {
    final url = r['image'] != null ? '${context.read<AuthProvider>().api.baseUrl}${r['image']}' : null;
    return Container(
      width: size, height: size, clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: _navy.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(13)),
      child: url != null
          ? Image.network(url, fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Center(child: Text('📦', style: TextStyle(fontSize: size * 0.42))))
          : Center(child: Text('📦', style: TextStyle(fontSize: size * 0.42))),
    );
  }

  // ------------------------------------------------------------ detail sheets
  void _openItem(Map r) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.82, minChildSize: 0.5, maxChildSize: 0.95,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
            CustomPaint(painter: const BrandPattern(opacity: 0.06), child: Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(colors: [_navy, Color.lerp(_navy, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Row(children: [
                _thumb(r), const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${r['product']}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 3),
                  Text('${r['store'] ?? ''}${r['barcode'] != null ? ' · ${r['barcode']}' : ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                ])),
              ]),
            )),
            Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                _bigStat('${r['on_hand']} ${r['uom'] ?? ''}', tr('المتوفر', 'On hand'), r['low_stock'] == true ? const Color(0xFFE11D48) : const Color(0xFF16A34A)),
                _bigStat('${r['min_qty']} / ${r['max_qty']}', tr('حد أدنى/أقصى', 'Min / Max'), const Color(0xFF6366F1)),
                _bigStat('${r['stock_value'] ?? 0}', tr('القيمة', 'Value'), const Color(0xFF0891B2)),
              ]),
              const SizedBox(height: 14),
              _kv(Icons.attach_money_rounded, tr('تكلفة الوحدة', 'Unit cost'), '${r['unit_cost'] ?? 0}'),
              if (r['low_stock'] == true) _kv(Icons.shopping_cart_rounded, tr('كمية لإعادة الطلب', 'To reorder'), '${r['to_reorder']}'),
              if (r['last_move'] != null) _kv(Icons.history_rounded, tr('آخر حركة', 'Last move'), '${r['last_move']}'),
              const SizedBox(height: 12),
              Row(children: [const Icon(Icons.history_rounded, size: 17, color: _navy), const SizedBox(width: 6),
                Text(tr('آخر الحركات على الصنف', 'Recent movements'), style: const TextStyle(fontWeight: FontWeight.w900, color: _navy))]),
              const SizedBox(height: 8),
              FutureBuilder<List<dynamic>>(
                future: context.read<AuthProvider>().api.clientInvMoves(productId: r['product_id'] as int?),
                builder: (_, snap) {
                  if (!snap.hasData) return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator(color: _accent)));
                  final ms = snap.data!;
                  if (ms.isEmpty) return Padding(padding: const EdgeInsets.all(14), child: Text(tr('لا حركات', 'No movements'), style: TextStyle(color: Colors.grey.shade500)));
                  return Column(children: [for (final m in ms.take(15)) _miniMove(m as Map)]);
                },
              ),
            ])),
          ]),
        ),
      ),
    );
  }

  Widget _miniMove(Map m) {
    final t = '${m['type_raw']}';
    final c = _moveColors[t] ?? Colors.grey;
    final sign = (t == 'receipt' || t == 'return' || t == 'adjust') ? '+' : '−';
    return Container(
      margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.grey.shade200)),
      child: Row(children: [
        Icon(_moveIcon(t), size: 16, color: c), const SizedBox(width: 8),
        Expanded(child: Text([m['type'], m['location'] ?? m['facility'], m['date']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
            maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12))),
        Text('$sign${m['quantity']}', style: TextStyle(fontWeight: FontWeight.w900, color: c)),
      ]),
    );
  }

  void _openMove(Map r) {
    final t = '${r['type_raw']}';
    final c = _moveColors[t] ?? Colors.grey;
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
            decoration: BoxDecoration(gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.35)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
              Text('${r['type']} · ${r['name'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text('${r['product']}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
            ])),
          Padding(padding: const EdgeInsets.all(16), child: Column(children: [
            _kv(Icons.numbers_rounded, tr('الكمية', 'Quantity'), '${r['quantity']} ${r['uom'] ?? ''}'),
            if (r['store'] != null) _kv(Icons.warehouse_rounded, tr('المخزن', 'Store'), '${r['store']}'),
            if (r['location'] != null || r['facility'] != null) _kv(Icons.place_rounded, tr('الوجهة', 'Destination'), '${r['location'] ?? r['facility']}'),
            if (r['employee'] != null) _kv(Icons.person_rounded, tr('المنفّذ', 'By'), '${r['employee']}'),
            if (r['date'] != null) _kv(Icons.schedule_rounded, tr('التاريخ', 'Date'), '${r['date']}'),
            if (r['total_cost'] != null) _kv(Icons.attach_money_rounded, tr('التكلفة', 'Cost'), '${r['total_cost']}'),
            if (r['note'] != null) _kv(Icons.notes_rounded, tr('ملاحظة', 'Note'), '${r['note']}'),
            const SizedBox(height: 12),
          ])),
        ]),
      ),
    );
  }

  Widget _bigStat(String v, String l, Color c) => Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12), border: Border.all(color: c.withValues(alpha: 0.3))),
        child: Column(children: [
          FittedBox(fit: BoxFit.scaleDown, child: Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c))),
          const SizedBox(height: 2),
          Text(l, textAlign: TextAlign.center, style: TextStyle(fontSize: 9.5, color: Colors.grey.shade700, fontWeight: FontWeight.w600)),
        ]),
      ));

  Widget _kv(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          Icon(ic, size: 17, color: _accent), const SizedBox(width: 10),
          SizedBox(width: 120, child: Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5, fontWeight: FontWeight.w700))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy))),
        ]),
      );

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  Widget _empty() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.inventory_2_outlined, size: 56, color: Colors.grey.shade300),
        const SizedBox(height: 10),
        Text(tr('لا سجلات', 'No records'), style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
      ]));

  // --------------------------------------------------------------- issue -----
  Widget _issueButton() {
    final ready = _storeId != null;
    return FloatingActionButton.extended(
      backgroundColor: ready ? const Color(0xFFF7A23B) : Colors.grey.shade400,
      onPressed: ready ? _scanIssue : () => ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('اختر المخزن أولًا', 'Pick a store first')))),
      icon: const Icon(Icons.qr_code_scanner_rounded),
      label: Text(tr('صرف صنف', 'Issue item'), style: const TextStyle(fontWeight: FontWeight.w900)),
    );
  }

  Future<void> _scanIssue() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const _ScanPage()));
    if (code == null || code.isEmpty || !mounted) return;
    await _issueSheet(code);
  }

  /// The issue sheet, rebuilt.
  ///
  /// It used to show a bare barcode and ask for a quantity — a worker had no
  /// way to tell whether they had scanned the right thing, and an
  /// unregistered code failed only after they pressed confirm. Now the item
  /// identifies itself first: name, photo, what is on the shelf, and a plain
  /// refusal when the code is not in the system at all.
  Future<void> _issueSheet(String code) async {
    Map<String, dynamic> info;
    try {
      info = await context.read<AuthProvider>().api.invLookup(code, storeId: _storeId);
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
      return;
    }
    if (!mounted) return;
    if (info['found'] != true || info['in_store'] != true) {
      await showDialog(
        context: context,
        builder: (c) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          icon: const Icon(Icons.search_off_rounded, size: 44, color: Color(0xFFE11D48)),
          title: Text(
              info['found'] == true
                  ? tr('غير متوفّر في هذا المخزن', 'Not stocked in this store')
                  : tr('صنف غير مسجّل', 'Unregistered item'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('${info['name'] ?? code}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text('${info['message'] ?? ''}',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600)),
          ]),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(c),
                child: Text(tr('حسنًا', 'OK'))),
          ],
        ),
      );
      return;
    }

    final qtyCtrl = TextEditingController(text: '1');
    int? locId;
    String locLabel = '';
    final onHand = numOf(info['on_hand']);
    final maxIssue = numOf(info['max_issue']);

    final go = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.fromLTRB(18, 4, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          // The item, so the worker can see they scanned the right thing.
          Row(children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: '${info['image'] ?? ''}'.isNotEmpty
                  ? Image.network('${info['image']}', width: 64, height: 64, fit: BoxFit.cover,
                      errorBuilder: (c, e, st) => _imgBox())
                  : _imgBox(),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${info['name']}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: _navy)),
              const SizedBox(height: 3),
              Row(children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                      color: (info['low'] == true ? const Color(0xFFE11D48) : const Color(0xFF16A34A))
                          .withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20)),
                  child: Text(
                      '${tr('الرصيد', 'On hand')} ${onHand.toStringAsFixed(0)} ${info['uom'] ?? ''}',
                      style: TextStyle(
                          fontSize: 11.5, fontWeight: FontWeight.w800,
                          color: info['low'] == true
                              ? const Color(0xFFE11D48) : const Color(0xFF16A34A))),
                ),
                const SizedBox(width: 7),
                Text('${info['default_code'] ?? code}',
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              ]),
            ])),
          ]),
          const SizedBox(height: 16),
          // Destination: scan where you are standing, or search for it.
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () async {
                  final picked = await _pickLocation();
                  if (picked != null) setSt(() {
                    locId = picked.$1; locLabel = picked.$2;
                  });
                },
                icon: const Icon(Icons.place_outlined, size: 18),
                style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                label: Text(
                    locLabel.isEmpty ? tr('وجهة الصرف', 'Destination') : locLabel,
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          TextField(controller: qtyCtrl, keyboardType: TextInputType.number,
              decoration: InputDecoration(
                  labelText: tr('الكمية', 'Quantity'),
                  helperText: maxIssue > 0
                      ? tr('حد الصرف للمرة: ${maxIssue.toStringAsFixed(0)}',
                           'Max per issue: ${maxIssue.toStringAsFixed(0)}')
                      : null,
                  border: const OutlineInputBorder())),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
                backgroundColor: _navy, foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: () => Navigator.pop(ctx, true),
            icon: const Icon(Icons.check),
            label: Text(tr('تأكيد الصرف', 'Confirm issue'),
                style: const TextStyle(fontWeight: FontWeight.w900)),
          )),
        ]),
      )),
    );
    if (go != true || !mounted) return;
    try {
      final qty = double.tryParse(qtyCtrl.text) ?? 1.0;
      final res = await context.read<AuthProvider>().api
          .clientInvIssue(_storeId!, barcode: code, quantity: qty, locationId: locId);
      if (mounted) {
        _snack('✅ ${res['product']} → ${res['location'] ?? '—'} · '
               '${tr('المتبقّي', 'left')}: ${res['on_hand']}', const Color(0xFF16A34A));
        _boot();
      }
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Widget _imgBox() => Container(
        width: 64, height: 64,
        color: _navy.withValues(alpha: 0.07),
        child: Icon(Icons.inventory_2_outlined, color: _navy.withValues(alpha: 0.4)),
      );

  void _snack(String m, Color c) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  /// Pick a destination by scanning its QR or NFC tag, or by searching.
  /// A dropdown of two hundred locations is not a picker, it is a punishment.
  Future<(int, String)?> _pickLocation() async {
    Map<String, dynamic> d;
    try {
      d = await context.read<AuthProvider>().api.invLocations();
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
      return null;
    }
    final locs = ((d['locations'] as List?) ?? const []).cast<Map>();
    if (!mounted) return null;
    final ctrl = TextEditingController();
    return showModalBottomSheet<(int, String)?>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) {
        final q = ctrl.text.trim().toLowerCase();
        final list = q.isEmpty
            ? locs
            : locs.where((l) =>
                '${l['path'] ?? l['name']}'.toLowerCase().contains(q) ||
                '${l['code'] ?? ''}'.toLowerCase().contains(q)).toList();
        return Padding(
          padding: EdgeInsets.fromLTRB(14, 4, 14, MediaQuery.of(ctx).viewInsets.bottom + 14),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(children: [
              Expanded(child: TextField(
                controller: ctrl, autofocus: true,
                onChanged: (_) => setSt(() {}),
                decoration: InputDecoration(
                    hintText: tr('ابحث عن الموقع…', 'Search a location…'),
                    prefixIcon: const Icon(Icons.search),
                    border: const OutlineInputBorder(), isDense: true),
              )),
              const SizedBox(width: 8),
              IconButton(
                tooltip: tr('مسح QR أو NFC', 'Scan QR or NFC'),
                icon: const Icon(Icons.qr_code_scanner_rounded),
                onPressed: () async {
                  final scanned = await Navigator.push<String>(ctx,
                      MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
                  if (scanned == null) return;
                  final v = scanned.trim().toLowerCase();
                  final hit = locs.firstWhere(
                      (l) => '${l['code'] ?? ''}'.toLowerCase() == v ||
                             '${l['nfc_uid'] ?? ''}'.toLowerCase() == v,
                      orElse: () => const {});
                  if (hit.isEmpty) {
                    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
                        content: Text(tr('لا موقع بهذا الرمز', 'No location with that code'))));
                    return;
                  }
                  Navigator.pop(ctx, (intOf(hit['id']), '${hit['path'] ?? hit['name']}'));
                },
              ),
            ]),
            const SizedBox(height: 8),
            SizedBox(
              height: 320,
              child: ListView.builder(
                itemCount: list.length,
                itemBuilder: (_, i) {
                  final l = list[i];
                  return ListTile(
                    dense: true,
                    leading: const Icon(Icons.place_outlined, size: 18),
                    title: Text('${l['path'] ?? l['name']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                    subtitle: Text('${l['code'] ?? ''}',
                        style: const TextStyle(fontSize: 11)),
                    onTap: () => Navigator.pop(ctx, (intOf(l['id']), '${l['path'] ?? l['name']}')),
                  );
                },
              ),
            ),
          ]),
        );
      }),
    );
  }
}

/// Minimal full-screen barcode scanner that pops the scanned code.
class _ScanPage extends StatefulWidget {
  const _ScanPage();
  @override
  State<_ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<_ScanPage> {
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  bool _done = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('امسح باركود المنتج', 'Scan product barcode'))),
      body: MobileScanner(
        controller: _controller,
        onDetect: (cap) {
          if (_done) return;
          final code = cap.barcodes.isNotEmpty ? cap.barcodes.first.rawValue : null;
          if (code == null || code.isEmpty) return;
          _done = true;
          Navigator.pop(context, code);
        },
      ),
    );
  }
}
