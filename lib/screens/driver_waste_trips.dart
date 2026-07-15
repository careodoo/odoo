import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Driver workspace for waste trips — lists the trips assigned to the logged-in
/// driver and lets them broadcast their live GPS location during a trip so the
/// client can track them on the map.
class DriverWasteTripsScreen extends StatefulWidget {
  const DriverWasteTripsScreen({super.key});
  @override
  State<DriverWasteTripsScreen> createState() => _DriverWasteTripsScreenState();
}

class _DriverWasteTripsScreenState extends State<DriverWasteTripsScreen> {
  Future<List<dynamic>>? _trips;
  int? _sharingTripId; // trip currently broadcasting
  StreamSubscription<Position>? _sub;
  Timer? _throttle;
  Position? _last;

  static const _navy = Color(0xFF0E3A5F);
  static const _green = Color(0xFF16A34A);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _stopSharing();
    super.dispose();
  }

  void _load() => setState(() => _trips = context.read<AuthProvider>().api.wasteDriverTrips());

  Future<void> _toggleShare(int tripId) async {
    if (_sharingTripId == tripId) { _stopSharing(); setState(() {}); return; }
    // permission
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('يلزم إذن الموقع لمشاركة موقعك', 'Location permission required'))));
      return;
    }
    _stopSharing();
    final api = context.read<AuthProvider>().api;
    setState(() => _sharingTripId = tripId);
    // push an immediate fix, then stream
    try {
      final p = await Geolocator.getCurrentPosition();
      await api.wasteTripSetLocation(tripId, p.latitude, p.longitude);
    } catch (_) {}
    _sub = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, distanceFilter: 20),
    ).listen((p) {
      _last = p;
      // throttle network to ~every 15s
      _throttle ??= Timer.periodic(const Duration(seconds: 15), (_) async {
        if (_last != null && _sharingTripId != null) {
          try { await api.wasteTripSetLocation(_sharingTripId!, _last!.latitude, _last!.longitude); } catch (_) {}
        }
      });
    });
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('بدأت مشاركة موقعك المباشر', 'Live location sharing started')), backgroundColor: _green));
  }

  void _stopSharing() {
    _sub?.cancel(); _sub = null;
    _throttle?.cancel(); _throttle = null;
    _sharingTripId = null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F6F5),
      appBar: AppBar(backgroundColor: _navy, foregroundColor: Colors.white, title: Text(tr('رحلاتي — النفايات', 'My waste trips')), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _trips,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final trips = snap.data!;
            if (trips.isEmpty) {
              return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90), child: Column(children: [
                const Icon(Icons.local_shipping_outlined, size: 60, color: Colors.grey),
                const SizedBox(height: 10),
                Text(tr('لا رحلات مُسندة إليك حاليًا', 'No trips assigned to you'), style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w700)),
              ]))]);
            }
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: trips.length,
              itemBuilder: (_, i) => _tripCard(trips[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _tripCard(Map t) {
    final sharing = _sharingTripId == t['id'];
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))], border: sharing ? Border.all(color: _green, width: 2) : null),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Text('🚛', style: TextStyle(fontSize: 22)), const SizedBox(width: 8),
          Expanded(child: Text('${t['sequence']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4), decoration: BoxDecoration(color: _navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(20)), child: Text('${t['state_label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: _navy))),
        ]),
        const SizedBox(height: 8),
        _kv(Icons.place_outlined, tr('الالتقاط', 'Pickup'), t['pickup']),
        _kv(Icons.factory_outlined, tr('مركز المعالجة', 'Center'), t['center']),
        _kv(Icons.event_outlined, tr('التاريخ', 'Date'), t['date']),
        const SizedBox(height: 10),
        SizedBox(width: double.infinity, height: 48, child: ElevatedButton.icon(
          onPressed: () => _toggleShare(t['id'] as int),
          icon: Icon(sharing ? Icons.stop_circle_outlined : Icons.my_location_rounded),
          label: Text(sharing ? tr('إيقاف مشاركة الموقع', 'Stop sharing') : tr('مشاركة موقعي المباشر', 'Share my live location'), style: const TextStyle(fontWeight: FontWeight.w800)),
          style: ElevatedButton.styleFrom(backgroundColor: sharing ? const Color(0xFFC0392B) : _green, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
        )),
        if (sharing) Padding(padding: const EdgeInsets.only(top: 8), child: Row(children: [
          Container(width: 9, height: 9, decoration: const BoxDecoration(color: _green, shape: BoxShape.circle)), const SizedBox(width: 6),
          Text(tr('يتم بث موقعك للعميل الآن', 'Broadcasting your location now'), style: const TextStyle(color: _green, fontSize: 12, fontWeight: FontWeight.w700)),
        ])),
      ]),
    );
  }

  Widget _kv(IconData ic, String k, dynamic v) => (v == null || '$v'.isEmpty) ? const SizedBox.shrink() : Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [Icon(ic, size: 16, color: Colors.grey), const SizedBox(width: 8), Text('$k: ', style: const TextStyle(color: Colors.grey, fontSize: 12.5)), Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)))]),
      );
}
