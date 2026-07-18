import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Client purchase orders — a professional dashboard: KPI header, filter chips,
/// rich order cards, and a polished tracking/detail sheet.
class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});
  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<List<dynamic>> _future;
  String _filter = 'all';

  static const _accent = Color(0xFFC0392B);
  static const _navy = Color(0xFF0E3A5F);
  static const _sc = {
    'draft': Color(0xFF64748B), 'sent': Color(0xFF3B82F6), 'sale': Color(0xFF16A34A),
    'done': Color(0xFF0891B2), 'cancel': Color(0xFFE11D48),
  };
  static const _si = {
    'draft': Icons.edit_note_rounded, 'sent': Icons.mark_email_read_rounded,
    'sale': Icons.check_circle_rounded, 'done': Icons.inventory_rounded,
    'cancel': Icons.cancel_rounded,
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientOrders();

  // ————————————————————————————————————————————— detail sheet
  Future<void> _openOrder(int id) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FutureBuilder<Map<String, dynamic>>(
        future: context.read<AuthProvider>().api.clientOrder(id),
        builder: (ctx, snap) {
          if (!snap.hasData) {
            return Container(
              height: 240,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: const Center(child: CircularProgressIndicator(color: _accent)),
            );
          }
          final o = snap.data!;
          final steps = (o['tracking']?['steps'] as List?) ?? [];
          final invs = (o['invoices'] as List?) ?? [];
          final st = '${o['state']}';
          final c = _sc[st] ?? Colors.grey;
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.82,
            minChildSize: 0.5,
            maxChildSize: 0.96,
            builder: (_, sc) => Container(
              decoration: const BoxDecoration(
                color: Color(0xFFF6F7F9),
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              clipBehavior: Clip.antiAlias,
              child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
                // gradient header band
                CustomPaint(
                  painter: const BrandPattern(opacity: 0.07),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 18),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color.lerp(c, Colors.white, 0.12)!, Color.lerp(c, Colors.black, 0.3)!],
                        begin: Alignment.topRight, end: Alignment.bottomLeft),
                    ),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
                          decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                      Row(children: [
                        Container(
                          width: 44, height: 44, alignment: Alignment.center,
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(13)),
                          child: Icon(_si[st] ?? Icons.receipt_long_rounded, color: Colors.white, size: 24),
                        ),
                        const SizedBox(width: 12),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${o['name']}', style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 2),
                          Text('${o['state_label'] ?? o['state']}${o['date'] != null ? ' · ${o['date']}' : ''}',
                              style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12)),
                        ])),
                        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                          Text('${o['amount_total']}', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
                          Text('${o['currency'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11, fontWeight: FontWeight.w700)),
                        ]),
                      ]),
                    ]),
                  ),
                ),
                Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  if (steps.isNotEmpty) ...[
                    _sheetLabel(Icons.timeline_rounded, tr('حالة الطلب', 'Order progress')),
                    const SizedBox(height: 8),
                    _track(steps, (o['tracking']?['pickings'] as List?) ?? const []),
                    const SizedBox(height: 14),
                  ],
                  if (o['delivery_address'] != null || o['delivery_date'] != null) ...[
                    _deliveryBox(o),
                    const SizedBox(height: 14),
                  ],
                  _sheetLabel(Icons.inventory_2_rounded, tr('الأصناف', 'Items')),
                  const SizedBox(height: 8),
                  _card(Column(children: [
                    ...((o['lines'] as List?) ?? []).map((l) => _lineRow(l as Map)),
                    const Divider(height: 18),
                    _kv(tr('قبل الضريبة', 'Untaxed'), '${o['amount_untaxed']} ${o['currency'] ?? ''}'),
                    _kv(tr('الضريبة', 'Tax'), '${o['amount_tax']} ${o['currency'] ?? ''}'),
                    _kv(tr('الإجمالي', 'Total'), '${o['amount_total']} ${o['currency'] ?? ''}', bold: true),
                  ])),
                  if (invs.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    _sheetLabel(Icons.receipt_rounded, tr('الفواتير', 'Invoices')),
                    const SizedBox(height: 8),
                    _card(Column(children: [
                      for (var i = 0; i < invs.length; i++) ...[
                        if (i > 0) const Divider(height: 14),
                        Row(children: [
                          const Icon(Icons.description_outlined, size: 18, color: _navy),
                          const SizedBox(width: 8),
                          Expanded(child: Text('${invs[i]['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13))),
                          Text('${tr('المتبقّي', 'Due')}: ${invs[i]['amount_residual']} ${invs[i]['currency'] ?? ''}',
                              style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700, fontWeight: FontWeight.w700)),
                        ]),
                      ],
                    ])),
                  ],
                  if (o['can_cancel'] == true)
                    Padding(
                      padding: const EdgeInsets.only(top: 18),
                      child: SizedBox(width: double.infinity, child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFFE11D48),
                          side: const BorderSide(color: Color(0xFFE11D48)),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        icon: const Icon(Icons.close_rounded, size: 18),
                        label: Text(tr('إلغاء الطلب', 'Cancel order'), style: const TextStyle(fontWeight: FontWeight.w800)),
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
                      )),
                    ),
                  const SizedBox(height: 8),
                ])),
              ]),
            ),
          );
        },
      ),
    );
  }

  Widget _sheetLabel(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _accent),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _card(Widget child) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 3))],
        ),
        child: child,
      );

  /// The order's journey as a rail: each step's state is visible at a glance,
  /// and any deliveries are named underneath rather than hidden in a count.
  Widget _track(List steps, List pickings) {
    if (steps.isEmpty) return const SizedBox.shrink();
    return _card(Column(children: [
      Row(children: [
        for (var i = 0; i < steps.length; i++) ...[
          Expanded(child: Column(children: [
            Row(children: [
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
                    color: steps[i]['done'] == true ? _navy : Colors.grey)),
          ])),
        ],
      ]),
      if (pickings.isNotEmpty) ...[
        const Divider(height: 16),
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
    ]));
  }

  Widget _deliveryBox(Map o) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF16A34A).withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF16A34A).withValues(alpha: 0.2)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (o['delivery_date'] != null)
            Row(children: [
              const Icon(Icons.event_available_rounded, size: 14, color: Color(0xFF16A34A)),
              const SizedBox(width: 6),
              Text(tr('موعد التسليم المطلوب', 'Requested delivery'),
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: Color(0xFF16A34A))),
              const SizedBox(width: 6),
              Text('${o['delivery_date']}'.replaceFirst('T', ' ').substring(0, 16),
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900)),
            ]),
          if (o['delivery_address'] != null) ...[
            if (o['delivery_date'] != null) const SizedBox(height: 6),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.place_rounded, size: 14, color: Color(0xFF16A34A)),
              const SizedBox(width: 6),
              Expanded(child: Text('${o['delivery_address']}'.replaceAll('\n', '، '),
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600))),
            ]),
          ],
        ]),
      );

  Widget _lineRow(Map l) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(9),
            child: l['image'] != null
                ? Image.network('${l['image']}', width: 44, height: 44, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _lineFallback())
                : _lineFallback(),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${l['product']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
            Text('${l['qty']} ${l['uom'] ?? ''} × ${l['price']}',
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
          ])),
          Text('${l['subtotal']}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: _navy)),
        ]),
      );

  Widget _lineFallback() => Container(
        width: 44, height: 44,
        color: _navy.withValues(alpha: 0.06),
        child: Icon(Icons.inventory_2_outlined, size: 19, color: Colors.grey.shade400),
      );

  Widget _kv(String k, String v, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2.5),
        child: Row(children: [
          Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: bold ? 13.5 : 12.5)),
          const Spacer(),
          Text(v, style: TextStyle(fontWeight: bold ? FontWeight.w900 : FontWeight.w600,
              fontSize: bold ? 14 : 12.5, color: bold ? _navy : Colors.black87)),
        ]),
      );

  // ————————————————————————————————————————————— list + stats
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(title: Text(tr('طلبات الشراء', 'Purchase orders')), backgroundColor: _accent, foregroundColor: Colors.white),
      body: RefreshIndicator(
        color: _accent,
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _accent));
            final all = snap.data!.cast<Map>();
            if (all.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 120),
                Icon(Icons.shopping_bag_outlined, size: 64, color: Colors.grey.shade300),
                const SizedBox(height: 12),
                Center(child: Text(tr('لا طلبات — تسوّق من المتجر', 'No orders yet — shop now'),
                    style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
              ]);
            }
            final shown = all.where((o) => _match(o)).toList();
            return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
              _statsHeader(all),
              _filterBar(all),
              const SizedBox(height: 4),
              if (shown.isEmpty)
                Padding(padding: const EdgeInsets.all(40), child: Center(
                    child: Text(tr('لا طلبات في هذا التصنيف', 'No orders in this filter'),
                        style: TextStyle(color: Colors.grey.shade500)))),
              ...shown.map(_orderCard),
            ]);
          },
        ),
      ),
    );
  }

  bool _match(Map o) {
    final s = '${o['state']}';
    switch (_filter) {
      case 'active': return s == 'sale' || s == 'sent' || s == 'draft';
      case 'done': return s == 'done';
      case 'cancel': return s == 'cancel';
      default: return true;
    }
  }

  num _num(dynamic v) => v is num ? v : num.tryParse('$v') ?? 0;

  Widget _statsHeader(List<Map> all) {
    final total = all.length;
    final active = all.where((o) => ['sale', 'sent', 'draft'].contains('${o['state']}')).length;
    final delivered = all.where((o) => '${o['state']}' == 'done').length;
    final spent = all.where((o) => '${o['state']}' != 'cancel').fold<num>(0, (s, o) => s + _num(o['amount_total']));
    final cur = all.isNotEmpty ? '${all.first['currency'] ?? ''}' : '';
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.06),
      child: Container(
        margin: const EdgeInsets.fromLTRB(12, 12, 12, 6),
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: _accent.withValues(alpha: 0.3), blurRadius: 14, offset: const Offset(0, 7))],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.account_balance_wallet_rounded, color: Colors.white70, size: 16),
            const SizedBox(width: 6),
            Text(tr('إجمالي المشتريات', 'Total spend'),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 4),
          Text('${spent.toStringAsFixed(3)} $cur', style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          Row(children: [
            _kpi(Icons.receipt_long_rounded, '$total', tr('طلب', 'Orders')),
            _kpiDiv(),
            _kpi(Icons.pending_actions_rounded, '$active', tr('قيد التنفيذ', 'Active')),
            _kpiDiv(),
            _kpi(Icons.inventory_rounded, '$delivered', tr('مُستلمة', 'Delivered')),
          ]),
        ]),
      ),
    );
  }

  Widget _kpi(IconData ic, String v, String l) => Expanded(
        child: Column(children: [
          Icon(ic, color: Colors.white, size: 18),
          const SizedBox(height: 4),
          Text(v, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
          Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 10, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _kpiDiv() => Container(width: 1, height: 34, color: Colors.white.withValues(alpha: 0.2));

  Widget _filterBar(List<Map> all) {
    final counts = {
      'all': all.length,
      'active': all.where((o) => ['sale', 'sent', 'draft'].contains('${o['state']}')).length,
      'done': all.where((o) => '${o['state']}' == 'done').length,
      'cancel': all.where((o) => '${o['state']}' == 'cancel').length,
    };
    final chips = [
      ('all', tr('الكل', 'All')),
      ('active', tr('قيد التنفيذ', 'Active')),
      ('done', tr('مُستلمة', 'Delivered')),
      ('cancel', tr('ملغاة', 'Cancelled')),
    ];
    return SizedBox(
      height: 42,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        children: [
          for (final ch in chips)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: ChoiceChip(
                selected: _filter == ch.$1,
                onSelected: (_) => setState(() => _filter = ch.$1),
                showCheckmark: false,
                label: Text('${ch.$2} (${counts[ch.$1]})',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12,
                        color: _filter == ch.$1 ? Colors.white : _navy)),
                selectedColor: _accent,
                backgroundColor: Colors.white,
                side: BorderSide(color: _filter == ch.$1 ? _accent : Colors.grey.shade300),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _orderCard(Map o) {
    final s = '${o['state']}';
    final c = _sc[s] ?? Colors.grey;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 6, 12, 0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 8, offset: const Offset(0, 3))],
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openOrder(o['id'] as int),
        child: Row(children: [
          Container(width: 5, height: 74, color: c),
          Container(
            margin: const EdgeInsets.all(11),
            width: 44, height: 44, alignment: Alignment.center,
            decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
            child: Icon(_si[s] ?? Icons.receipt_long_rounded, color: c, size: 22),
          ),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${o['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
            const SizedBox(height: 3),
            Row(children: [
              Icon(Icons.event_rounded, size: 11, color: Colors.grey.shade500),
              const SizedBox(width: 3),
              Text('${o['date'] ?? '—'}', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              if (o['invoice_status_label'] != null) ...[
                const SizedBox(width: 8),
                Icon(Icons.receipt_rounded, size: 11, color: Colors.grey.shade500),
                const SizedBox(width: 3),
                Flexible(child: Text('${o['invoice_status_label']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600))),
              ],
            ]),
          ])),
          Padding(
            padding: const EdgeInsets.only(right: 12, left: 6),
            child: Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
              Text('${o['amount_total']} ${o['currency'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                child: Text('${o['state_label'] ?? o['state']}',
                    style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800)),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}
