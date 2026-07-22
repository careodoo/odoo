import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;

/// Professional finance dashboard: contract value, Kuwait target + achievement,
/// monthly invoice, salaries, allowances, materials, diesel and total expenses.
class FinanceScreen extends StatefulWidget {
  final int projectId;
  const FinanceScreen({super.key, required this.projectId});
  @override
  State<FinanceScreen> createState() => _FinanceScreenState();
}

class _FinanceScreenState extends State<FinanceScreen> {
  Map<String, dynamic>? _d;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.pmsFinance(widget.projectId);
      if (mounted) setState(() { _d = d; _error = null; });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  static const _icons = {
    'contract': Icons.description_rounded, 'target': Icons.flag_rounded,
    'invoice': Icons.receipt_rounded, 'invoices': Icons.receipt_long_rounded,
    'salary': Icons.payments_rounded, 'allowance': Icons.card_giftcard_rounded,
    'materials': Icons.inventory_2_rounded, 'fuel': Icons.local_gas_station_rounded,
    'petty': Icons.account_balance_wallet_rounded, 'expenses': Icons.trending_down_rounded,
  };

  Color _hex(String h) {
    h = h.replaceAll('#', '');
    if (h.length == 6) h = 'FF$h';
    return Color(int.tryParse(h, radix: 16) ?? 0xFF6B7280);
  }

  String _money(dynamic v, String cur) {
    if (v == null) return '—';
    final n = (v is num) ? v : num.tryParse('$v') ?? 0;
    final s = n.toStringAsFixed(n == n.roundToDouble() ? 0 : 3);
    // thousands separator
    final parts = s.split('.');
    final intp = parts[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ',');
    return '$intp${parts.length > 1 ? '.${parts[1]}' : ''} $cur';
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(tr('المالية', 'Finance'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
      ),
      body: d == null
          ? (_error != null
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('$_error', style: const TextStyle(color: Pms.red))))
              : const Center(child: CircularProgressIndicator()))
          : RefreshIndicator(onRefresh: _load, child: ListView(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 30),
              children: [
                _targetHero(d),
                if (d['contract'] != null) ...[const SizedBox(height: 14), _contractCard(d)],
                const SizedBox(height: 14),
                Text(tr('التفاصيل المالية', 'Financial breakdown'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Pms.ink)),
                const SizedBox(height: 8),
                GridView.count(
                  crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 9, crossAxisSpacing: 9, childAspectRatio: 1.55,
                  children: [for (final c in (d['cards'] as List? ?? const [])) _card(c as Map, '${d['currency'] ?? ''}')],
                ),
              ],
            )),
    );
  }

  Widget _targetHero(Map d) {
    final target = d['target'];
    final revenue = d['revenue'] ?? 0;
    final ach = d['achievement'];
    final achV = (ach is num) ? ach.toDouble() : 0.0;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(18),
          gradient: const LinearGradient(colors: [Color(0xFF7C3AED), Color(0xFF4C1D95)],
              begin: Alignment.topRight, end: Alignment.bottomLeft)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.flag_rounded, color: Colors.white, size: 20),
          const SizedBox(width: 8),
          Text(tr('الكويت تارجت', 'Kuwait Target'),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
          const Spacer(),
          if (ach != null) Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
            child: Text('$ach%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
          ),
        ]),
        const SizedBox(height: 12),
        Text(target == null ? tr('لم يُحدَّد بعد', 'Not set yet') : _money(target, '${d['currency'] ?? ''}'),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 24)),
        const SizedBox(height: 4),
        Text('${tr('المحقّق', 'Achieved')}: ${_money(revenue, '${d['currency'] ?? ''}')}',
            style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5, fontWeight: FontWeight.w700)),
        if (target != null) ...[
          const SizedBox(height: 10),
          ClipRRect(borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: (achV / 100).clamp(0.0, 1.0), minHeight: 8,
                color: Colors.white, backgroundColor: Colors.white.withValues(alpha: 0.25))),
        ],
      ]),
    );
  }

  Widget _contractCard(Map d) {
    final c = d['contract'] as Map;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 38, height: 38, alignment: Alignment.center,
            decoration: BoxDecoration(color: const Color(0xFF15213B).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(11)),
            child: const Icon(Icons.assignment_rounded, color: Color(0xFF15213B))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('العقد', 'Contract'), style: const TextStyle(fontSize: 11, color: Pms.slate, fontWeight: FontWeight.w700)),
            Text('${c['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          ])),
          if (c['has_copy'] == true) const Icon(Icons.picture_as_pdf_rounded, color: Color(0xFF7A1340), size: 20),
        ]),
        const Divider(height: 18),
        Wrap(spacing: 16, runSpacing: 8, children: [
          if (c['amount'] != null) _ck(tr('القيمة', 'Value'), _money(c['amount'], '${d['currency'] ?? ''}'), const Color(0xFF16A34A)),
          if (c['no'] != null) _ck(tr('رقم العقد', 'Contract No.'), '${c['no']}', Pms.ink),
          if (c['type'] != null) _ck(tr('النوع', 'Type'), '${c['type']}', Pms.slate),
          if (c['insurance'] != null && (c['insurance'] as num) > 0) _ck(tr('التأمين', 'Insurance'), _money(c['insurance'], '${d['currency'] ?? ''}'), const Color(0xFF0891B2)),
          _ck(tr('التمديدات', 'Renewals'), '${c['renewals'] ?? 0}', const Color(0xFFEA580C)),
          if (c['expiry'] != null) _ck(tr('الانتهاء', 'Expiry'), '${c['expiry']}', Pms.red),
        ]),
      ]),
    );
  }

  Widget _ck(String k, String v, Color c) => Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(k, style: const TextStyle(fontSize: 10, color: Pms.slate, fontWeight: FontWeight.w700)),
        Text(v, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: c)),
      ]);

  Widget _card(Map c, String cur) {
    final color = _hex('${c['color'] ?? '#6B7280'}');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withValues(alpha: 0.16)),
          boxShadow: [BoxShadow(color: color.withValues(alpha: 0.06), blurRadius: 6, offset: const Offset(0, 2))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Row(children: [
          Container(width: 30, height: 30, alignment: Alignment.center,
            decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(9)),
            child: Icon(_icons['${c['icon']}'] ?? Icons.attach_money_rounded, size: 16, color: color)),
          const Spacer(),
        ]),
        Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text(_money(c['value'], cur), maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink)),
          const SizedBox(height: 2),
          Text('${c['label']}', style: const TextStyle(fontSize: 10.5, color: Pms.slate, fontWeight: FontWeight.w700)),
        ]),
      ]),
    );
  }
}
