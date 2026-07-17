import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// اشتراكاتي — the customer's subscription requests and their state.
class C2CSubscriptionsScreen extends StatefulWidget {
  const C2CSubscriptionsScreen({super.key});
  @override
  State<C2CSubscriptionsScreen> createState() => _C2CSubscriptionsScreenState();
}

class _C2CSubscriptionsScreenState extends State<C2CSubscriptionsScreen> {
  Future<List<dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.c2cMySubscriptions();

  static const _stateColor = {
    'new': Color(0xFFF59E0B), 'active': Color(0xFF16A34A),
    'paused': Color(0xFF64748B), 'converted': Color(0xFF0891B2),
    'cancelled': Color(0xFFE5484D),
  };

  Future<void> _cancel(Map r) async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('إلغاء الاشتراك', 'Cancel subscription')),
      content: Text(tr('إلغاء الاشتراك في «${r['plan']}»؟', 'Cancel "${r['plan']}"?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('تراجع', 'Back'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: C2C.red),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إلغاء', 'Cancel'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.c2cSubscriptionCancel(r['id'] as int);
      if (mounted) setState(_load);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(
        backgroundColor: C2C.navy, foregroundColor: Colors.white, elevation: 0,
        flexibleSpace: const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
            colors: [Color(0xFF17547F), C2C.navy], begin: Alignment.topRight, end: Alignment.bottomLeft))),
        title: Text(tr('اشتراكاتي', 'My subscriptions')),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const [];
            if (rows.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 120),
                Center(child: Column(children: [
                  Icon(Icons.card_membership_rounded, size: 46, color: Colors.grey.shade300),
                  const SizedBox(height: 10),
                  Text(tr('لا اشتراكات بعد.', 'No subscriptions yet.'),
                      style: TextStyle(color: Colors.grey.shade500)),
                  const SizedBox(height: 4),
                  Text(tr('اختر باقة من الصفحة الرئيسية.', 'Pick a plan from the home page.'),
                      style: TextStyle(color: Colors.grey.shade400, fontSize: 12)),
                ])),
              ]);
            }
            return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
              for (final r in rows) _card(r as Map),
            ]);
          },
        ),
      ),
    );
  }

  Widget _card(Map r) {
    final c = _stateColor['${r['state']}'] ?? Colors.grey;
    return Container(
      margin: const EdgeInsets.only(bottom: 11),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['plan'] ?? '—'}',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: C2C.navy)),
            Text('${r['name']}',
                style: TextStyle(color: Colors.grey.shade500, fontSize: 11)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text('${r['state_label']}',
                style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 11)),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          _chip(Icons.payments_rounded, '${r['price']} KWD'),
          const SizedBox(width: 7),
          _chip(Icons.event_repeat_rounded,
              tr(r['period'] == 'yearly' ? 'سنوي' : (r['period'] == 'quarterly' ? 'ربع سنوي' : 'شهري'),
                 '${r['period']}')),
          if ((r['visits'] ?? 0) > 0) ...[
            const SizedBox(width: 7),
            _chip(Icons.repeat_rounded, tr('${r['visits']} زيارة', '${r['visits']} visits')),
          ],
        ]),
        if (r['created'] != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(tr('طُلب في ${r['created']}', 'Requested ${r['created']}'),
                style: TextStyle(color: Colors.grey.shade400, fontSize: 10)),
          ),
        if (r['can_cancel'] == true) ...[
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: C2C.red, side: BorderSide(color: C2C.red.withValues(alpha: 0.4)),
                padding: const EdgeInsets.symmetric(vertical: 8),
              ),
              icon: const Icon(Icons.cancel_outlined, size: 16),
              label: Text(tr('إلغاء الاشتراك', 'Cancel subscription'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
              onPressed: () => _cancel(r),
            ),
          ),
        ],
      ]),
    );
  }

  Widget _chip(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
            color: C2C.navy.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 12, color: C2C.navy),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C2C.navy)),
        ]),
      );
}
