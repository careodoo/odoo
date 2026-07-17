import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client internal inventory: stores, stock balances, low stock, movements +
/// a scan-to-issue flow (scan a product barcode to consume it from a store).
class ClientInventoryScreen extends StatefulWidget {
  const ClientInventoryScreen({super.key});
  @override
  State<ClientInventoryScreen> createState() => _ClientInventoryScreenState();
}

class _ClientInventoryScreenState extends State<ClientInventoryScreen> {
  Map<String, dynamic>? _summary;
  List<dynamic> _stores = [];
  List<dynamic> _locations = [];
  int? _storeId;
  String _kind = 'items';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ['items', '📦 الأرصدة', 'Stock'],
    ['low', '⚠️ منخفض', 'Low'],
    ['moves', '🔄 الحركات', 'Moves'],
  ];

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
      if (mounted) setState(() { _summary = s; _stores = st; _locations = locs; _storeId = st.isNotEmpty ? st.first['id'] as int : null; });
    } catch (_) {}
    _load();
  }

  void _load() => setState(() {
        final api = context.read<AuthProvider>().api;
        _list = _kind == 'moves'
            ? api.clientInvMoves()
            : api.clientInvItems(storeId: _storeId, low: _kind == 'low');
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      appBar: AppBar(title: Text(tr('المخزون الداخلي', 'Inventory')), actions: [
        IconButton(icon: const Icon(Icons.insights_rounded), tooltip: tr('تحليلات الاستهلاك', 'Consumption'), onPressed: _showConsumption),
      ]),
      // The issue action used to be a navy FAB on a navy app bar — it read as
      // part of the chrome. Amber separates it from the CARE navy and says
      // "this is the thing you came here to do".
      floatingActionButton: _issueButton(),
      body: Column(children: [
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('🏬', '${s['stores'] ?? 0}', tr('المخازن', 'Stores'), const Color(0xFF6366F1)),
              _stat('📦', '${s['items'] ?? 0}', tr('الأصناف', 'Items'), const Color(0xFF0891B2)),
              _stat('⚠️', '${s['low_stock'] ?? 0}', tr('منخفض', 'Low'), const Color(0xFFE11D48)),
              _stat('💰', '${s['stock_value'] ?? 0}', tr('قيمة المخزون', 'Value'), const Color(0xFF16A34A)),
              _stat('🔄', '${s['moves_month'] ?? 0}', tr('حركات الشهر', 'Moves'), const Color(0xFFF59E0B)),
            ]),
          ),
        if (_stores.length > 1)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: DropdownButtonFormField<int>(
              value: _storeId,
              decoration: InputDecoration(labelText: tr('المخزن', 'Store'), isDense: true, border: const OutlineInputBorder()),
              items: [for (final st in _stores) DropdownMenuItem(value: st['id'] as int, child: Text('${st['name']}'))],
              onChanged: (v) { setState(() => _storeId = v); _load(); },
            ),
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
                  onSelected: (_) { setState(() => _kind = k[0]); _load(); },
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
              return RefreshIndicator(
                onRefresh: () async { _load(); await _list; },
                child: ListView.separated(
                  padding: const EdgeInsets.all(8),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) => _kind == 'moves' ? _moveRow(rows[i] as Map) : _itemRow(rows[i] as Map),
                ),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _issueButton() {
    final ready = _storeId != null;
    return Container(
      decoration: ready
          ? BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.45),
                  blurRadius: 14, offset: const Offset(0, 5))],
            )
          : null,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          // Without a store picked there is nothing to issue from; say that
          // rather than present a dead button.
          onTap: ready
              ? _scanIssue
              : () => ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text(tr('اختر المخزن أولًا', 'Pick a store first')))),
          child: Ink(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: ready
                    ? const [Color(0xFFF7A23B), Color(0xFFD97706)]
                    : [Colors.grey.shade400, Colors.grey.shade500],
                begin: Alignment.topRight, end: Alignment.bottomLeft,
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.22),
                      borderRadius: BorderRadius.circular(9)),
                  child: const Icon(Icons.qr_code_scanner_rounded, color: Colors.white, size: 17),
                ),
                const SizedBox(width: 9),
                Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Text(tr('صرف صنف', 'Issue item'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5)),
                  Text(tr('امسح باركود الصنف', 'Scan the item barcode'),
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.85),
                          fontWeight: FontWeight.w600, fontSize: 8.5)),
                ]),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 128,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );

  Widget _itemRow(Map r) {
    final low = r['low_stock'] == true;
    return ListTile(
      leading: (r['image'] != null)
          ? CircleAvatar(backgroundImage: NetworkImage('${context.read<AuthProvider>().api.baseUrl}${r['image']}'))
          : const CircleAvatar(child: Text('📦')),
      title: Text('${r['product']}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text([r['store'], r['barcode']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
          maxLines: 1, overflow: TextOverflow.ellipsis),
      trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
        Text('${r['on_hand']} ${r['uom'] ?? ''}', style: TextStyle(fontWeight: FontWeight.w800, color: low ? const Color(0xFFE11D48) : null)),
        if (low) Text('${tr('اطلب', 'reorder')} ${r['to_reorder']}', style: const TextStyle(fontSize: 10, color: Color(0xFFE11D48))),
      ]),
    );
  }

  Widget _moveRow(Map r) {
    final t = '${r['type_raw']}';
    const c = {'receipt': Color(0xFF16A34A), 'issue': Color(0xFFE11D48), 'transfer': Color(0xFF6366F1), 'adjust': Color(0xFFF59E0B), 'return': Color(0xFF0891B2)};
    final sign = t == 'receipt' || t == 'return' || t == 'adjust' ? '+' : '−';
    return ListTile(
      dense: true,
      title: Text('${r['type']} · ${r['product']}', style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text([r['store'], r['location'] ?? r['facility'], r['employee'], r['date']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
          maxLines: 1, overflow: TextOverflow.ellipsis),
      trailing: Text('$sign${r['quantity']}', style: TextStyle(fontWeight: FontWeight.w800, color: c[t] ?? Colors.grey)),
    );
  }

  Future<void> _scanIssue() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const _ScanPage()));
    if (code == null || code.isEmpty || !mounted) return;
    final qtyCtrl = TextEditingController(text: '1');
    int? locId;
    final go = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.fromLTRB(18, 4, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('صرف من المخزون', 'Issue from stock'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
          const SizedBox(height: 4),
          Text('${tr('الباركود', 'Barcode')}: $code', style: const TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 14),
          DropdownButtonFormField<int>(
            initialValue: locId,
            isExpanded: true,
            decoration: InputDecoration(labelText: tr('وجهة الصرف (مبنى › دور › مكتب)', 'Destination (building › floor › office)'), border: const OutlineInputBorder(), prefixIcon: const Icon(Icons.place_outlined)),
            items: [for (final l in _locations) DropdownMenuItem(value: l['id'] as int, child: Text('${l['path'] ?? l['name']}', overflow: TextOverflow.ellipsis))],
            onChanged: (v) => setSt(() => locId = v),
          ),
          const SizedBox(height: 12),
          TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: tr('الكمية', 'Quantity'), border: const OutlineInputBorder())),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true), icon: const Icon(Icons.check), label: Text(tr('تأكيد الصرف', 'Confirm issue')),
          )),
        ]),
      )),
    );
    if (go != true || !mounted) return;
    try {
      final qty = double.tryParse(qtyCtrl.text) ?? 1.0;
      final res = await context.read<AuthProvider>().api.clientInvIssue(_storeId!, barcode: code, quantity: qty, locationId: locId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ ${res['product']} → ${res['location'] ?? '—'} · ${tr('المتبقّي', 'left')}: ${res['on_hand']}'),
          backgroundColor: const Color(0xFF16A34A),
        ));
        _boot();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
    }
  }

  Future<void> _showConsumption() async {
    Map<String, dynamic>? data;
    String period = 'month';
    await showModalBottomSheet(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) {
        Future<void> load() async {
          try { final d = await context.read<AuthProvider>().api.clientInvConsumption(period: period); setSt(() => data = d); } catch (_) {}
        }
        if (data == null) load();
        Widget topList(String title, String emoji, List rows) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(padding: const EdgeInsets.only(top: 14, bottom: 6), child: Text('$emoji $title', style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F)))),
          if (rows.isEmpty) const Text('—', style: TextStyle(color: Colors.grey)),
          for (int i = 0; i < rows.length && i < 6; i++)
            Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(children: [
              Container(width: 22, height: 22, alignment: Alignment.center, decoration: BoxDecoration(color: const Color(0xFF0E3A5F).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)), child: Text('${i + 1}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF0E3A5F)))),
              const SizedBox(width: 8),
              Expanded(child: Text('${rows[i]['label']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13))),
              Text('${rows[i]['qty']}', style: const TextStyle(fontWeight: FontWeight.w800, color: Color(0xFFC0392B))),
            ])),
        ]);
        return DraggableScrollableSheet(expand: false, initialChildSize: 0.8, maxChildSize: 0.95, builder: (_, ctrl) => ListView(controller: ctrl, padding: const EdgeInsets.fromLTRB(18, 0, 18, 20), children: [
          Text(tr('تحليلات الاستهلاك', 'Consumption analytics'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
          const SizedBox(height: 10),
          Wrap(spacing: 8, children: [
            for (final p in const [['day', 'اليوم', 'Day'], ['month', 'الشهر', 'Month'], ['year', 'السنة', 'Year'], ['all', 'الكل', 'All']])
              ChoiceChip(label: Text(gLang == 'en' ? p[2] : p[1]), selected: period == p[0], onSelected: (_) { period = p[0]; data = null; setSt(() {}); }),
          ]),
          if (data == null) const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
          else ...[
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: _cstat('${data!['total_qty'] ?? 0}', tr('إجمالي المصروف', 'Total issued'), const Color(0xFF0891B2))),
              const SizedBox(width: 8),
              Expanded(child: _cstat('${data!['total_value'] ?? 0}', tr('القيمة', 'Value'), const Color(0xFF16A34A))),
              const SizedBox(width: 8),
              Expanded(child: _cstat('${data!['issues'] ?? 0}', tr('عمليات', 'Issues'), const Color(0xFFF59E0B))),
            ]),
            topList(tr('أكثر المواد استهلاكًا', 'Top materials'), '📦', (data!['top_materials'] as List?) ?? []),
            topList(tr('أكثر المواقع استهلاكًا', 'Top locations'), '📍', (data!['top_locations'] as List?) ?? []),
            topList(tr('أكثر المباني', 'Top buildings'), '🏢', (data!['top_buildings'] as List?) ?? []),
            topList(tr('أكثر الموظفين صرفًا', 'Top employees'), '👷', (data!['top_employees'] as List?) ?? []),
          ],
        ]));
      }),
    );
  }

  Widget _cstat(String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)),
          Text(l, style: const TextStyle(fontSize: 10, color: Colors.grey), textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );
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
