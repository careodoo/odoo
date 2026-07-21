import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'pdf_report_screen.dart';

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

  Future<void> _open(String url) async {
    // don't gate on canLaunchUrl — it can report false even when a handler
    // exists; just try, and tell the user if it genuinely fails.
    final u = Uri.parse(url);
    try {
      if (await launchUrl(u, mode: LaunchMode.externalApplication)) return;
    } catch (_) {}
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
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
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
                child: Wrap(spacing: 8, runSpacing: 8, children: [
                  if (m['pay_url'] != null && numOf(m['amount_residual']) > 0.001)
                    FilledButton.icon(
                        onPressed: () => _open('${m['pay_url']}'),
                        icon: const Icon(Icons.payment_rounded, size: 19),
                        label: Text(tr('ادفع الآن', 'Pay now'),
                            style: const TextStyle(fontWeight: FontWeight.w800))),
                  if (m['pdf_url'] != null)
                    OutlinedButton.icon(
                        onPressed: () => Navigator.push(context, MaterialPageRoute(
                            builder: (_) => PdfReportScreen(
                                url: '${m['pdf_url']}',
                                title: tr('فاتورة ${m['name'] ?? ''}', 'Invoice ${m['name'] ?? ''}'),
                                fileName: 'invoice-${m['name'] ?? ''}.pdf'))),
                        icon: const Icon(Icons.picture_as_pdf_rounded, size: 19),
                        label: const Text('PDF')),
                  if ((m['client_approval'] ?? 'pending') == 'pending') ...[
                    FilledButton.icon(
                        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
                        onPressed: () => _decision(ctx, id, true),
                        icon: const Icon(Icons.check_circle_rounded, size: 19),
                        label: Text(tr('قبول', 'Accept'),
                            style: const TextStyle(fontWeight: FontWeight.w800))),
                    OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE11D48)),
                        onPressed: () => _decision(ctx, id, false),
                        icon: const Icon(Icons.cancel_rounded, size: 19),
                        label: Text(tr('رفض', 'Reject'))),
                  ],
                ]),
              ),
              const Divider(height: 20),
              ...((m['lines'] as List?) ?? []).map((l) => ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 18),
                    dense: true,
                    title: Text('${l['name'] ?? ''}'),
                    subtitle: Text('${l['qty']} × ${l['price']}'),
                    trailing: Text('${l['subtotal']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  )),
              const Divider(),
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
                      Text('${m['amount_residual']}', style: TextStyle(color: (m['amount_residual'] as num) > 0 ? const Color(0xFFE11D48) : const Color(0xFF16A34A), fontWeight: FontWeight.w800)),
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
