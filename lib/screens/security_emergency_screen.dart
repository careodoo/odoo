import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:geolocator/geolocator.dart';
import 'package:local_auth/local_auth.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/geo.dart';
import 'security_stream_screen.dart';

/// Panic / SOS. Raising requires a biometric confirmation, captures GPS, and
/// broadcasts to the guard's team; responders see the raiser on a live map and
/// can navigate to them. The raiser can stop the alert with a logged reason.
class Emergency {
  static Future<bool> _biometric(BuildContext context) async {
    final auth = LocalAuthentication();
    try {
      final can = await auth.isDeviceSupported() && await auth.canCheckBiometrics;
      if (!can) return true; // no biometrics enrolled → allow (confirm dialog already shown)
      return await auth.authenticate(
        localizedReason: tr('أكّد هويتك لإرسال نداء الاستغاثة', 'Confirm your identity to send an SOS'),
        options: const AuthenticationOptions(biometricOnly: false, stickyAuth: true),
      );
    } catch (_) {
      return true; // biometric error must never block a real emergency
    }
  }

  /// Confirm → biometric → GPS → raise → open the responder map.
  static Future<void> raise(BuildContext context) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text('🚨 ${tr('نداء استغاثة', 'Emergency SOS')}'),
      content: Text(tr('سيتم إشعار فريقك فوراً بموقعك. متابعة؟', 'Your team will be alerted with your location immediately. Continue?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('إرسال', 'Send'))),
      ]));
    if (ok != true || !context.mounted) return;
    if (!await _biometric(context)) return;
    double? lat, lng;
    try {
      if (await Geolocator.checkPermission() == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }
      final p = await Geolocator.getCurrentPosition();
      lat = p.latitude; lng = p.longitude;
    } catch (_) {/* send even without GPS */}
    if (!context.mounted) return;
    try {
      final r = await context.read<AuthProvider>().api.securityEmergencyRaise(lat: lat, lng: lng);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('🚨 ${tr('أُرسل النداء — أُشعر', 'SOS sent — notified')} ${r['notified'] ?? 0}'),
          backgroundColor: const Color(0xFFE5484D)));
      Navigator.push(context, MaterialPageRoute(builder: (_) => const SecurityEmergencyMapScreen()));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'.replaceFirst('Exception: ', '')), backgroundColor: const Color(0xFFE11D48)));
    }
  }
}

class SecurityEmergencyMapScreen extends StatefulWidget {
  const SecurityEmergencyMapScreen({super.key});
  @override
  State<SecurityEmergencyMapScreen> createState() => _SecurityEmergencyMapScreenState();
}

class _SecurityEmergencyMapScreenState extends State<SecurityEmergencyMapScreen> {
  static const _kwCenter = LatLng(29.3759, 47.9774);
  List<Map> _items = const [];
  Timer? _poll;
  LatLng? _myLoc;
  final _map = MapController();

  @override
  void initState() {
    super.initState();
    _load();
    Geo.current().then((l) { if (mounted && l != null) setState(() => _myLoc = l); });
    _poll = Timer.periodic(const Duration(seconds: 8), (_) { if (mounted) _load(); });
  }

