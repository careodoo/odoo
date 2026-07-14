import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

class C2CBookingsScreen extends StatefulWidget {
  const C2CBookingsScreen({super.key});
  @override
  State<C2CBookingsScreen> createState() => _C2CBookingsScreenState();
}

class _C2CBookingsScreenState extends State<C2CBookingsScreen> {
  Future<List<dynamic>>? _list;

  static const _stC = {
    'draft': Color(0xFF94A3B8), 'confirmed': Color(0xFF3B82F6), 'assigned': Color(0xFF6366F1),
    'in_progress': Color(0xFFF59E0B), 'done': Color(0xFF16A34A), 'cancelled': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _list = context.read<AuthProvider>().api.c2cBookings());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(backgroundColor: C2C.navy, foregroundColor: Colors.white, title: Text(tr('حجوزاتي', 'My bookings'))),
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
                const Center(child: Text('🗓️', style: TextStyle(fontSize: 60))),
                Center(child: Padding(padding: const EdgeInsets.all(12), child: Text(tr('لا حجوزات بعد', 'No bookings yet'), style: const TextStyle(color: Colors.grey, fontSize: 16)))),
              ]);
            }
            return ListView(padding: const EdgeInsets.all(12), children: [for (final b in rows) _card(b as Map)]);
          },
        ),
      ),
    );
  }

  Widget _card(Map b) {
    final st = '${b['state']}';
    final c = _stC[st] ?? Colors.grey;
    final canCancel = st != 'done' && st != 'cancelled';
    final canRate = st == 'done' && (b['rating'] == null || b['rating'] == false);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: const BorderRadius.vertical(top: Radius.circular(16))),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(children: [
            Text('${b['category_icon'] ?? '🧩'} ', style: const TextStyle(fontSize: 16)),
            Text('${b['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            const Spacer(),
            Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3), decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)), child: Text('${b['state_label']}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800))),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${b['service']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            if (b['package'] != null) Text('${b['package']}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
            const SizedBox(height: 8),
            _kv(Icons.event_rounded, '${b['visit'] ?? ''}'),
            if (b['address'] != null) _kv(Icons.location_on_outlined, '${b['area'] ?? ''} ${b['address']}'),
            if (b['provider'] != null) _kv(Icons.engineering_outlined, '${b['provider']}'),
            _kv(Icons.payments_outlined, '${b['amount']} ${b['currency'] ?? ''} · ${b['payment_method']} · ${b['payment_label']}'),
            if (b['rating'] != null && b['rating'] != false) Padding(padding: const EdgeInsets.only(top: 6), child: Text('★' * int.parse('${b['rating']}'), style: const TextStyle(color: Color(0xFFF5A623), fontSize: 16))),
            if (canCancel || canRate) ...[
              const Divider(height: 20),
              Row(children: [
                if (canRate)
                  Expanded(child: OutlinedButton.icon(onPressed: () => _rate(b['id'] as int), icon: const Icon(Icons.star_rounded, color: Color(0xFFF5A623)), label: Text(tr('قيّم الخدمة', 'Rate')))),
                if (canRate && canCancel) const SizedBox(width: 10),
                if (canCancel)
                  Expanded(child: OutlinedButton.icon(style: OutlinedButton.styleFrom(foregroundColor: C2C.red), onPressed: () => _cancel(b['id'] as int), icon: const Icon(Icons.close_rounded), label: Text(tr('إلغاء', 'Cancel')))),
              ]),
            ],
          ]),
        ),
      ]),
    );
  }

  Widget _kv(IconData ic, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 15, color: Colors.grey),
          const SizedBox(width: 6),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 12.5))),
        ]),
      );

  Future<void> _cancel(int id) async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('إلغاء الحجز', 'Cancel booking')),
      content: Text(tr('هل تريد إلغاء هذا الحجز؟', 'Cancel this booking?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('لا', 'No'))),
        ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: C2C.red), onPressed: () => Navigator.pop(ctx, true), child: Text(tr('نعم، إلغاء', 'Yes'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.c2cCancel(id);
      if (!mounted) return;
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _rate(int id) async {
    int stars = 5;
    final fb = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => StatefulBuilder(
      builder: (ctx, setSt) => AlertDialog(
        title: Text(tr('قيّم الخدمة', 'Rate service')),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (int i = 1; i <= 5; i++)
              IconButton(onPressed: () => setSt(() => stars = i), icon: Icon(i <= stars ? Icons.star_rounded : Icons.star_border_rounded, color: const Color(0xFFF5A623), size: 32)),
          ]),
          TextField(controller: fb, decoration: InputDecoration(hintText: tr('ملاحظاتك (اختياري)', 'Feedback (optional)'), border: const OutlineInputBorder()), maxLines: 2),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال', 'Submit'))),
        ],
      ),
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.c2cRate(id, stars, feedback: fb.text);
      if (!mounted) return;
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
