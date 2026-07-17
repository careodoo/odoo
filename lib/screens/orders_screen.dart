import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client sales orders — list + detail (tracking, invoices, cancel).
class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});
  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<List<dynamic>> _future;

  static const _sc = {
    'draft': Color(0xFF64748B), 'sent': Color(0xFF3B82F6), 'sale': Color(0xFF16A34A),
    'done': Color(0xFF0891B2), 'cancel': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientOrders();

  Future<void> _openOrder(int id) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => FutureBuilder<Map<String, dynamic>>(
        future: context.read<AuthProvider>().api.clientOrder(id),
        builder: (ctx, snap) {
          if (!snap.hasData) {
            return const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()));
          }
          final o = snap.data!;
          final steps = (o['tracking']?['steps'] as List?) ?? [];
          final invs = (o['invoices'] as List?) ?? [];
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.7,
            builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
              Text('${o['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              Text('${o['state_label'] ?? o['state']} · ${o['amount_total']} ${o['currency'] ?? ''}',
                  style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 14),
              _track(steps, (o['tracking']?['pickings'] as List?) ?? const []),
              if (o['delivery_address'] != null || o['delivery_date'] != null) ...[
                const SizedBox(height: 12),
                _deliveryBox(o),
              ],
              const Divider(height: 24),
              Text(tr('الأصناف', 'Items'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
              const SizedBox(height: 6),
              ...((o['lines'] as List?) ?? []).map((l) => _lineRow(l as Map)),
              const Divider(),
              _kv(tr('قبل الضريبة', 'Untaxed'), '${o['amount_untaxed']}'),
              _kv(tr('الضريبة', 'Tax'), '${o['amount_tax']}'),
              _kv(tr('الإجمالي', 'Total'), '${o['amount_total']} ${o['currency'] ?? ''}', bold: true),
              if (invs.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(tr('الفواتير', 'Invoices'), style: const TextStyle(fontWeight: FontWeight.w800)),
                ...invs.map((m) => ListTile(
                      dense: true,
                      title: Text('${m['name']}'),
                      subtitle: Text('${tr('المتبقّي', 'Residual')}: ${m['amount_residual']} ${m['currency'] ?? ''}'),
                    )),
              ],
              if (o['can_cancel'] == true)
                Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE11D48)),
                    icon: const Icon(Icons.close),
                    label: Text(tr('إلغاء الطلب', 'Cancel order')),
                    onPressed: () async {
                      try {
                        await context.read<AuthProvider>().api.orderCancel(id);
                        if (!mounted) return;
                        Navigator.pop(ctx);
                        setState(_load);
                      } catch (e) {
                        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                      }
                    },
                  ),
                ),
            ]),
          );
        },
      ),
    );
  }

  /// The order's journey as a rail: each step's state is visible at a glance,
  /// and any deliveries are named underneath rather than hidden in a count.
  Widget _track(List steps, List pickings) {
    if (steps.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
      decoration: BoxDecoration(
        color: const Color(0xFF0E3A5F).withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF0E3A5F).withValues(alpha: 0.10)),
      ),
      child: Column(children: [
        Row(children: [
          for (var i = 0; i < steps.length; i++) ...[
            Expanded(child: Column(children: [
              Row(children: [
                // the connector to the previous step
                Expanded(child: Container(height: 2.5,
                    color: i == 0 ? Colors.transparent
                        : ((steps[i]['done'] == true) ? const Color(0xFF16A34A) : Colors.grey.shade300))),
                Icon(
                  steps[i]['done'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                  color: steps[i]['done'] == true ? const Color(0xFF16A34A) : Colors.grey.shade400,
                  size: 20,
                ),
                Expanded(child: Container(height: 2.5,
                    color: i == steps.length - 1 ? Colors.transparent
                        : ((steps[i + 1]['done'] == true) ? const Color(0xFF16A34A) : Colors.grey.shade300))),
              ]),
              const SizedBox(height: 5),
              Text('${steps[i]['label']}',
                  textAlign: TextAlign.center, maxLines: 2,
                  style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: steps[i]['done'] == true ? FontWeight.w900 : FontWeight.w600,
                      color: steps[i]['done'] == true ? const Color(0xFF0E3A5F) : Colors.grey)),
            ])),
          ],
        ]),
        if (pickings.isNotEmpty) ...[
          const SizedBox(height: 10),
          for (final p in pickings)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(children: [
                Icon(p['done'] == true ? Icons.local_shipping_rounded : Icons.pending_rounded,
                    size: 13, color: p['done'] == true ? const Color(0xFF16A34A) : const Color(0xFFF7A23B)),
                const SizedBox(width: 6),
                Text('${p['name']}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
                const SizedBox(width: 6),
                Text('${p['state_label'] ?? ''}',
                    style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600)),
                const Spacer(),
                if (p['date'] != null)
                  Text('${p['date']}'.split(' ').first,
                      style: TextStyle(fontSize: 9, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
              ]),
            ),
        ],
      ]),
    );
  }

  Widget _deliveryBox(Map o) => Container(
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: const Color(0xFF16A34A).withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFF16A34A).withValues(alpha: 0.18)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (o['delivery_date'] != null)
            Row(children: [
              const Icon(Icons.event_available_rounded, size: 13, color: Color(0xFF16A34A)),
              const SizedBox(width: 6),
              Text(tr('موعد التسليم المطلوب', 'Requested delivery'),
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Color(0xFF16A34A))),
              const SizedBox(width: 6),
              Text('${o['delivery_date']}'.replaceFirst('T', ' ').substring(0, 16),
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900)),
            ]),
          if (o['delivery_address'] != null) ...[
            if (o['delivery_date'] != null) const SizedBox(height: 5),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.place_rounded, size: 13, color: Color(0xFF16A34A)),
              const SizedBox(width: 6),
              Expanded(child: Text('${o['delivery_address']}'.replaceAll('\n', '، '),
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600))),
            ]),
          ],
        ]),
      );

  Widget _lineRow(Map l) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          // The image is only requested when the product actually has one; the
          // API sends null otherwise, so this never renders a blank box.
          ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: l['image'] != null
                ? Image.network('${l['image']}', width: 42, height: 42, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _lineFallback())
                : _lineFallback(),
          ),
          const SizedBox(width: 9),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${l['product']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
            Text('${l['qty']} ${l['uom'] ?? ''} × ${l['price']}',
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
          ])),
          Text('${l['subtotal']}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: Color(0xFF0E3A5F))),
        ]),
      );

  Widget _lineFallback() => Container(
        width: 42, height: 42,
        color: const Color(0xFF0E3A5F).withValues(alpha: 0.06),
        child: Icon(Icons.inventory_2_outlined, size: 19, color: Colors.grey.shade400),
      );

  Widget _kv(String k, String v, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          Text(k, style: const TextStyle(color: Colors.grey)),
          const Spacer(),
          Text(v, style: TextStyle(fontWeight: bold ? FontWeight.w800 : FontWeight.w600)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('طلبات الشراء', 'My orders'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final os = snap.data!;
            if (os.isEmpty) return Center(child: Text(tr('لا طلبات — تسوّق من المتجر', 'No orders — shop now')));
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: os.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final o = os[i] as Map;
                final c = _sc[o['state']] ?? Colors.grey;
                return ListTile(
                  title: Text('${o['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text('${o['date'] ?? ''} · ${o['invoice_status_label'] ?? ''}'),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text('${o['amount_total']} ${o['currency'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    Container(
                      margin: const EdgeInsets.only(top: 2),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                      child: Text('${o['state_label'] ?? o['state']}', style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700)),
                    ),
                  ]),
                  onTap: () => _openOrder(o['id'] as int),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
