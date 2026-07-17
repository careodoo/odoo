import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// The customer's long-term / contract requests, with quotes to approve.
class C2CContractsScreen extends StatefulWidget {
  const C2CContractsScreen({super.key});
  @override
  State<C2CContractsScreen> createState() => _C2CContractsScreenState();
}

class _C2CContractsScreenState extends State<C2CContractsScreen> {
  Future<List<dynamic>>? _list;

  static const _stC = {
    'new': Color(0xFF3B82F6), 'reviewing': Color(0xFFF59E0B), 'quoted': Color(0xFF8B5CF6),
    'approved': Color(0xFF16A34A), 'converted': Color(0xFF16A34A), 'rejected': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _list = context.read<AuthProvider>().api.c2cContracts());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(backgroundColor: C2C.red, foregroundColor: Colors.white, title: Text(tr('طلبات التعاقد وعروض الأسعار', 'My contracts & quotes'))),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _list,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final rows = snap.data!;
            if (rows.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 100),
                const Center(child: Text('📄', style: TextStyle(fontSize: 56))),
                Center(child: Padding(padding: const EdgeInsets.all(12), child: Text(tr('لا طلبات تعاقد', 'No contract requests'), style: const TextStyle(color: Colors.grey, fontSize: 16)))),
              ]);
            }
            return ListView(padding: const EdgeInsets.all(12), children: [for (final r in rows) _card(r as Map)]);
          },
        ),
      ),
    );
  }

  Widget _card(Map r) {
    final st = '${r['state']}';
    final c = _stC[st] ?? Colors.grey;
    final quoted = st == 'quoted' && r['quote_amount'] != null;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${r['title']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3), decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)), child: Text('${r['state_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11))),
        ]),
        const SizedBox(height: 4),
        Text('${r['name']} · ${r['category'] ?? ''} · ${r['duration_months']} ${tr('شهر', 'mo')}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
        if (quoted) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFF8B5CF6).withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(tr('عرض السعر', 'Quote'), style: const TextStyle(fontWeight: FontWeight.w800)),
                const Spacer(),
                Text('${r['quote_amount']} KWD/${r['quote_period'] == 'yearly' ? tr('سنة', 'yr') : r['quote_period'] == 'monthly' ? tr('شهر', 'mo') : tr('إجمالي', 'total')}', style: const TextStyle(color: Color(0xFF8B5CF6), fontWeight: FontWeight.w900, fontSize: 16)),
              ]),
              if (r['quote_note'] != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text('${r['quote_note']}', style: const TextStyle(fontSize: 12, color: Colors.black87))),
              const SizedBox(height: 10),
              Row(children: [
                Expanded(child: ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white), onPressed: () => _decide(r['id'] as int, 'approve'), child: Text(tr('موافقة', 'Approve')))),
                const SizedBox(width: 8),
                Expanded(child: OutlinedButton(style: OutlinedButton.styleFrom(foregroundColor: C2C.red), onPressed: () => _decide(r['id'] as int, 'reject'), child: Text(tr('رفض', 'Reject')))),
              ]),
            ]),
          ),
        ],
        if (st == 'approved') Padding(padding: const EdgeInsets.only(top: 8), child: Text('✅ ${tr('بانتظار التفعيل من فريق CARE', 'Awaiting activation by CARE')}', style: const TextStyle(color: Color(0xFF16A34A), fontSize: 12, fontWeight: FontWeight.w700))),
        if (st == 'converted') Padding(padding: const EdgeInsets.only(top: 8), child: Text('🎉 ${tr('تم تفعيلك كعميل إدارة مرافق', 'Activated as a facilities client')}', style: const TextStyle(color: Color(0xFF16A34A), fontSize: 12, fontWeight: FontWeight.w700))),
      ]),
    );
  }

  Future<void> _decide(int id, String decision) async {
    try {
      await context.read<AuthProvider>().api.c2cContractDecide(id, decision);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(decision == 'approve' ? tr('تمت الموافقة على العرض', 'Quote approved') : tr('تم رفض العرض', 'Quote rejected')), backgroundColor: decision == 'approve' ? const Color(0xFF16A34A) : C2C.red));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
