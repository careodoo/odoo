import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// A single booking with a visual status timeline and actions.
class C2CBookingDetailScreen extends StatefulWidget {
  const C2CBookingDetailScreen({super.key, required this.booking});
  final Map booking;
  @override
  State<C2CBookingDetailScreen> createState() => _C2CBookingDetailScreenState();
}

class _C2CBookingDetailScreenState extends State<C2CBookingDetailScreen> {
  late Map _b = Map.from(widget.booking);

  static const _flow = ['confirmed', 'assigned', 'in_progress', 'done'];
  static const _flowLabel = {
    'confirmed': ['مؤكّد', 'Confirmed'], 'assigned': ['تم الإسناد', 'Assigned'],
    'in_progress': ['قيد التنفيذ', 'In progress'], 'done': ['منجز', 'Done'],
  };
  static const _flowIcon = {
    'confirmed': Icons.check_circle, 'assigned': Icons.engineering,
    'in_progress': Icons.cleaning_services, 'done': Icons.verified,
  };

  @override
  Widget build(BuildContext context) {
    final st = '${_b['state']}';
    final cancelled = st == 'cancelled';
    final curIdx = _flow.indexOf(st);
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(backgroundColor: C2C.navy, foregroundColor: Colors.white, title: Text('${_b['name']}')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        // header card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
          child: Row(children: [
            Text('${_b['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 36)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_b['service']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              if (_b['package'] != null) Text('${_b['package']}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
              const SizedBox(height: 4),
              Text('${_b['amount']} ${_b['currency'] ?? ''} · ${_b['payment_label'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800, fontSize: 13)),
            ])),
          ]),
        ),
        const SizedBox(height: 16),
        // timeline
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
          child: cancelled
              ? Row(children: [const Icon(Icons.cancel, color: Color(0xFFE11D48)), const SizedBox(width: 10), Text(tr('تم إلغاء هذا الحجز', 'This booking was cancelled'), style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFFE11D48)))])
              : Column(children: [
                  for (int i = 0; i < _flow.length; i++) _step(i, curIdx),
                ]),
        ),
        const SizedBox(height: 16),
        // details
        _infoCard([
          [Icons.event_rounded, tr('الموعد', 'Appointment'), '${_b['visit'] ?? ''}'],
          if (_b['address'] != null) [Icons.location_on_outlined, tr('العنوان', 'Address'), '${_b['area'] ?? ''} ${_b['address']}'],
          if (_b['provider'] != null) [Icons.engineering_outlined, tr('الفنّي', 'Technician'), '${_b['provider']}'],
          if (_b['phone'] != null) [Icons.phone_outlined, tr('الهاتف', 'Phone'), '${_b['phone']}'],
        ]),
        if (_b['rating'] != null && _b['rating'] != false) Padding(padding: const EdgeInsets.only(top: 12), child: Text('${tr('تقييمك', 'Your rating')}: ${'★' * int.parse('${_b['rating']}')}', style: const TextStyle(color: Color(0xFFF5A623), fontSize: 18))),
        const SizedBox(height: 18),
        // actions
        Row(children: [
          Expanded(child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: C2C.navy, padding: const EdgeInsets.symmetric(vertical: 12)),
            onPressed: _rebook, icon: const Icon(Icons.replay_rounded), label: Text(tr('إعادة الحجز', 'Rebook')),
          )),
          if (!cancelled && st != 'done') ...[
            const SizedBox(width: 10),
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: C2C.red, padding: const EdgeInsets.symmetric(vertical: 12)),
              onPressed: _cancel, icon: const Icon(Icons.close_rounded), label: Text(tr('إلغاء', 'Cancel')),
            )),
          ],
        ]),
      ]),
    );
  }

  Widget _step(int i, int curIdx) {
    final done = curIdx >= i && curIdx >= 0;
    final active = curIdx == i;
    final st = _flow[i];
    final color = done ? const Color(0xFF16A34A) : Colors.grey.shade300;
    return IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Column(children: [
          Container(
            width: 34, height: 34,
            decoration: BoxDecoration(color: done ? color : Colors.white, shape: BoxShape.circle, border: Border.all(color: color, width: 2)),
            child: Icon(_flowIcon[st], size: 18, color: done ? Colors.white : Colors.grey),
          ),
          if (i < _flow.length - 1) Expanded(child: Container(width: 2, color: curIdx > i ? const Color(0xFF16A34A) : Colors.grey.shade300)),
        ]),
        const SizedBox(width: 12),
        Padding(
          padding: const EdgeInsets.only(top: 6, bottom: 18),
          child: Text(tr(_flowLabel[st]![0], _flowLabel[st]![1]), style: TextStyle(fontWeight: active ? FontWeight.w900 : FontWeight.w600, color: done ? C2C.navy : Colors.grey, fontSize: 14)),
        ),
      ]),
    );
  }

  Widget _infoCard(List<List<dynamic>> rows) => Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(children: [
          for (final r in rows)
            ListTile(dense: true, leading: Icon(r[0] as IconData, size: 20, color: C2C.navy), title: Text('${r[1]}', style: const TextStyle(fontSize: 12, color: Colors.grey)), subtitle: Text('${r[2]}', style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );

  void _rebook() => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceScreen(serviceId: _b['service_id'] as int)));

  Future<void> _cancel() async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('إلغاء الحجز', 'Cancel booking')),
      content: Text(tr('هل تريد إلغاء هذا الحجز؟', 'Cancel this booking?')),
      actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('لا', 'No'))), ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: C2C.red), onPressed: () => Navigator.pop(ctx, true), child: Text(tr('نعم', 'Yes')))],
    ));
    if (ok != true) return;
    try {
      final r = await context.read<AuthProvider>().api.c2cCancel(_b['id'] as int);
      if (mounted) setState(() => _b = {..._b, 'state': r['state']});
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
