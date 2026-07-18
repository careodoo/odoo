import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'pdf_report_screen.dart';
import 'in_app_map_screen.dart';
import 'client_workorders_screen.dart';

/// A professional facility page: a stats header, a clickable building → floor →
/// location tree, and a location sheet showing its QR (viewable + printable),
/// live stats, work orders and assets.
class FacilityDetailScreen extends StatefulWidget {
  const FacilityDetailScreen({super.key, required this.facilityId, required this.name});
  final int facilityId;
  final String name;
  @override
  State<FacilityDetailScreen> createState() => _FacilityDetailScreenState();
}

class _FacilityDetailScreenState extends State<FacilityDetailScreen> {
  late Future<Map<String, dynamic>> _future;
  String _q = '';

  static const _accent = Color(0xFFC0392B);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.clientFacility(widget.facilityId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(widget.name, overflow: TextOverflow.ellipsis),
        backgroundColor: _accent, foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.map_rounded), tooltip: tr('الموقع على الخريطة', 'On the map'),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
                  InAppMapScreen(query: widget.name, title: widget.name)))),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey)));
          final d = snap.data!;
          final buildings = ((d['buildings'] as List?) ?? const []).cast<Map>();
          final locations = ((d['locations'] as List?) ?? const []).cast<Map>();
          final stats = (d['stats'] as Map?) ?? const {};
          final shown = _q.isEmpty ? locations
              : locations.where((l) => '${l['name']}${l['code']}${l['building'] ?? ''}${l['floor'] ?? ''}'
                  .toLowerCase().contains(_q.toLowerCase())).toList();
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            _statsHeader(d, stats),
            if (d['address'] != null) ...[
              const SizedBox(height: 10),
              _addressCard('${d['address']}'),
            ],
            const SizedBox(height: 14),
            if (buildings.isNotEmpty) ...[
              _sectionTitle(Icons.business_rounded, tr('المباني والأدوار', 'Buildings & floors')),
              const SizedBox(height: 8),
              ...buildings.map(_buildingCard),
              const SizedBox(height: 14),
            ],
            _sectionTitle(Icons.qr_code_2_rounded, tr('المواقع (QR) — ${locations.length}', 'Locations (QR) — ${locations.length}')),
            const SizedBox(height: 8),
            if (locations.length > 5) ...[
              TextField(
                onChanged: (v) => setState(() => _q = v),
                decoration: InputDecoration(
                  hintText: tr('ابحث عن موقع…', 'Search a location…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  isDense: true, filled: true, fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                ),
              ),
              const SizedBox(height: 8),
            ],
            ...shown.map(_locationCard),
          ]);
        },
      ),
    );
  }

  Widget _statsHeader(Map d, Map s) => CustomPaint(
        painter: const BrandPattern(opacity: 0.06),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: _accent.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 6))],
          ),
          child: Column(children: [
            Row(children: [
              _kpi('${s['buildings'] ?? 0}', tr('مبنى', 'Buildings'), Icons.business_rounded),
              _kdiv(),
              _kpi('${s['floors'] ?? 0}', tr('دور', 'Floors'), Icons.layers_rounded),
              _kdiv(),
              _kpi('${s['locations'] ?? 0}', tr('موقع', 'Locations'), Icons.pin_drop_rounded),
              _kdiv(),
              _kpi('${s['assets'] ?? 0}', tr('أصل', 'Assets'), Icons.precision_manufacturing_rounded),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: _band(Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'),
                  '${s['workorders'] ?? 0}', () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => const ClientWorkOrdersScreen(initialFilter: 'all'))))),
              const SizedBox(width: 8),
              Expanded(child: _band(Icons.pending_actions_rounded, tr('مفتوحة', 'Open'),
                  '${s['open_workorders'] ?? 0}', () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => const ClientWorkOrdersScreen(initialFilter: 'open'))))),
              const SizedBox(width: 8),
              Expanded(child: _band(Icons.verified_user_rounded, tr('نقاط تفتيش', 'Checkpoints'),
                  '${s['checkpoints'] ?? 0}', null)),
            ]),
          ]),
        ),
      );

  Widget _kpi(String v, String l, IconData ic) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 17),
        const SizedBox(height: 4),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _kdiv() => Container(width: 1, height: 34, color: Colors.white.withValues(alpha: 0.2));

  Widget _band(IconData ic, String l, String v, VoidCallback? onTap) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 6),
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(11)),
          child: Column(children: [
            Icon(ic, color: Colors.white, size: 15),
            const SizedBox(height: 3),
            Text(v, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900)),
            Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 8.5, fontWeight: FontWeight.w600)),
          ]),
        ),
      );

  Widget _addressCard(String addr) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          const Icon(Icons.place_rounded, color: _accent, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(addr, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600))),
        ]),
      );

  Widget _sectionTitle(IconData ic, String t) => Row(children: [
        Icon(ic, size: 17, color: _accent),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
      ]);

  Widget _buildingCard(Map b) {
    final floors = ((b['floor_list'] as List?) ?? const []).cast<Map>();
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 6, offset: const Offset(0, 2))]),
      clipBehavior: Clip.antiAlias,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          leading: Container(
            width: 42, height: 42, alignment: Alignment.center,
            decoration: BoxDecoration(color: _navy.withValues(alpha: 0.09), borderRadius: BorderRadius.circular(12)),
            child: const Icon(Icons.apartment_rounded, color: _navy, size: 22),
          ),
          title: Text('${b['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
          subtitle: Text(tr('${b['floors']} دور · ${b['locations']} موقع', '${b['floors']} floors · ${b['locations']} locations'),
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
          children: [
            for (final f in floors)
              ListTile(
                dense: true,
                leading: const Icon(Icons.layers_rounded, size: 18, color: Color(0xFF0891B2)),
                title: Text('${f['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                trailing: Text(tr('${f['locations']} موقع', '${f['locations']} loc'),
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _locationCard(Map l) {
    final checkpoint = l['checkpoint'] == true;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 5, offset: const Offset(0, 2))]),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openLocation(l['id'] as int, '${l['name']}'),
        child: Padding(
          padding: const EdgeInsets.all(11),
          child: Row(children: [
            Container(
              width: 42, height: 42, alignment: Alignment.center,
              decoration: BoxDecoration(color: (checkpoint ? const Color(0xFF16A34A) : _accent).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12)),
              child: Icon(checkpoint ? Icons.verified_user_rounded : Icons.qr_code_2_rounded,
                  color: checkpoint ? const Color(0xFF16A34A) : _accent, size: 22),
            ),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${l['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
              const SizedBox(height: 2),
              Text([
                if (l['code'] != null) '${l['code']}',
                if (l['building'] != null) '${l['building']}',
                if (l['floor'] != null) '${l['floor']}',
                if (l['type_label'] != null) '${l['type_label']}',
              ].join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
            ])),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              if (((l['wo_count'] ?? 0) as int) > 0)
                Text(tr('${l['wo_count']} أمر', '${l['wo_count']} WO'), style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
              if (((l['asset_count'] ?? 0) as int) > 0)
                Text(tr('${l['asset_count']} أصل', '${l['asset_count']} asset'), style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
            ]),
            const Icon(Icons.chevron_left_rounded, color: Colors.grey, size: 20),
          ]),
        ),
      ),
    );
  }

  void _openLocation(int id, String name) {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.96,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: context.read<AuthProvider>().api.clientLocation(id),
          builder: (_, snap) {
            final d = snap.data ?? const {};
            final st = (d['stats'] as Map?) ?? const {};
            final wos = ((d['workorders'] as List?) ?? const []).cast<Map>();
            final assets = ((d['assets'] as List?) ?? const []).cast<Map>();
            return Container(
              decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
              clipBehavior: Clip.antiAlias,
              child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
                  decoration: BoxDecoration(gradient: LinearGradient(
                      colors: [_navy, Color.lerp(_navy, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                  child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                      if (d['code'] != null) Text('${d['code']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5, letterSpacing: 1)),
                      if (d['building'] != null || d['floor'] != null)
                        Text('${d['building'] ?? ''}${d['floor'] != null ? ' · ${d['floor']}' : ''}',
                            style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 11)),
                    ])),
                    if (d['checkpoint'] == true)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                        decoration: BoxDecoration(color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(20)),
                        child: Text(tr('نقطة تفتيش', 'Checkpoint'), style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900)),
                      ),
                  ]),
                ),
                if (snap.connectionState == ConnectionState.waiting)
                  const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: _navy)))
                else Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    // QR image
                    if (d['qr_image'] != null)
                      Center(child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 8)]),
                        child: Column(children: [
                          Image.network('${d['qr_image']}', width: 150, height: 150, fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const SizedBox(width: 150, height: 150,
                                  child: Icon(Icons.qr_code_2_rounded, size: 90, color: Colors.grey))),
                          const SizedBox(height: 4),
                          Text('${d['code'] ?? ''}', style: TextStyle(fontSize: 11, letterSpacing: 2, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
                        ]),
                      )),
                    const SizedBox(height: 12),
                    // stats
                    Row(children: [
                      _lStat('${st['workorders'] ?? 0}', tr('أوامر عمل', 'Work orders'), const Color(0xFF2563EB)),
                      const SizedBox(width: 8),
                      _lStat('${st['open_workorders'] ?? 0}', tr('مفتوحة', 'Open'), const Color(0xFFF7A23B)),
                      const SizedBox(width: 8),
                      _lStat('${st['done_workorders'] ?? 0}', tr('منجزة', 'Done'), const Color(0xFF16A34A)),
                      const SizedBox(width: 8),
                      _lStat('${st['assets'] ?? 0}', tr('أصول', 'Assets'), const Color(0xFF0891B2)),
                    ]),
                    const SizedBox(height: 14),
                    // print QR
                    SizedBox(width: double.infinity, child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(foregroundColor: _navy, side: const BorderSide(color: _navy),
                          padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                        title: tr('ملصق QR للموقع', 'Location QR label'), path: '/cafm/location/$id/qr', fileName: 'location-qr-$id.pdf'))),
                      icon: const Icon(Icons.print_rounded, size: 18),
                      label: Text(tr('طباعة ملصق QR', 'Print QR label'), style: const TextStyle(fontWeight: FontWeight.w800)),
                    )),
                    if (wos.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      _sectionTitle(Icons.assignment_rounded, tr('أوامر العمل (${wos.length})', 'Work orders (${wos.length})')),
                      const SizedBox(height: 8),
                      ...wos.map((w) => Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.all(11),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                            child: Row(children: [
                              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${w['title'] ?? w['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                                Text('${w['name']} · ${w['date'] ?? ''}', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
                              ])),
                              Text('${w['state_label'] ?? w['state']}', style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
                            ]),
                          )),
                    ],
                    if (assets.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      _sectionTitle(Icons.precision_manufacturing_rounded, tr('الأصول (${assets.length})', 'Assets (${assets.length})')),
                      const SizedBox(height: 8),
                      ...assets.map((a) => Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.all(11),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                            child: Row(children: [
                              const Icon(Icons.precision_manufacturing_rounded, size: 16, color: Color(0xFF0891B2)),
                              const SizedBox(width: 8),
                              Expanded(child: Text('${a['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5))),
                              if (a['code'] != null) Text('${a['code']}', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
                            ]),
                          )),
                    ],
                    const SizedBox(height: 8),
                  ]),
                ),
              ]),
            );
          },
        ),
      ),
    );
  }

  Widget _lStat(String v, String l, Color c) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
          child: Column(children: [
            Text(v, style: TextStyle(color: c, fontSize: 17, fontWeight: FontWeight.w900)),
            Text(l, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                style: TextStyle(fontSize: 8.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
          ]),
        ),
      );
}
