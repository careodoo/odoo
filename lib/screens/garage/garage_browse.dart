import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_home.dart' show kGrgNavy, kGrgBg, kGrgInk, kGrgGrey, grgNum;

Color _partColor(String s) {
  switch (s) {
    case 'in_stock':
      return const Color(0xFF16A34A);
    case 'installed':
      return const Color(0xFF2563EB);
    case 'damaged':
      return const Color(0xFFE08A00);
    case 'disposed':
      return const Color(0xFFDC3030);
    default:
      return kGrgGrey;
  }
}

/// قائمة عامة قابلة للبحث مبنية من دالة تحميل + باني بطاقة.
class _GrgList extends StatefulWidget {
  const _GrgList({required this.title, required this.loader, required this.card, this.searchable = true});
  final String title;
  final Future<List> Function(String q) loader;
  final Widget Function(Map<String, dynamic> row) card;
  final bool searchable;
  @override
  State<_GrgList> createState() => _GrgListState();
}

class _GrgListState extends State<_GrgList> {
  List _rows = const [];
  bool _loading = true;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await widget.loader(_q);
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(widget.title),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: Column(children: [
        if (widget.searchable)
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
            child: TextField(
              onSubmitted: (v) {
                _q = v;
                _load();
              },
              style: const TextStyle(fontSize: 13),
              decoration: InputDecoration(
                  hintText: tr('بحث…', 'Search…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 19),
                  isDense: true,
                  filled: true,
                  fillColor: const Color(0xFFF1F4F8),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
            ),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا سجلات', 'No records'), style: const TextStyle(color: kGrgGrey)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 24),
                        itemCount: _rows.length,
                        itemBuilder: (_, i) => widget.card(Map<String, dynamic>.from(_rows[i] as Map)),
                      ),
                    ),
        ),
      ]),
    );
  }
}

Widget _tile(BuildContext ctx, {required String title, String? sub, String? trail, Color? trailColor, List<Widget>? chips, VoidCallback? onTap}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(13),
      child: InkWell(
        borderRadius: BorderRadius.circular(13),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(children: [
            Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk, fontSize: 13.5)),
              if (sub != null && sub.isNotEmpty) ...[
                const SizedBox(height: 3),
                Text(sub, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kGrgGrey, fontSize: 11.5)),
              ],
              if (chips != null && chips.isNotEmpty) ...[const SizedBox(height: 6), Wrap(spacing: 6, runSpacing: 5, children: chips)],
            ])),
            if (trail != null)
              Text(trail, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: trailColor ?? kGrgInk)),
          ]),
        ),
      ),
    ),
  );
}

Widget _miniChip(String t, Color c) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
      child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 10.5)),
    );

class GarageVehiclesScreen extends StatelessWidget {
  const GarageVehiclesScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return _GrgList(
      title: tr('المركبات', 'Vehicles'),
      loader: (q) => api.grgVehicles(q: q.isEmpty ? null : q),
      card: (r) => _tile(context,
          title: '${r['name']}',
          sub: '${r['plate'] ?? ''}',
          chips: [
            if ('${r['tire_size'] ?? ''}'.isNotEmpty) _miniChip('🛞 ${r['tire_size']}', const Color(0xFF0E8A8A)),
            if ('${r['battery'] ?? ''}'.isNotEmpty) _miniChip('🔋 ${r['battery']}', const Color(0xFFE08A00)),
            _miniChip('${grgNum(r['odometer'])} كم', const Color(0xFF334155)),
          ],
          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => GarageVehicleDetail(id: r['id'] as int)))),
    );
  }
}

class GarageVehicleDetail extends StatefulWidget {
  const GarageVehicleDetail({super.key, required this.id});
  final int id;
  @override
  State<GarageVehicleDetail> createState() => _GarageVehicleDetailState();
}

