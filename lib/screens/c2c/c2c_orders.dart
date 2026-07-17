import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// Customer "My Orders" (طلباتي) — store product orders with live status
/// tracking, full detail and a cancel request.
class C2COrdersScreen extends StatefulWidget {
  const C2COrdersScreen({super.key});
  @override
  State<C2COrdersScreen> createState() => _C2COrdersScreenState();
}

class _C2COrdersScreenState extends State<C2COrdersScreen> {
  late Future<List<dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.c2cShopOrders());

  static const _stateColor = {
    'draft': Color(0xFFF59E0B), 'confirmed': Color(0xFF2563EB),
    'shipped': Color(0xFF7C3AED), 'delivered': Color(0xFF16A34A), 'cancelled': Color(0xFFB91C1C),
  };
  static const _stateIcon = {
    'draft': Icons.hourglass_top_rounded, 'confirmed': Icons.check_circle_outline_rounded,
    'shipped': Icons.local_shipping_rounded, 'delivered': Icons.done_all_rounded, 'cancelled': Icons.cancel_outlined,
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(backgroundColor: C2C.red, foregroundColor: Colors.white, elevation: 0, title: Text(tr('طلباتي', 'My orders'))),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final list = snap.data!;
            if (list.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 120),
                Center(child: Column(children: [
                  Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(26)), child: const Icon(Icons.receipt_long_rounded, size: 46, color: C2C.navy)),
                  const SizedBox(height: 14),
                  Text(tr('لا توجد طلبات بعد', 'No orders yet'), style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.navy, fontSize: 15)),
                ])),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _card(list[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map o) {
    final state = '${o['state']}';
    final col = _stateColor[state] ?? C2C.slate;
    final reqCancel = o['cancel_requested'] == true;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(o['id'] as int),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)), child: Icon(_stateIcon[state] ?? Icons.receipt_long_rounded, color: col, size: 20)),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${o['name']}', style: const TextStyle(fontWeight: FontWeight.w900, color: C2C.ink, fontSize: 14)),
                Text('${o['date'] ?? ''}'.split(' ').first, style: const TextStyle(color: C2C.slate, fontSize: 11.5)),
              ])),
              Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)), child: Text(reqCancel ? tr('طلب إلغاء', 'Cancel req.') : '${o['state_label']}', style: TextStyle(color: reqCancel ? const Color(0xFFB91C1C) : col, fontWeight: FontWeight.w800, fontSize: 11))),
            ]),
            const Divider(height: 20),
            Row(children: [
              Icon(Icons.inventory_2_outlined, size: 15, color: C2C.slate),
              const SizedBox(width: 5),
              Text(tr('${o['item_count']} صنف', '${o['item_count']} items'), style: const TextStyle(color: C2C.slate, fontSize: 12.5)),
              const Spacer(),
              Text('${(o['amount_total'] as num).toStringAsFixed(2)} KWD', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 15)),
            ]),
            if (state != 'cancelled') Padding(padding: const EdgeInsets.only(top: 12), child: _miniTrack(o['progress'] is int ? o['progress'] as int : 0)),
          ]),
        ),
      ),
    );
  }

  // compact 3-dot tracker for the list card (confirmed → shipped → delivered)
  Widget _miniTrack(int progress) {
    Widget dot(bool on) => Container(width: 9, height: 9, decoration: BoxDecoration(shape: BoxShape.circle, color: on ? C2C.navy : Colors.black12));
    Widget bar(bool on) => Expanded(child: Container(height: 3, color: on ? C2C.navy : Colors.black12));
    // progress: 0 draft,1 confirmed,2 shipped,3 delivered
    return Row(children: [dot(progress >= 1), bar(progress >= 2), dot(progress >= 2), bar(progress >= 3), dot(progress >= 3)]);
  }

  Future<void> _openDetail(int id) async {
    Map? d;
    try {
      d = await context.read<AuthProvider>().api.c2cShopOrder(id);
    } catch (_) {}
    if (!mounted || d == null) return;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _OrderDetailSheet(order: d!, onChanged: _reload),
    );
  }
}

class _OrderDetailSheet extends StatefulWidget {
  const _OrderDetailSheet({required this.order, required this.onChanged});
  final Map order;
  final VoidCallback onChanged;
  @override
  State<_OrderDetailSheet> createState() => _OrderDetailSheetState();
}