  @override
  void dispose() { _poll?.cancel(); super.dispose(); }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.securityEmergencies();
      if (mounted) setState(() => _items = ((d['items'] as List?) ?? const []).cast<Map>());
    } catch (_) {}
  }

  LatLng? _pt(Map e) {
    final la = e['lat'], ln = e['lng'];
    if (la == null || ln == null) return null;
    final a = la is num ? la.toDouble() : double.tryParse('$la');
    final b = ln is num ? ln.toDouble() : double.tryParse('$ln');
    return (a != null && b != null) ? LatLng(a, b) : null;
  }

  Future<void> _stop(Map e) async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('إنهاء النداء', 'Stop SOS')),
      content: TextField(controller: ctrl, autofocus: true, decoration: InputDecoration(labelText: tr('السبب/النتيجة', 'Reason / outcome'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('إنهاء', 'Stop'))),
      ]));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.securityEmergencyStop(e['id'] as int, ctrl.text.trim());
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أُنهي النداء', 'SOS stopped')), backgroundColor: const Color(0xFF16A34A)));
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final markers = <Marker>[];
    for (final e in _items) {
      final p = _pt(e);
      if (p != null) {
        markers.add(Marker(point: p, width: 46, height: 46, child: const _Pulse()));
      }
    }
    if (_myLoc != null) markers.add(Geo.meMarker(_myLoc!));
    final center = markers.isNotEmpty ? markers.first.point : _kwCenter;
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(backgroundColor: const Color(0xFFE5484D), foregroundColor: Colors.white,
          title: Text('🚨 ${tr('نداءات الاستغاثة', 'SOS alerts')} (${_items.length})'),
          actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)]),
      body: Column(children: [
        SizedBox(height: 300, child: Stack(children: [
          FlutterMap(
          mapController: _map,
          options: MapOptions(initialCenter: center, initialZoom: 13),
          children: [
            TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'com.carekw.care_mobile'),
            MarkerLayer(markers: markers),
          ],
        ),
          Positioned(right: 10, bottom: 10, child: FloatingActionButton.small(
            heroTag: 'sos_myloc', backgroundColor: Colors.white, foregroundColor: const Color(0xFF1A73E8),
            onPressed: () async {
              var l = _myLoc ?? await Geo.current();
              if (l == null) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر تحديد موقعك', 'Could not get your location')))); return; }
              if (mounted) setState(() => _myLoc = l);
              _map.move(l, 15);
            },
            child: const Icon(Icons.my_location_rounded, size: 20),
          )),
        ])),
        Expanded(child: _items.isEmpty
            ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.verified_user_rounded, size: 70, color: Color(0xFF37C98A)),
                const SizedBox(height: 12),
                Text(tr('لا نداءات نشطة', 'No active alerts'), style: const TextStyle(color: Color(0xFF9CB2CD))),
              ]))
            : ListView(padding: const EdgeInsets.all(12), children: [for (final e in _items) _row(e)])),
      ]),
    );
  }

  Widget _row(Map e) {
    final p = _pt(e);
    return Card(color: const Color(0xFF152238), child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const _Pulse(size: 14),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${e['guard'] ?? tr('حارس', 'Guard')}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
            Text([e['premise'], e['at']].where((x) => x != null).join(' · '), style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 11)),
          ])),
          if (e['mine'] == true) Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: const Color(0xFF4AA8FF).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(10)),
              child: Text(tr('ندائي', 'Mine'), style: const TextStyle(color: Color(0xFF4AA8FF), fontSize: 9.5, fontWeight: FontWeight.w800))),
        ]),
        if (e['note'] != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text('${e['note']}', style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12))),
        const SizedBox(height: 8),
        Row(children: [
          if (p != null) Expanded(child: OutlinedButton.icon(
            onPressed: () => launchUrl(Uri.parse('https://www.google.com/maps/dir/?api=1&destination=${p.latitude},${p.longitude}'), mode: LaunchMode.externalApplication),
            icon: const Icon(Icons.navigation_rounded, size: 16, color: Color(0xFF4AA8FF)),
            style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF4AA8FF), side: const BorderSide(color: Color(0xFF4AA8FF))),
            label: Text(tr('التوجّه', 'Navigate'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          const SizedBox(width: 8),
          Expanded(child: FilledButton.icon(
            onPressed: () => _stop(e),
            icon: const Icon(Icons.stop_circle_rounded, size: 16),
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF37C98A)),
            label: Text(tr('إنهاء', 'Resolve'), style: const TextStyle(fontWeight: FontWeight.w800)))),
        ]),
        const SizedBox(height: 8),
        // stream: raiser can go live on their own alert; others can watch.
        SizedBox(width: double.infinity, child: e['mine'] == true
            ? FilledButton.icon(
                onPressed: () => Stream.goLive(context, incidentId: e['id'] as int, title: tr('بث مباشر', 'Live')),
                icon: const Icon(Icons.videocam_rounded, size: 16),
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
                label: Text(tr('بث مباشر من موقعي', 'Go live from my location'), style: const TextStyle(fontWeight: FontWeight.w800)))
            : OutlinedButton.icon(
                onPressed: () => Stream.watch(context, e['id'] as int, title: '${e['guard'] ?? ''}'),
                icon: const Icon(Icons.live_tv_rounded, size: 16, color: Color(0xFFE5484D)),
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5484D), side: const BorderSide(color: Color(0xFFE5484D))),
                label: Text(tr('مشاهدة بث الحارس', 'Watch guard\'s stream'), style: const TextStyle(fontWeight: FontWeight.w800)))),
      ]),
    ));
  }
}

/// A pulsing red dot for the SOS marker.
class _Pulse extends StatefulWidget {
  const _Pulse({this.size = 22});
  final double size;
  @override
  State<_Pulse> createState() => _PulseState();
}

class _PulseState extends State<_Pulse> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat(reverse: true);
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => AnimatedBuilder(animation: _c, builder: (_, __) => Stack(alignment: Alignment.center, children: [
        Container(width: widget.size * (1 + _c.value), height: widget.size * (1 + _c.value),
            decoration: BoxDecoration(color: const Color(0xFFE5484D).withValues(alpha: 0.25 * (1 - _c.value)), shape: BoxShape.circle)),
        Container(width: widget.size, height: widget.size,
            decoration: BoxDecoration(color: const Color(0xFFE5484D), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 2))),
      ]));
}