class _GarageVehicleDetailState extends State<GarageVehicleDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map<String, dynamic>? _d;
  bool _loading = true;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _api.grgVehicle(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text('${d?['name'] ?? tr('المركبة', 'Vehicle')}')),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
          : d == null
              ? Center(child: Text(tr('تعذّر التحميل', 'Load failed'), style: const TextStyle(color: kGrgGrey)))
              : ListView(padding: const EdgeInsets.all(14), children: [
                  _box(tr('المواصفات', 'Specs'), [
                    _kv(tr('اللوحة', 'Plate'), '${d['plate'] ?? '—'}'),
                    _kv(tr('العدّاد', 'Odometer'), '${grgNum(d['odometer'])} كم'),
                    _kv(tr('مقاس الإطار', 'Tire size'), '${d['tire_size'] ?? '—'}'),
                    _kv(tr('عدد الإطارات', 'Tire count'), '${d['tire_count'] ?? 0}'),
                    _kv(tr('البطارية', 'Battery'), '${d['battery'] ?? '—'}'),
                    _kv(tr('الزيت', 'Oil'), '${d['oil_type'] ?? '—'}'),
                    _kv(tr('دورة التزييت', 'Service km'), '${grgNum(d['service_km'])} كم'),
                  ]),
                  const SizedBox(height: 14),
                  _box(tr('الإطارات', 'Tires'),
                      ((d['tires'] as List?) ?? const []).map((x) {
                        final t = Map<String, dynamic>.from(x as Map);
                        return _kv('${t['position']} ${t['label'] ?? ''}', '${t['size'] ?? ''} · ${t['serial'] ?? ''} · ${t['tread'] ?? 0}%');
                      }).toList()),
                  const SizedBox(height: 14),
                  _box(tr('آخر الصيانات', 'Recent services'),
                      ((d['services'] as List?) ?? const []).map((x) {
                        final s = Map<String, dynamic>.from(x as Map);
                        return _kv('${s['date']}', '${s['state_label']} · ${grgNum(s['cost'])}');
                      }).toList()),
                ]),
    );
  }

  Widget _box(String title, List<Widget> rows) => Container(
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(padding: const EdgeInsets.fromLTRB(14, 12, 14, 4), child: Text(title, style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy, fontSize: 13.5))),
        if (rows.isEmpty) Padding(padding: const EdgeInsets.all(14), child: Text(tr('لا يوجد', 'None'), style: const TextStyle(color: kGrgGrey, fontSize: 12))),
        ...rows,
        const SizedBox(height: 6),
      ]));

  Widget _kv(String k, String v) => Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 120, child: Text(k, style: const TextStyle(color: kGrgGrey, fontSize: 12))),
        Expanded(child: Text(v, style: const TextStyle(color: kGrgInk, fontWeight: FontWeight.w700, fontSize: 12.5))),
      ]));
}

class GarageTechniciansScreen extends StatelessWidget {
  const GarageTechniciansScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return _GrgList(
      title: tr('الفنّيون', 'Technicians'),
      searchable: false,
      loader: (_) => api.grgTechnicians(),
      card: (r) => _tile(context,
          title: '${r['name']}',
          sub: '${r['phone'] ?? ''}',
          chips: [
            if ('${r['specialty'] ?? ''}'.isNotEmpty) _miniChip('${r['specialty']}', const Color(0xFF7C3AED)),
            _miniChip('${r['type']}', const Color(0xFF334155)),
            _miniChip('${r['jobs']} عمل', const Color(0xFF0E8A8A)),
          ]),
    );
  }
}

class GarageItemsScreen extends StatelessWidget {
  const GarageItemsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return _GrgList(
      title: tr('الأصناف', 'Items'),
      loader: (q) => api.grgItems(q: q.isEmpty ? null : q),
      card: (r) => _tile(context,
          title: '${r['name']}',
          sub: '${r['category']}${'${r['size'] ?? ''}'.isNotEmpty ? ' · ${r['size']}' : ''}',
          trail: grgNum(r['in_stock']),
          trailColor: ((r['low_stock'] == true)) ? const Color(0xFFDC3030) : const Color(0xFF16A34A),
          chips: [
            _miniChip('${tr('بالمخزن', 'Stock')} ${grgNum(r['in_stock'])}', const Color(0xFF16A34A)),
            _miniChip('${tr('بالسيارات', 'Installed')} ${grgNum(r['installed'])}', const Color(0xFF2563EB)),
            _miniChip('${tr('تالف', 'Damaged')} ${grgNum(r['damaged'])}', const Color(0xFFE08A00)),
            _miniChip('${tr('متلف', 'Disposed')} ${grgNum(r['disposed'])}', const Color(0xFFDC3030)),
          ]),
    );
  }
}

class GaragePartsScreen extends StatelessWidget {
  const GaragePartsScreen({super.key, this.state, required this.title, required this.titleEn});
  final String? state;
  final String title;
  final String titleEn;
  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return _GrgList(
      title: tr(title, titleEn),
      loader: (q) => api.grgParts(state: state, q: q.isEmpty ? null : q),
      card: (r) => _tile(context,
          title: '${r['name']}',
          sub: '${r['serial'] ?? ''}${'${r['vehicle'] ?? ''}'.isNotEmpty ? ' · ${r['vehicle']}' : ''}',
          trail: grgNum(r['cost']),
          chips: [
            _miniChip('${r['state_label']}', _partColor('${r['state']}')),
            if ('${r['condition'] ?? ''}'.isNotEmpty) _miniChip('${r['condition']}', kGrgGrey),
            if ('${r['store'] ?? ''}'.isNotEmpty) _miniChip('${r['store']}', const Color(0xFF334155)),
          ]),
    );
  }
}

class GarageDisposalsScreen extends StatelessWidget {
  const GarageDisposalsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    return _GrgList(
      title: tr('لجان الإتلاف', 'Disposals'),
      searchable: false,
      loader: (_) => api.grgDisposals(),
      card: (r) => _tile(context,
          title: '${r['name']}',
          sub: '${r['reason'] ?? ''} · ${r['date']}',
          trail: '${r['lines']}',
          chips: [
            _miniChip('${r['state_label']}', r['state'] == 'approved' ? const Color(0xFF16A34A) : kGrgGrey),
            if (((r['scrap_total'] as num?)?.toDouble() ?? 0) > 0) _miniChip('${tr('سكراب', 'Scrap')} ${grgNum(r['scrap_total'])}', const Color(0xFF7A1020)),
          ]),
    );
  }
}
