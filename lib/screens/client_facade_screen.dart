import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/service_ui.dart';
import 'excel_export.dart';
import 'facade_permit_create.dart';

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

  static const _c = Color(0xFF7C3AED);
  String _q = '';
  static const _kinds = <(String, String, IconData)>[
    ('permits', 'التصاريح', Icons.health_and_safety_rounded),
    ('zones', 'الواجهات', Icons.location_city_rounded),
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
        _q = '';
        _list = context.read<AuthProvider>().api.clientFacade(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary ?? const {};
    final label = _kinds.firstWhere((k) => k.$1 == _kind).$2;
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _c, foregroundColor: Colors.white,
        icon: const Icon(Icons.add_moderator_rounded),
        label: Text(tr('إصدار تصريح', 'Issue permit'), style: const TextStyle(fontWeight: FontWeight.w900)),
        onPressed: () async {
          final created = await FacadePermitCreateSheet.open(context);
          if (created == true && mounted) { _loadSummary(); _loadKind('permits'); }
        },
      ),
      appBar: AppBar(
        title: Text(tr('الواجهات', 'Facade')),
        actions: [
          IconButton(icon: const Icon(Icons.grid_on_rounded), tooltip: tr('تصدير Excel', 'Export Excel'),
              onPressed: () => exportExcelFile(context, path: '/cafm/facade/permits/export',
                  fileName: 'facade-permits.xlsx', shareText: tr('تصاريح العمل على الارتفاع', 'Height-work permits'))),
          IconButton(icon: const Icon(Icons.refresh_rounded),
              onPressed: () { _loadSummary(); _loadKind(_kind); }),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async { await _loadSummary(); _loadKind(_kind); },
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          ServiceHero(
            title: tr('الواجهات', 'Facade'),
            subtitle: tr('${s['zones'] ?? 0} واجهة · ${s['permits_total'] ?? 0} تصريح', '${s['zones'] ?? 0} elevations · ${s['permits_total'] ?? 0} permits'),
            icon: Icons.location_city_rounded,
            color: _c,
            stats: [
              (tr('الواجهات', 'elevations'), '${s['zones'] ?? 0}', null),
              (tr('تنظيف مستحقّ', 'due'), '${s['zones_due'] ?? 0}',
                  ((s['zones_due'] ?? 0) as int) > 0 ? const Color(0xFFF59E0B) : null),
              (tr('تصريح فعّال', 'active'), '${s['permits_active'] ?? 0}', null),
              (tr('إجمالي التصاريح', 'permits'), '${s['permits_total'] ?? 0}', null),
              (tr('رياح غير آمنة', 'wind'), '${s['wind_unsafe'] ?? 0}',
                  ((s['wind_unsafe'] ?? 0) as int) > 0 ? const Color(0xFFDC2626) : null),
            ],
            onStatTap: (i) => _loadKind(const ['zones', 'zones', 'permits', 'permits', 'permits'][i]),
          ),
          const SizedBox(height: 12),
          ServiceTabs(kinds: _kinds, current: _kind, onSelect: _loadKind, color: _c),
          const SizedBox(height: 10),
          FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Padding(padding: EdgeInsets.symmetric(vertical: 50),
                    child: Center(child: CircularProgressIndicator()));
              }
              final all = snap.data ?? const [];
              final rows = _q.isEmpty
                  ? all
                  : all.where((r) => (r as Map).values.map((v) => '$v').join(' ').toLowerCase()
                      .contains(_q.toLowerCase())).toList();
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (all.length > 6) ...[
                  TextField(
                    onChanged: (v) => setState(() => _q = v),
                    decoration: InputDecoration(
                      hintText: tr('ابحث في $label…', 'Search $label…'),
                      prefixIcon: const Icon(Icons.search_rounded, size: 19),
                      isDense: true, filled: true,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                MoreList(
                  items: rows,
                  color: _c,
                  header: label,
                  emptyText: tr('لا سجلات في $label.', 'No $label records.'),
                  itemBuilder: (_, r, __) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Material(
                      color: Theme.of(context).cardColor,
                      borderRadius: BorderRadius.circular(12),
                      child: _row(r as Map),
                    ),
                  ),
                ),
              ]);
            },
          ),
        ]),
      ),
    );
  }

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
