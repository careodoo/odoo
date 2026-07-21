import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Gate-cashier board — today's takings, who collected what, and the latest
/// receipts. Read-only mirror of the security_management cashier system.
class SecurityCashierScreen extends StatefulWidget {
  const SecurityCashierScreen({super.key});
  @override
  State<SecurityCashierScreen> createState() => _SecurityCashierScreenState();
}

class _SecurityCashierScreenState extends State<SecurityCashierScreen> {
  static const _accent = Color(0xFF0E7A4F);
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.securityCashier();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('صندوق البوابة', 'Gate cashier'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}',
                style: const TextStyle(color: Colors.black54)));
          }
          final d = snap.data ?? const {};
          if (d['available'] == false) {
            return Center(child: Text(tr('نظام الصندوق غير مُفعَّل', 'Cashier system not enabled'),
                style: const TextStyle(color: Colors.black54)));
          }
          final cur = '${d['currency'] ?? 'KWD'}';
          final cashiers = (d['cashiers'] as List?) ?? const [];
          final recent = (d['recent'] as List?) ?? const [];
          return RefreshIndicator(
            color: _accent,
            onRefresh: () async => setState(_load),
            child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
              _todayCard(d, cur),
              const SizedBox(height: 16),
              if (cashiers.isNotEmpty) ...[
                _sectionTitle(tr('حسب أمين الصندوق — اليوم', 'By cashier — today')),
                const SizedBox(height: 8),
                for (final c in cashiers.cast<Map>()) _cashierRow(c, cur),
                const SizedBox(height: 16),
              ],
              _sectionTitle(tr('أحدث الإيصالات', 'Latest receipts')),
              const SizedBox(height: 8),
              if (recent.isEmpty)
                Padding(padding: const EdgeInsets.all(24),
                    child: Center(child: Text(tr('لا إيصالات', 'No receipts'),
                        style: const TextStyle(color: Colors.black45)))),
              for (final r in recent.cast<Map>()) _receiptRow(r, cur),
            ]),
          );
        },
      ),
    );
  }

  Widget _todayCard(Map d, String cur) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [_accent, Color(0xFF0B5F3D)],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(color: _accent.withOpacity(0.3), blurRadius: 16, offset: const Offset(0, 6))],
        ),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('محصّلات اليوم', "Today's takings"),
                style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w700, fontSize: 13)),
            const SizedBox(height: 6),
            Text('${d['today_total'] ?? 0} $cur',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 30)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.18),
                borderRadius: BorderRadius.circular(14)),
            child: Column(children: [
              Text('${d['today_count'] ?? 0}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22)),
              Text(tr('إيصال', 'receipts'), style: const TextStyle(color: Colors.white70, fontSize: 11)),
            ]),
          ),
        ]),
      );

  Widget _sectionTitle(String t) => Text(t,
      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Color(0xFF1D2433)));

  Widget _cashierRow(Map c, String cur) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE3E7EE))),
        child: Row(children: [
          CircleAvatar(radius: 20, backgroundColor: _accent.withOpacity(0.12),
              child: const Icon(Icons.point_of_sale_rounded, color: _accent, size: 20)),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${c['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
            if (c['gate'] != null)
              Text('${c['gate']}', style: const TextStyle(fontSize: 11.5, color: Colors.black54)),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${c['amount'] ?? 0} $cur',
                style: const TextStyle(fontWeight: FontWeight.w900, color: _accent, fontSize: 15)),
            Text('${c['count'] ?? 0} ${tr('إيصال', 'receipts')}',
                style: const TextStyle(fontSize: 11, color: Colors.black45)),
          ]),
        ]),
      );

  Widget _receiptRow(Map r, String cur) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFEDEFF3))),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            const SizedBox(height: 2),
            Text([
              if (r['visitor'] != null) '${r['visitor']}',
              if (r['company'] != null) '${r['company']}',
              if (r['cashier'] != null) '👤 ${r['cashier']}',
              if (r['date'] != null) '${r['date']}',
            ].join(' · '), style: const TextStyle(fontSize: 11, color: Colors.black54)),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${r['amount'] ?? 0} $cur',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF1D2433))),
            if (r['method'] != null)
              Text('${r['method']}', style: const TextStyle(fontSize: 10.5, color: Colors.black45)),
          ]),
        ]),
      );
}