class _OrderDetailSheetState extends State<_OrderDetailSheet> {
  late Map o;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    o = widget.order;
  }

  @override
  Widget build(BuildContext context) {
    final steps = (o['steps'] as List?) ?? [];
    final cancelled = o['state'] == 'cancelled';
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.82, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => ListView(controller: sc, padding: EdgeInsets.zero, children: [
        // hero
        Container(
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
          decoration: const BoxDecoration(gradient: LinearGradient(colors: [C2C.navy2, C2C.navy], begin: Alignment.topRight, end: Alignment.bottomLeft), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 14),
            Row(children: [
              const Icon(Icons.receipt_long_rounded, color: Colors.white70, size: 20),
              const SizedBox(width: 8),
              Text('${o['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
              const Spacer(),
              Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)), child: Text('${o['state_label']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12))),
            ]),
            const SizedBox(height: 6),
            Text('${o['date'] ?? ''}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
          ]),
        ),
        if (o['cancel_requested'] == true)
          Container(margin: const EdgeInsets.fromLTRB(16, 14, 16, 0), padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: const Color(0xFFFEF2F2), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFFECACA))), child: Row(children: [const Icon(Icons.info_outline_rounded, color: Color(0xFFB91C1C), size: 20), const SizedBox(width: 8), Expanded(child: Text(tr('طلب الإلغاء قيد المراجعة من قِبل الفريق', 'Your cancellation request is under review'), style: const TextStyle(color: Color(0xFFB91C1C), fontSize: 12.5, fontWeight: FontWeight.w600)))])),
        // timeline
        if (!cancelled) Padding(padding: const EdgeInsets.fromLTRB(20, 18, 20, 4), child: Text(tr('حالة الطلب', 'Order status'), style: const TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 14))),
        if (!cancelled) Padding(padding: const EdgeInsets.fromLTRB(16, 8, 16, 0), child: Column(children: [for (int i = 0; i < steps.length; i++) _step(steps[i] as Map, i == steps.length - 1)])),
        if (cancelled) Container(margin: const EdgeInsets.all(16), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: const Color(0xFFFEF2F2), borderRadius: BorderRadius.circular(12)), child: Row(children: [const Icon(Icons.cancel_rounded, color: Color(0xFFB91C1C)), const SizedBox(width: 10), Expanded(child: Text(tr('تم إلغاء هذا الطلب', 'This order was cancelled'), style: const TextStyle(color: Color(0xFFB91C1C), fontWeight: FontWeight.w700)))])),
        // items
        _sectionTitle(tr('الأصناف', 'Items')),
        ...((o['lines'] as List?) ?? []).map((l) => _lineRow(l as Map)),
        // delivery + payment
        _sectionTitle(tr('التوصيل والدفع', 'Delivery & payment')),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: Column(children: [
          if (o['address'] != null) _kv(Icons.location_on_outlined, tr('العنوان', 'Address'), '${o['address']}'),
          if (o['phone'] != null) _kv(Icons.phone_outlined, tr('الهاتف', 'Phone'), '${o['phone']}'),
          _kv(Icons.payments_outlined, tr('الدفع', 'Payment'), '${o['payment_method_label']} · ${o['payment_label']}'),
        ])),
        // total
        Container(margin: const EdgeInsets.fromLTRB(16, 12, 16, 4), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(14)), child: Row(children: [Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: C2C.ink)), const Spacer(), Text('${(o['amount_total'] as num).toStringAsFixed(2)} ${o['currency'] ?? 'KWD'}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 19))])),
        // cancel
        if (o['cancellable'] == true) Padding(padding: const EdgeInsets.fromLTRB(16, 8, 16, 20), child: SizedBox(width: double.infinity, height: 48, child: OutlinedButton.icon(
          style: OutlinedButton.styleFrom(foregroundColor: C2C.red, side: const BorderSide(color: C2C.red), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
          onPressed: _busy ? null : _cancel,
          icon: const Icon(Icons.cancel_outlined),
          label: Text(tr('طلب إلغاء الطلب', 'Request cancellation'), style: const TextStyle(fontWeight: FontWeight.w800)),
        ))),
        const SizedBox(height: 12),
      ]),
    );
  }

  Widget _step(Map s, bool last) {
    final done = s['done'] == true;
    return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Column(children: [
        Container(width: 26, height: 26, decoration: BoxDecoration(shape: BoxShape.circle, color: done ? C2C.navy : Colors.white, border: Border.all(color: done ? C2C.navy : Colors.black26, width: 2)), child: done ? const Icon(Icons.check_rounded, size: 15, color: Colors.white) : null),
        if (!last) Expanded(child: Container(width: 2.5, color: done ? C2C.navy : Colors.black12)),
      ]),
      const SizedBox(width: 12),
      Padding(padding: const EdgeInsets.only(bottom: 18, top: 2), child: Text('${s['label']}', style: TextStyle(fontWeight: done ? FontWeight.w800 : FontWeight.w600, color: done ? C2C.ink : C2C.slate, fontSize: 13.5))),
    ]));
  }

  Widget _sectionTitle(String t) => Padding(padding: const EdgeInsets.fromLTRB(20, 18, 20, 6), child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 14)));

  Widget _lineRow(Map l) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
        child: Row(children: [
          ClipRRect(borderRadius: BorderRadius.circular(10), child: l['image'] != null
              ? Image.network('${l['image']}', width: 46, height: 46, fit: BoxFit.cover, errorBuilder: (_, __, ___) => _ph())
              : _ph()),
          const SizedBox(width: 10),
          Expanded(child: Text('${l['product']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
          const SizedBox(width: 8),
          Text('×${(l['qty'] as num).toStringAsFixed(0)}', style: const TextStyle(color: C2C.slate, fontWeight: FontWeight.w700)),
          SizedBox(width: 66, child: Text('${(l['subtotal'] as num).toStringAsFixed(2)}', textAlign: TextAlign.end, style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800))),
        ]),
      );

  Widget _ph() => Container(width: 46, height: 46, color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 20));

  Widget _kv(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 18, color: C2C.slate),
          const SizedBox(width: 8),
          SizedBox(width: 70, child: Text(k, style: const TextStyle(color: C2C.slate, fontSize: 12.5))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12.5, color: C2C.ink))),
        ]),
      );

  Future<void> _cancel() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('طلب إلغاء الطلب', 'Request cancellation'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(tr('سيتم إرسال طلب الإلغاء لفريق كير للمراجعة.', 'Your request will be sent to the CARE team for review.'), style: const TextStyle(fontSize: 13, color: C2C.slate)),
        const SizedBox(height: 12),
        TextField(controller: reason, maxLines: 2, decoration: InputDecoration(hintText: tr('سبب الإلغاء (اختياري)', 'Reason (optional)'), filled: true, fillColor: C2C.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none))),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('تراجع', 'Back'))),
        ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white), onPressed: () => Navigator.pop(context, true), child: Text(tr('إرسال', 'Submit'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.c2cShopOrderCancel(o['id'] as int, reason: reason.text.trim());
      if (!mounted) return;
      setState(() => o = res);
      widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم إرسال طلب الإلغاء', 'Cancellation request sent')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
