import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import '../core/geo.dart';

/// Live security positioning: every premise on an interactive OpenStreetMap
/// (geocoded from its name/address — no GPS field needed), each pin colored by
/// its security health (coverage + open incidents). Tapping a pin opens its
/// coverage sheet: patrol checkpoints with live status, guards on duty, and
/// incidents. A ranked list underneath mirrors the map for quick scanning.
class SecurityPositioningScreen extends StatefulWidget {
  const SecurityPositioningScreen({super.key});
  @override
  State<SecurityPositioningScreen> createState() => _SecurityPositioningScreenState();
}

class _SecurityPositioningScreenState extends State<SecurityPositioningScreen> {
  Future<Map<String, dynamic>>? _future;
  final Map<int, LatLng> _coords = {};
  final _mapController = MapController();
  bool _geocoding = false;
  LatLng? _myLoc;

  static const _navy = Color(0xFF0E3A5F);
  static const _kwCenter = LatLng(29.3759, 47.9774);
  static const _health = {
    'good': Color(0xFF16A34A), 'warn': Color(0xFFF7A23B), 'risk': Color(0xFFE5484D),
  };

  @override
  void initState() {
    super.initState();
    _future = _loadAndGeocode();
    Geo.current().then((l) { if (mounted && l != null) setState(() => _myLoc = l); });
  }

