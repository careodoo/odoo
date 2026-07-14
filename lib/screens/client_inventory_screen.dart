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
      if (mounted) setState(() { _summary = s; _stores = st; _storeId = st.isNotEmpty ? st.first['id'] as int : null; });
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
      appBar: AppBar(title: Text(tr('المخزون الداخلي', 'Inventory'))),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF0E3A5F),
        onPressed: _storeId == null ? null : _scanIssue,
        icon: const Icon(Icons.qr_code_scanner),
        label: Text(tr('صرف بالمسح', 'Scan-issue')),
      ),
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
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('صرف من المخزون', 'Issue from stock')),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${tr('الباركود', 'Barcode')}: $code', style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: tr('الكمية', 'Quantity'), border: const OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('صرف', 'Issue'))),
        ],
      ),
    );
    if (go != true || !mounted) return;
    try {
      final qty = double.tryParse(qtyCtrl.text) ?? 1.0;
      final res = await context.read<AuthProvider>().api.clientInvScanIssue(_storeId!, code, quantity: qty);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ ${res['product']} · ${tr('المتبقّي', 'remaining')}: ${res['on_hand']}${res['low_stock'] == true ? ' ⚠️' : ''}'),
        ));
        _boot();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
    }
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
