import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client waste transfer & treatment: collection orders + trips, with a
/// new-order form. Scoped to the client's waste projects.
class ClientWasteScreen extends StatefulWidget {
  const ClientWasteScreen({super.key});
  @override
  State<ClientWasteScreen> createState() => _ClientWasteScreenState();
}

class _ClientWasteScreenState extends State<ClientWasteScreen> {
  Map<String, dynamic>? _summary;
  String _kind = 'orders';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ['orders', '♻️ الأوامر', 'Orders'],
    ['trips', '🚛 الرحلات', 'Trips'],
    ['centers', '🏭 المراكز', 'Centers'],
  ];
  static const _stL = {
    'draft': 'مسودة', 'scheduled': 'مجدول', 'pickuped': 'تم الالتقاط', 'arrived': 'وصل',
    'processing': 'قيد المعالجة', 'delivered': 'تم التسليم', 'completed': 'مكتمل', 'cancelled': 'ملغى',
  };
  static const _stC = {
    'draft': Color(0xFF94A3B8), 'scheduled': Color(0xFF3B82F6), 'pickuped': Color(0xFF0891B2),
    'arrived': Color(0xFF6366F1), 'processing': Color(0xFFF59E0B), 'delivered': Color(0xFF16A34A),
    'completed': Color(0xFF16A34A), 'cancelled': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _load();
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientWasteSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _load() => setState(() => _list = context.read<AuthProvider>().api.clientWaste(_kind));

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      appBar: AppBar(title: Text(tr('نقل ومعالجة النفايات', 'Waste'))),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF16A34A),
        onPressed: _newOrder,
        icon: const Icon(Icons.add),
        label: Text(tr('طلب نقل', 'New order')),
      ),
      body: Column(children: [
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('♻️', '${s['orders'] ?? 0}', tr('الأوامر', 'Orders'), const Color(0xFF16A34A)),
              _stat('⏳', '${s['open'] ?? 0}', tr('قيد التنفيذ', 'In progress'), const Color(0xFFF59E0B)),
              _stat('✅', '${s['completed'] ?? 0}', tr('مكتملة', 'Completed'), const Color(0xFF0891B2)),
              _stat('🚛', '${s['trips'] ?? 0}', tr('الرحلات', 'Trips'), const Color(0xFF6366F1)),
              _stat('🏭', '${s['centers'] ?? 0}', tr('المراكز', 'Centers'), const Color(0xFF334155)),
            ]),
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
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
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

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  Widget _row(Map r) {
    if (_kind == 'centers') {
      return ListTile(leading: const Text('🏭', style: TextStyle(fontSize: 22)), title: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700)));
    }
    final st = '${r['state']}';
    final c = _stC[st] ?? Colors.blueGrey;
    if (_kind == 'trips') {
      return ListTile(
        leading: const Text('🚛', style: TextStyle(fontSize: 22)),
        title: Text('${r['sequence']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${r['pickup'] ?? ''} → ${r['center'] ?? ''} · ${r['total_weight'] ?? 0}kg', maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill(tr(_stL[st] ?? st, st), c),
        onTap: () => _openTrip(r),
      );
    }
    final items = (r['items'] as List?) ?? [];
    return ListTile(
      title: Text('${r['serial']}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text([r['pickup'], items.map((i) => '${i['item'] ?? ''}×${i['qty']}').join('، ')].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
          maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: _pill(tr(_stL[st] ?? st, st), c),
      onTap: () => _openOrder(r),
    );
  }

  static const _flow = ['draft', 'scheduled', 'pickuped', 'arrived', 'processing', 'delivered', 'completed'];

  void _openOrder(Map r) {
    final st = '${r['state']}';
    final cur = _flow.indexOf(st);
    final cancelled = st == 'cancelled';
    final items = (r['items'] as List?) ?? [];
    showModalBottomSheet(
      context: context, isScrollControlled: true, showDragHandle: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.85, maxChildSize: 0.95,
        builder: (_, ctrl) => ListView(controller: ctrl, padding: const EdgeInsets.all(18), children: [
          Text('♻️ ${r['serial']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
          if (r['project'] != null) Text('${r['project']}', style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 14),
          _secTitle(tr('حالة الطلب', 'Order status')),
          if (cancelled)
            const Text('✖ تم إلغاء الطلب', style: TextStyle(color: Color(0xFFE11D48), fontWeight: FontWeight.w700))
          else
            Column(children: [for (int i = 0; i < _flow.length; i++) _step(i, cur)]),
          _secTitle(tr('فريق العملية', 'Operation team')),
          _kv(Icons.manage_accounts, tr('مدير العمليات', 'Ops manager'), r['ops_manager']),
          _kv(Icons.local_shipping_outlined, tr('السائق', 'Driver'), r['driver']),
          _kv(Icons.how_to_reg_outlined, tr('مستلم الكميات', 'Receiver'), r['receiver']),
          if ((r['final_weight'] ?? 0) != 0) _kv(Icons.scale_outlined, tr('الوزن النهائي', 'Final weight'), '${r['final_weight']} كجم'),
          if (r['final_note'] != null) _kv(Icons.sticky_note_2_outlined, tr('ملاحظة الاستلام', 'Receipt note'), r['final_note']),
          _secTitle(tr('التفاصيل', 'Details')),
          _kv(Icons.place_outlined, tr('موقع الالتقاط', 'Pickup'), r['pickup']),
          _kv(Icons.route_outlined, tr('الرحلة', 'Trip'), r['trip']),
          _kv(Icons.event_outlined, tr('التاريخ', 'Date'), r['order_date']),
          if (items.isNotEmpty) ...[
            _secTitle(tr('الأصناف', 'Items')),
            for (final i in items) Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(children: [Expanded(child: Text('${i['item'] ?? '—'}')), Text('×${i['qty']}', style: const TextStyle(fontWeight: FontWeight.w700))])),
          ],
          if (r['proof'] != null) ...[
            _secTitle(tr('صورة الإثبات', 'Proof photo')),
            ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.network('${r['proof']}', errorBuilder: (_, __, ___) => const SizedBox())),
          ],
          if (r['notes'] != null) ...[_secTitle(tr('ملاحظات', 'Notes')), Text('${r['notes']}')],
          const SizedBox(height: 20),
        ]),
      ),
    );
  }

  void _openTrip(Map r) {
    final items = (r['items'] as List?) ?? [];
    showModalBottomSheet(
      context: context, isScrollControlled: true, showDragHandle: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('🚛 ${r['sequence']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _tstat('⚖️', '${r['total_weight'] ?? 0}', tr('الوزن الكلي', 'Weight'), const Color(0xFF0891B2))),
            const SizedBox(width: 8),
            Expanded(child: _tstat('📦', '${r['total_quantity'] ?? 0}', tr('الكمية', 'Qty'), const Color(0xFF6366F1))),
            const SizedBox(width: 8),
            Expanded(child: _tstat('📋', '${r['order_count'] ?? 0}', tr('الأوامر', 'Orders'), const Color(0xFF16A34A))),
          ]),
          const SizedBox(height: 8),
          _kv(Icons.place_outlined, tr('الالتقاط', 'Pickup'), r['pickup']),
          _kv(Icons.factory_outlined, tr('مركز المعالجة', 'Center'), r['center']),
          _kv(Icons.groups_outlined, tr('الفريق', 'Team'), r['team']),
          _kv(Icons.event_outlined, tr('التاريخ', 'Date'), r['date']),
          if (items.isNotEmpty) ...[
            _secTitle(tr('الأصناف المنقولة', 'Transported items')),
            for (final i in items) Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(children: [Expanded(child: Text('${i['item'] ?? '—'}')), Text('×${i['qty']} · ${i['weight']}kg', style: const TextStyle(fontWeight: FontWeight.w700))])),
          ],
        ]),
      ),
    );
  }

  Widget _step(int i, int cur) {
    final done = cur >= i && cur >= 0;
    final s = _flow[i];
    final color = done ? const Color(0xFF16A34A) : Colors.grey.shade300;
    return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Column(children: [
        Container(width: 28, height: 28, decoration: BoxDecoration(color: done ? color : Colors.white, shape: BoxShape.circle, border: Border.all(color: color, width: 2)), child: Icon(done ? Icons.check : Icons.circle_outlined, size: 15, color: done ? Colors.white : Colors.grey)),
        if (i < _flow.length - 1) Expanded(child: Container(width: 2, color: cur > i ? const Color(0xFF16A34A) : Colors.grey.shade300)),
      ]),
      const SizedBox(width: 12),
      Padding(padding: const EdgeInsets.only(top: 3, bottom: 14), child: Text(tr(_stL[s] ?? s, s), style: TextStyle(fontWeight: cur == i ? FontWeight.w900 : FontWeight.w600, color: done ? const Color(0xFF0E3A5F) : Colors.grey))),
    ]));
  }

  Widget _secTitle(String t) => Padding(padding: const EdgeInsets.only(top: 16, bottom: 8), child: Row(children: [Container(width: 4, height: 16, decoration: BoxDecoration(color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(3))), const SizedBox(width: 8), Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Color(0xFF0E3A5F)))]));

  Widget _kv(IconData ic, String k, dynamic v) => (v == null || '$v'.isEmpty) ? const SizedBox.shrink() : Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [Icon(ic, size: 17, color: Colors.grey), const SizedBox(width: 8), SizedBox(width: 110, child: Text(k, style: const TextStyle(color: Colors.grey, fontSize: 12.5))), Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)))]),
      );

  Widget _tstat(String ic, String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12), decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
        child: Column(children: [Text('$ic $v', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c)), Text(l, style: const TextStyle(fontSize: 10, color: Colors.grey))]),
      );

  Future<void> _newOrder() async {
    Map<String, dynamic> opt;
    try {
      opt = await context.read<AuthProvider>().api.clientWasteOptions();
    } catch (_) { return; }
    final projects = (opt['projects'] as List?) ?? [];
    if (projects.isEmpty) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('لا يوجد مشروع نفايات مرتبط', 'No waste project linked'))));
      return;
    }
    final pickups = (opt['pickups'] as List?) ?? [];
    final items = (opt['items'] as List?) ?? [];
    int projId = projects.first['id'] as int;
    int? pickId, itemId;
    final qtyCtrl = TextEditingController(text: '1');
    if (!mounted) return;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => Padding(
          padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('طلب نقل جديد', 'New collection order'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            DropdownButtonFormField<int>(
              initialValue: projId,
              decoration: InputDecoration(labelText: tr('المشروع', 'Project'), border: const OutlineInputBorder()),
              items: [for (final p in projects) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))],
              onChanged: (v) => setSt(() => projId = v ?? projId),
            ),
            const SizedBox(height: 10),
            if (pickups.isNotEmpty)
              DropdownButtonFormField<int>(
                initialValue: pickId,
                decoration: InputDecoration(labelText: tr('موقع الالتقاط', 'Pickup location'), border: const OutlineInputBorder()),
                items: [for (final p in pickups) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))],
                onChanged: (v) => setSt(() => pickId = v),
              ),
            const SizedBox(height: 10),
            if (items.isNotEmpty)
              DropdownButtonFormField<int>(
                initialValue: itemId,
                decoration: InputDecoration(labelText: tr('الصنف', 'Item'), border: const OutlineInputBorder()),
                items: [for (final it in items) DropdownMenuItem(value: it['id'] as int, child: Text('${it['name']}'))],
                onChanged: (v) => setSt(() => itemId = v),
              ),
            const SizedBox(height: 10),
            TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: tr('الكمية', 'Quantity'), border: const OutlineInputBorder())),
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, child: ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال الطلب', 'Submit')))),
          ]),
        ),
      ),
    );
    if (ok != true || !mounted) return;
    try {
      final res = await context.read<AuthProvider>().api.clientWasteCreate(projId, pickupId: pickId, itemId: itemId, qty: double.tryParse(qtyCtrl.text) ?? 1.0);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ ${res['serial']}')));
        _load();
        _loadSummary();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
