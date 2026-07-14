import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client-facing facade-cleaning suite: overview + elevation zones (schedule
/// compliance) and height-work permits (wind-lockout safety), scoped to the
/// client's facilities. Read-only visibility into façade ops & site safety.
class ClientFacadeScreen extends StatefulWidget {
  const ClientFacadeScreen({super.key});
  @override
  State<ClientFacadeScreen> createState() => _ClientFacadeScreenState();
}

class _ClientFacadeScreenState extends State<ClientFacadeScreen> {
  Map<String, dynamic>? _summary;
  String _kind = 'permits';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ['permits', '🦺 التصاريح', 'Permits'],
    ['zones', '🧱 الواجهات', 'Elevations'],
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _loadKind('permits');
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientFacadeSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _loadKind(String k) => setState(() {
        _kind = k;
        _list = context.read<AuthProvider>().api.clientFacade(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    final unsafe = (s?['wind_unsafe'] ?? 0);
    return Scaffold(
      appBar: AppBar(title: Text(tr('غسيل الواجهات', 'Facade cleaning'))),
      body: Column(children: [
        if (s != null && s['available'] == true) ...[
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('🧱', '${s['zones'] ?? 0}', tr('الواجهات', 'Elevations'), const Color(0xFF8B5CF6)),
              _stat('🕒', '${s['zones_due'] ?? 0}', tr('تنظيف مستحقّ', 'Due'), const Color(0xFFE11D48)),
              _stat('🦺', '${s['permits_active'] ?? 0}', tr('تصاريح فعّالة', 'Active permits'), const Color(0xFF0891B2)),
              _stat('💨', '${s['wind_unsafe'] ?? 0}', tr('رياح غير آمنة', 'Wind unsafe'), const Color(0xFFE11D48)),
            ]),
          ),
          Container(
            width: double.infinity,
            margin: const EdgeInsets.fromLTRB(10, 0, 10, 6),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
                color: (unsafe is num && unsafe > 0) ? const Color(0xFFFEF2F2) : const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: (unsafe is num && unsafe > 0) ? const Color(0xFFFECACA) : const Color(0xFFBBF7D0))),
            child: Text(
              (unsafe is num && unsafe > 0)
                  ? '⛔ ${tr('يوجد عمل على ارتفاع بسرعة رياح غير آمنة — العمل موقوف', 'A height-work permit exceeds the safe wind limit — work halted')}'
                  : '✅ ${tr('كل تصاريح الارتفاع ضمن حدود الرياح الآمنة', 'All height-work permits within safe wind limits')}',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: (unsafe is num && unsafe > 0) ? const Color(0xFFE11D48) : const Color(0xFF16A34A)),
            ),
          ),
        ],
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
            for (final k in _kinds)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: ChoiceChip(
                  label: Text(gLang == 'en' ? k[2] : k[1]),
                  selected: _kind == k[0],
                  onSelected: (_) => _loadKind(k[0]),
                ),
              ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records')));
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 132,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  Widget _row(Map r) {
    if (_kind == 'zones') {
      final due = r['is_due'] == true;
      return ListTile(
        leading: const Text('🧱', style: TextStyle(fontSize: 20)),
        title: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${r['facility'] ?? ''} · ${r['method'] ?? ''} · ${r['frequency'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill(due ? tr('مستحقّ', 'Due') : tr('منتظم', 'OK'), due ? const Color(0xFFE11D48) : const Color(0xFF16A34A)),
      );
    }
    // permits
    final safe = r['is_safe'] == true;
    return ListTile(
      leading: Text(safe ? '🦺' : '⛔', style: const TextStyle(fontSize: 20)),
      title: Text('${r['name']} · ${r['zone'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text('${r['method'] ?? ''} · 💨 ${r['wind_speed'] ?? 0}/${r['wind_limit'] ?? 0} · ${r['state_label'] ?? ''}',
          maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: _pill(safe ? tr('آمن', 'Safe') : tr('غير آمن', 'Unsafe'), safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48)),
      onTap: () => _openPermit(r),
    );
  }

  void _openPermit(Map x) {
    final workers = (x['workers'] as List?) ?? [];
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${x['name']}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          _kv(tr('المرفق', 'Facility'), x['facility']),
          _kv(tr('الواجهة', 'Elevation'), x['zone']),
          _kv(tr('الطريقة', 'Method'), x['method']),
          _kv(tr('سرعة الرياح', 'Wind speed'), '${x['wind_speed'] ?? 0} / ${x['wind_limit'] ?? 0} ${tr('كم/س', 'km/h')}'),
          _kv(tr('السلامة', 'Safety'), (x['is_safe'] == true) ? '✅ ${tr('آمن', 'Safe')}' : '⛔ ${tr('غير آمن', 'Unsafe')}'),
          _kv(tr('تقييم المخاطر', 'Risk assessed'), (x['risk_assessed'] == true) ? '✅' : '—'),
          _kv(tr('فحص المعدّات', 'Equipment checked'), (x['equipment_checked'] == true) ? '✅' : '—'),
          _kv(tr('مشرف السلامة', 'Supervisor'), x['supervisor']),
          if (workers.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(tr('العمّال', 'Workers'), style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Wrap(spacing: 6, runSpacing: 6, children: [for (final w in workers) _pill('$w', const Color(0xFF4338CA))]),
          ],
        ]),
      ),
    );
  }

  Widget _kv(String k, dynamic v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 130, child: Text(k, style: const TextStyle(color: Colors.grey))),
          Expanded(child: Text('${v ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );
}
