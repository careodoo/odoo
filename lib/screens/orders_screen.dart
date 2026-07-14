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
              const SizedBox(height: 12),
              // tracking
              Row(
                children: steps
                    .map<Widget>((s) => Expanded(
                          child: Column(children: [
                            Icon(s['done'] == true ? Icons.check_circle : Icons.radio_button_unchecked,
                                color: s['done'] == true ? const Color(0xFF16A34A) : Colors.grey, size: 20),
                            const SizedBox(height: 4),
                            Text('${s['label']}', style: const TextStyle(fontSize: 10), textAlign: TextAlign.center),
                          ]),
                        ))
                    .toList(),
              ),
              const Divider(height: 24),
              ...((o['lines'] as List?) ?? []).map((l) => ListTile(
                    dense: true,
                    title: Text('${l['product']}'),
                    subtitle: Text('${l['qty']} × ${l['price']}'),
                    trailing: Text('${l['subtotal']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  )),
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
