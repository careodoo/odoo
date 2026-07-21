import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'pdf_report_screen.dart';
import 'payment_webview_screen.dart';

/// Client invoices — totals, list (paid/unpaid + period + approval), and a
/// detail sheet with pay/PDF links and accept/reject.
class InvoicesScreen extends StatefulWidget {
  const InvoicesScreen({super.key});
  @override
  State<InvoicesScreen> createState() => _InvoicesScreenState();
}

class _InvoicesScreenState extends State<InvoicesScreen> {
  late Future<Map<String, dynamic>> _future;

  static const _ps = {
    'paid': Color(0xFF16A34A), 'not_paid': Color(0xFFE11D48), 'partial': Color(0xFFF59E0B),
    'in_payment': Color(0xFF3B82F6),
  };
  static const _ap = {
    'pending': Color(0xFFF59E0B), 'accepted': Color(0xFF16A34A), 'rejected': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientInvoices();

  /// In-app UPayments checkout: ask the server for a hosted-payment link, open
  /// it in a WebView, then settle the sheet once the gateway returns.
  Future<void> _payInApp(BuildContext sheetCtx, int id) async {
    final api = context.read<AuthProvider>().api;
    final messenger = ScaffoldMessenger.of(context);
    showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: CircularProgressIndicator()));
    Map<String, dynamic> link;
    try {
      link = await api.invoicePayLink(id);
    } catch (e) {
      if (mounted) Navigator.of(context).pop(); // close spinner
      messenger.showSnackBar(SnackBar(
          content: Text('${tr('تعذّر بدء الدفع', 'Could not start payment')}: $e')));
      return;
    }
    if (mounted) Navigator.of(context).pop(); // close spinner
    final url = '${link['payment_url'] ?? ''}';
    if (url.isEmpty) {
      messenger.showSnackBar(SnackBar(
          content: Text(tr('رابط الدفع غير متاح', 'Payment link unavailable'))));
      return;
    }
    if (!mounted) return;
    final paid = await Navigator.of(context).push<bool>(
        MaterialPageRoute(builder: (_) => PaymentWebViewScreen(url: url)));
    if (paid == true) {
      // Give the webhook a beat, then confirm settlement from the server.
      bool settled = false;
      for (var i = 0; i < 4 && !settled; i++) {
        await Future.delayed(const Duration(seconds: 2));
        try {
          final st = await api.invoicePayStatus(id);
          settled = st['paid'] == true;
        } catch (_) {}
      }
      messenger.showSnackBar(SnackBar(
          backgroundColor: settled ? const Color(0xFF16A34A) : const Color(0xFFF59E0B),
          content: Text(settled
              ? tr('تم الدفع بنجاح ✅', 'Paid successfully ✅')
              : tr('تم استلام الدفع، جارٍ التأكيد…', 'Payment received, confirming…'))));
      if (Navigator.of(sheetCtx).canPop()) Navigator.of(sheetCtx).pop();
      setState(() => _load());
    }
  }

  Future<void> _detail(int id) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      clipBehavior: Clip.antiAlias,
      builder: (_) => FutureBuilder<Map<String, dynamic>>(
        future: context.read<AuthProvider>().api.clientInvoice(id),
        builder: (ctx, snap) {
          if (!snap.hasData) return const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()));
          final m = snap.data!;
          final payments = (m['payments'] as List?) ?? [];
          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.8,
            maxChildSize: 0.95,
            builder: (_, sc) => ListView(controller: sc, padding: EdgeInsets.zero, children: [
              // A header that answers the question the invoice is opened for:
              // is it paid, and how much is left. The old sheet led with a
              // number and left the status to be inferred from two rows near
              // the bottom.
              Builder(builder: (_) {
                final residual = numOf(m['amount_residual']);
                final total = numOf(m['amount_total']);
                final paid = numOf(m['amount_paid']);
                final done = residual <= 0.001 && total > 0;
                final part = paid > 0 && residual > 0.001;
                final c = done
                    ? const Color(0xFF16A34A)
                    : (part ? const Color(0xFFF59E0B) : const Color(0xFF7A1340));
                final label = done
                    ? tr('مدفوعة بالكامل', 'Paid in full')
                    : (part ? tr('مدفوعة جزئيًا', 'Partly paid') : tr('غير مدفوعة', 'Unpaid'));
                return Container(
                  padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                        colors: [c, Color.lerp(c, Colors.black, 0.28)!],
                        begin: Alignment.topRight, end: Alignment.bottomLeft),
                  ),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(
                        child: Text('${m['name']}',
                            style: const TextStyle(
                                color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                        decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.22),
                            borderRadius: BorderRadius.circular(20)),
                        child: Text(label,
                            style: const TextStyle(
                                color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900)),
                      ),
                    ]),
                    const SizedBox(height: 10),
                    Text('${m['amount_total']} ${m['currency'] ?? ''}',
                        style: const TextStyle(
                            color: Colors.white, fontSize: 27, fontWeight: FontWeight.w900)),
                    if (residual > 0.001) ...[
                      const SizedBox(height: 4),
                      Text(
                          '${tr('المتبقّي', 'Outstanding')}: ${m['amount_residual']} '
                          '${m['currency'] ?? ''}',
                          style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.92),
                              fontSize: 12.5, fontWeight: FontWeight.w700)),
                    ],
                    if (total > 0) ...[
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: (paid / total).clamp(0.0, 1.0),
                          minHeight: 7,
                          color: Colors.white,
                          backgroundColor: Colors.white.withValues(alpha: 0.25),
                        ),
                      ),
                    ],
                    if (m['invoice_date'] != null || m['due_date'] != null) ...[
                      const SizedBox(height: 10),
                      Text(
                          [
                            if (m['invoice_date'] != null)
                              '${tr('التاريخ', 'Date')}: ${m['invoice_date']}',
                            if (m['due_date'] != null)
                              '${tr('الاستحقاق', 'Due')}: ${m['due_date']}',
                          ].join('   ·   '),
                          style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
                    ],
                  ]),
                );
              }),
              // ALL actions live here, right under the header — pay, print,
              // accept, reject — instead of being scattered top and bottom.
              // small, consistent actions in ONE horizontal row (scrolls if
              // they don't all fit) instead of wrapping to two rows.
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.fromLTRB(14, 6, 14, 6),
                  children: [
                    if (numOf(m['amount_residual']) > 0.001)
                      _actBtn(Icons.payment_rounded, tr('ادفع الآن', 'Pay now'), const Color(0xFF2563EB),
                          filled: true, onTap: () => _payInApp(ctx, id)),
                    if (m['pdf_url'] != null)
                      _actBtn(Icons.picture_as_pdf_rounded, 'PDF', const Color(0xFF7A1340),
                          onTap: () => Navigator.push(context, MaterialPageRoute(
                              builder: (_) => PdfReportScreen(
                                  url: '${m['pdf_url']}',
                                  title: tr('فاتورة ${m['name'] ?? ''}', 'Invoice ${m['name'] ?? ''}'),
                                  fileName: 'invoice-${m['name'] ?? ''}.pdf')))),
                    if ((m['client_approval'] ?? 'pending') == 'pending') ...[
                      _actBtn(Icons.check_circle_rounded, tr('قبول', 'Accept'), const Color(0xFF16A34A),
                          filled: true, onTap: () => _decision(ctx, id, true)),
                      _actBtn(Icons.cancel_rounded, tr('رفض', 'Reject'), const Color(0xFFE11D48),
                          onTap: () => _decision(ctx, id, false)),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 8),
              // lined, tabular invoice items — a header row then bordered rows
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Column(children: [
                  _lineRow(tr('البند', 'Item'), tr('كمية', 'Qty'), tr('السعر', 'Price'),
                      tr('الإجمالي', 'Total'), header: true),
                  for (final l in ((m['lines'] as List?) ?? const []))
                    _lineRow('${l['name'] ?? ''}', '${l['qty'] ?? ''}',
                        '${l['price'] ?? ''}', '${l['subtotal'] ?? ''}'),
                ]),
              ),
              const SizedBox(height: 10),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Column(children: [
              _kv(tr('قبل الضريبة', 'Untaxed'), '${m['amount_untaxed']}'),
              _kv(tr('الضريبة', 'Tax'), '${m['amount_tax']}'),
              _kv(tr('الإجمالي', 'Total'), '${m['amount_total']} ${m['currency'] ?? ''}', bold: true),
              _kv(tr('المدفوع', 'Paid'), '${m['amount_paid']}', color: const Color(0xFF16A34A)),
              _kv(tr('المتبقّي', 'Residual'), '${m['amount_residual']}', color: const Color(0xFFE11D48)),
                ]),
              ),
              if (payments.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(tr('سجلّات الدفع', 'Payment records'), style: const TextStyle(fontWeight: FontWeight.w800)),
                ...payments.map((p) => ListTile(
                      dense: true,
                      leading: const Icon(Icons.payments, color: Color(0xFF16A34A)),
                      title: Text('${p['name'] ?? ''}'),
                      subtitle: Text('${p['method'] ?? ''} · ${p['date'] ?? ''}'),
                      trailing: Text('${p['amount']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    )),
              ],
              const SizedBox(height: 20),
            ]),
          );
        },
      ),
    );
  }

  Future<void> _decision(BuildContext ctx, int id, bool accept) async {
    String comment = '';
    if (!accept) {
      final ctrl = TextEditingController();
      final ok = await showDialog<bool>(
        context: ctx,
        builder: (_) => AlertDialog(
          title: Text(tr('سبب الرفض', 'Rejection reason')),
          content: TextField(controller: ctrl, maxLines: 3),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال', 'Send'))),
          ],
        ),
      );
      if (ok != true) return;
      comment = ctrl.text.trim();
    }
    try {
      final api = context.read<AuthProvider>().api;
      if (accept) {
        await api.invoiceApprove(id, comment);
      } else {
        await api.invoiceReject(id, comment);
      }
      if (!mounted) return;
      Navigator.pop(ctx);
      setState(_load);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(accept ? tr('تم القبول', 'Accepted') : tr('تم الرفض', 'Rejected'))));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  /// A small, consistent action button for the invoice actions row.
  Widget _actBtn(IconData icon, String label, Color color,
          {bool filled = false, required VoidCallback onTap}) =>
      Padding(
        padding: const EdgeInsets.only(left: 8),
        child: Material(
          color: filled ? color : Colors.white,
          borderRadius: BorderRadius.circular(9),
          child: InkWell(
            borderRadius: BorderRadius.circular(9),
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(9),
                border: filled ? null : Border.all(color: color),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(icon, size: 16, color: filled ? Colors.white : color),
                const SizedBox(width: 5),
                Text(label, style: TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w800,
                    color: filled ? Colors.white : color)),
              ]),
            ),
          ),
        ),
      );

  /// One ruled row of the invoice item table.
  Widget _lineRow(String item, String qty, String price, String total,
          {bool header = false}) =>
      Container(
        decoration: BoxDecoration(
          color: header ? const Color(0xFFF1F3F7) : Colors.white,
          border: const Border(bottom: BorderSide(color: Color(0xFFE7EAF0))),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        child: Row(children: [
          Expanded(flex: 5, child: Text(item, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12.5,
                  fontWeight: header ? FontWeight.w900 : FontWeight.w600,
                  color: header ? const Color(0xFF64748B) : const Color(0xFF1D2433)))),
          Expanded(flex: 2, child: Text(qty, textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, fontWeight: header ? FontWeight.w900 : FontWeight.w500))),
          Expanded(flex: 3, child: Text(price, textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, fontWeight: header ? FontWeight.w900 : FontWeight.w500))),
          Expanded(flex: 3, child: Text(total, textAlign: TextAlign.end,
              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800,
                  color: header ? const Color(0xFF64748B) : const Color(0xFF1D2433)))),
        ]),
      );

  Widget _kv(String k, String v, {bool bold = false, Color? color}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          Text(k, style: const TextStyle(color: Colors.grey)),
          const Spacer(),
          Text(v, style: TextStyle(fontWeight: bold ? FontWeight.w800 : FontWeight.w600, color: color)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('الفواتير', 'Invoices'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final inv = (snap.data!['invoices'] as List?) ?? [];
            final t = (snap.data!['totals'] as Map?) ?? {};
            return ListView(padding: const EdgeInsets.all(12), children: [
              Row(children: [
                _tot(tr('المدفوع', 'Paid'), '${(t['paid'] ?? 0)}', const Color(0xFF16A34A)),
                const SizedBox(width: 8),
                _tot(tr('غير المدفوع', 'Outstanding'), '${(t['residual'] ?? 0)}', const Color(0xFFE11D48)),
              ]),
              const SizedBox(height: 8),
              if (inv.isEmpty) Padding(padding: const EdgeInsets.all(24), child: Center(child: Text(tr('لا فواتير', 'No invoices')))),
              ...inv.map((m) {
                final pc = _ps[m['payment_state']] ?? Colors.grey;
                final ac = _ap[m['client_approval'] ?? 'pending'] ?? Colors.grey;
                return Card(
                  child: ListTile(
                    title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text('${m['period'] ?? ''} · ${m['date'] ?? ''}'),
                    trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text('${m['amount_residual']}', style: TextStyle(color: numOf(m['amount_residual']) > 0 ? const Color(0xFFE11D48) : const Color(0xFF16A34A), fontWeight: FontWeight.w800)),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        _pill('${m['payment_label'] ?? ''}', pc),
                        const SizedBox(width: 4),
                        _pill('${m['approval_label'] ?? ''}', ac),
                      ]),
                    ]),
                    onTap: () => _detail(m['id'] as int),
                  ),
                );
              }),
            ]);
          },
        ),
      ),
    );
  }

  Widget _tot(String l, String v, Color c) => Expanded(
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(v, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: c)),
            Text(l, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ]),
        ),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w700)),
      );
}