  Future<Map<String, dynamic>> _loadAndGeocode() async {
    final d = await context.read<AuthProvider>().api.clientSecurityPositioning();
    final prem = ((d['premises'] as List?) ?? const []).cast<Map>();
    // geocode premises (best-effort, sequential to respect Nominatim rate limits)
    _geocoding = true;
    for (final p in prem) {
      final q = '${p['name'] ?? ''} ${p['address'] ?? ''} الكويت'.trim();
      try {
        final uri = Uri.parse('https://nominatim.openstreetmap.org/search'
            '?q=${Uri.encodeQueryComponent(q)}&format=json&limit=1&countrycodes=kw');
        final res = await http.get(uri, headers: {'User-Agent': 'CareMobile/1.0 (care-kw.com)'});
        if (res.statusCode == 200) {
          final list = jsonDecode(res.body) as List;
          if (list.isNotEmpty) {
            final m = list.first as Map;
            _coords[p['id'] as int] = LatLng(double.parse('${m['lat']}'), double.parse('${m['lon']}'));
          }
        }
      } catch (_) {}
      if (mounted) setState(() {});
    }
    _geocoding = false;
    if (mounted) setState(() {});
    return d;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(tr('خريطة تموضع الأمن', 'Security positioning')),
        backgroundColor: _navy, foregroundColor: Colors.white,
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _navy));
          }
          final d = snap.data ?? const {};
          if (d['available'] == false) {
            return Center(child: Text(tr('خدمة الأمن غير مفعّلة', 'Security not enabled'), style: const TextStyle(color: Colors.grey)));
          }
          final prem = ((d['premises'] as List?) ?? const []).cast<Map>();
          if (prem.isEmpty) {
            return Center(child: Text(tr('لا مواقع أمنية', 'No security premises'), style: const TextStyle(color: Colors.grey)));
          }
          final markers = <Marker>[
            for (final p in prem)
              if (_coords[p['id']] != null)
                Marker(
                  point: _coords[p['id']]!, width: 44, height: 54,
                  child: GestureDetector(
                    onTap: () => _openPremise(p),
                    child: _pin(p),
                  ),
                ),
            if (_myLoc != null) Geo.meMarker(_myLoc!),
          ];
          final center = _coords.values.isNotEmpty ? _coords.values.first : _kwCenter;
          return Column(children: [
            // ===== the map =====
            SizedBox(
              height: 300,
              child: Stack(children: [
                FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(initialCenter: center, initialZoom: 11),
                  children: [
                    TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.care.app', maxZoom: 19),
                    MarkerLayer(markers: markers),
                    const RichAttributionWidget(attributions: [TextSourceAttribution('OpenStreetMap contributors')]),
                  ],
                ),
                if (_geocoding)
                  Positioned(top: 10, right: 10, child: _Chip(text: tr('تحديد المواقع…', 'Locating…'))),
                // coverage legend
                Positioned(left: 10, bottom: 10, child: _legend()),
                // زر «موقعي»: يمركز الخريطة على موقع المستخدم
                Positioned(right: 10, bottom: 10, child: FloatingActionButton.small(
                  heroTag: 'pos_myloc', backgroundColor: Colors.white, foregroundColor: const Color(0xFF1A73E8),
                  onPressed: () async {
                    var l = _myLoc ?? await Geo.current();
                    if (l == null) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر تحديد موقعك — فعّل خدمة الموقع والإذن', 'Could not get your location — enable location & permission')))); return; }
                    if (mounted) setState(() => _myLoc = l);
                    _mapController.move(l, 15);
                  },
                  child: const Icon(Icons.my_location_rounded, size: 20),
                )),
              ]),
            ),
            // ===== ranked list =====
            Expanded(child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              _overallBar(prem),
              const SizedBox(height: 10),
              ...(prem.toList()..sort((a, b) => _rank(a).compareTo(_rank(b)))).map(_premiseCard),
            ])),
          ]);
        },
      ),
    );
  }

  int _rank(Map p) => {'risk': 0, 'warn': 1, 'good': 2}[p['health']] ?? 3;

  Widget _pin(Map p) {
    final c = _health[p['health']] ?? _navy;
    final g = (p['stats']?['guards'] ?? 0) as int;
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: c.withValues(alpha: 0.5), blurRadius: 6)]),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.shield_rounded, color: Colors.white, size: 12),
          const SizedBox(width: 3),
          Text('$g', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
        ]),
      ),
      Icon(Icons.arrow_drop_down_rounded, color: c, size: 20),
    ]);
  }

  Widget _legend() => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.92), borderRadius: BorderRadius.circular(10)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          for (final e in const [('good', 'مؤمّن'), ('warn', 'انتباه'), ('risk', 'خطر')]) ...[
            Container(width: 9, height: 9, decoration: BoxDecoration(color: _health[e.$1], shape: BoxShape.circle)),
            const SizedBox(width: 3),
            Text(tr(e.$2, e.$1), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
            const SizedBox(width: 8),
          ],
        ]),
      );

  Widget _overallBar(List<Map> prem) {
    final guards = prem.fold<int>(0, (s, p) => s + ((p['stats']?['guards'] ?? 0) as int));
    final overdue = prem.fold<int>(0, (s, p) => s + ((p['stats']?['overdue'] ?? 0) as int));
    final inc = prem.fold<int>(0, (s, p) => s + ((p['stats']?['incidents_open'] ?? 0) as int));
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.06),
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_navy, Color.lerp(_navy, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          _o('${prem.length}', tr('موقع', 'Premises'), Icons.location_city_rounded),
          _od(), _o('$guards', tr('حارس بالخدمة', 'Guards on duty'), Icons.shield_rounded),
          _od(), _o('$overdue', tr('نقاط متأخرة', 'Overdue points'), Icons.timer_off_rounded),
          _od(), _o('$inc', tr('بلاغ مفتوح', 'Open incidents'), Icons.report_rounded),
        ]),
      ),
    );
  }

  Widget _o(String v, String l, IconData ic) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white70, size: 16),
        const SizedBox(height: 3),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 8.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _od() => Container(width: 1, height: 32, color: Colors.white.withValues(alpha: 0.2));

  Widget _premiseCard(Map p) {
    final c = _health[p['health']] ?? _navy;
    final s = (p['stats'] as Map?) ?? const {};
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 3))]),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openPremise(p),
        child: Row(children: [
          Container(width: 5, height: 78, color: c),
          Expanded(child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${p['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text(tr('تغطية ${s['coverage'] ?? 0}%', '${s['coverage'] ?? 0}% cover'),
                      style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w900)),
                ),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: [
                _chip(Icons.shield_rounded, tr('${s['guards'] ?? 0} حارس', '${s['guards'] ?? 0} guards'), const Color(0xFF16A34A)),
                _chip(Icons.qr_code_scanner_rounded, tr('${s['checkpoints'] ?? 0} نقطة', '${s['checkpoints'] ?? 0} points'), const Color(0xFF0891B2)),
                if (((s['overdue'] ?? 0) as int) > 0)
                  _chip(Icons.timer_off_rounded, tr('${s['overdue']} متأخرة', '${s['overdue']} overdue'), const Color(0xFFF7A23B)),
                if (((s['incidents_open'] ?? 0) as int) > 0)
                  _chip(Icons.report_rounded, tr('${s['incidents_open']} بلاغ', '${s['incidents_open']} incidents'), const Color(0xFFE5484D)),
              ]),
            ]),
          )),
          Icon(_coords[p['id']] != null ? Icons.map_rounded : Icons.chevron_left_rounded,
              color: Colors.grey.shade400, size: 20),
          const SizedBox(width: 8),
        ]),
      ),
    );
  }

  Widget _chip(IconData ic, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 12, color: c),
          const SizedBox(width: 4),
          Text(t, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: c)),
        ]),
      );

  void _openPremise(Map p) {
    // recenter the map on the premise if we geocoded it
    final ll = _coords[p['id']];
    if (ll != null) _mapController.move(ll, 15);
    final c = _health[p['health']] ?? _navy;
    final cps = ((p['checkpoints'] as List?) ?? const []).cast<Map>();
    final guards = ((p['guards_on_duty'] as List?) ?? const []).cast<Map>();
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.7, maxChildSize: 0.95,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Row(children: [
                const Icon(Icons.shield_rounded, color: Colors.white, size: 26),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${p['name']}', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                  if (p['address'] != null) Text('${p['address']}'.replaceAll('\n', '، '),
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
                ])),
                Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                    child: Text(tr('تغطية ${p['stats']?['coverage'] ?? 0}%', '${p['stats']?['coverage'] ?? 0}%'),
                        style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w900))),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                // guards on duty
                Row(children: [const Icon(Icons.shield_rounded, size: 16, color: Color(0xFF16A34A)), const SizedBox(width: 6),
                  Text(tr('الحرّاس بالخدمة (${guards.length})', 'Guards on duty (${guards.length})'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))]),
                const SizedBox(height: 8),
                if (guards.isEmpty)
                  Text(tr('لا حرّاس بالخدمة حالياً', 'No guards on duty now'), style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5))
                else Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final gd in guards) Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                    decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.08), borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFF16A34A).withValues(alpha: 0.25))),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const CircleAvatar(radius: 10, backgroundColor: Color(0xFF16A34A), child: Icon(Icons.person_rounded, size: 12, color: Colors.white)),
                      const SizedBox(width: 6),
                      Text('${gd['name']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                    ]),
                  ),
                ]),
                const SizedBox(height: 18),
                // checkpoints
                Row(children: [const Icon(Icons.qr_code_scanner_rounded, size: 16, color: Color(0xFF0891B2)), const SizedBox(width: 6),
                  Text(tr('نقاط الدورية (${cps.length})', 'Patrol checkpoints (${cps.length})'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))]),
                const SizedBox(height: 8),
                if (cps.isEmpty)
                  Text(tr('لا نقاط دورية معرّفة', 'No checkpoints defined'), style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5))
                else ...cps.map(_checkpointRow),
                const SizedBox(height: 8),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _checkpointRow(Map c) {
    final s = '${c['status']}';
    final col = s == 'on_time' ? const Color(0xFF16A34A)
        : s == 'late' ? const Color(0xFFF7A23B)
        : s == 'missed' ? const Color(0xFFE5484D) : const Color(0xFF64748B);
    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        Container(width: 4, height: 36, decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${c['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          Text(tr('آخر فحص: ${c['last_check'] ?? '—'}', 'Last: ${c['last_check'] ?? '—'}'),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
          child: Text('${c['status_label'] ?? c['status']}', style: TextStyle(color: col, fontSize: 9.5, fontWeight: FontWeight.w900)),
        ),
      ]),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.92), borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2)),
          const SizedBox(width: 6),
          Text(text, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
        ]),
      );
}
