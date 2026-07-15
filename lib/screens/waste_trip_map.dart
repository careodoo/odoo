import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Live driver tracking for a waste trip — polls the driver's GPS location and
/// shows it on an OpenStreetMap map with the treatment center.
class WasteTripMapScreen extends StatefulWidget {
  const WasteTripMapScreen({super.key, required this.tripId, required this.title});
  final int tripId;
  final String title;
  @override
  State<WasteTripMapScreen> createState() => _WasteTripMapScreenState();
}

class _WasteTripMapScreenState extends State<WasteTripMapScreen> {
  final _map = MapController();
  Timer? _timer;
  LatLng? _driver;
  String? _updated, _driverName;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final d = await context.read<AuthProvider>().api.wasteTripTrack(widget.tripId);
      final lat = (d['lat'] as num?)?.toDouble() ?? 0;
      final lng = (d['lng'] as num?)?.toDouble() ?? 0;
      if (mounted) {
        setState(() {
          _loading = false;
          _driverName = d['driver'] as String?;
          _updated = d['time'] as String?;
          if (lat != 0 || lng != 0) {
            _driver = LatLng(lat, lng);
          }
        });
        if (_driver != null) _map.move(_driver!, 14);
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white,
          title: Text('${tr('تتبّع', 'Track')} ${widget.title}')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _driver == null
              ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.location_off_outlined, size: 60, color: Colors.grey),
                  const SizedBox(height: 10),
                  Text(tr('لا يوجد موقع مباشر للسائق حاليًا', 'No live driver location yet'), style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w700)),
                ]))
              : Stack(children: [
                  FlutterMap(
                    mapController: _map,
                    options: MapOptions(initialCenter: _driver!, initialZoom: 14),
                    children: [
                      TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'com.care.app'),
                      MarkerLayer(markers: [
                        Marker(point: _driver!, width: 54, height: 54, child: _driverPin()),
                      ]),
                    ],
                  ),
                  Positioned(left: 12, right: 12, bottom: 12, child: _infoCard()),
                ]),
    );
  }

  Widget _driverPin() => Container(
        decoration: BoxDecoration(color: const Color(0xFF16A34A), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 3), boxShadow: const [BoxShadow(color: Colors.black38, blurRadius: 6)]),
        child: const Icon(Icons.local_shipping_rounded, color: Colors.white, size: 26),
      );

  Widget _infoCard() => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 10)]),
        child: Row(children: [
          Container(padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.local_shipping_rounded, color: Color(0xFF16A34A))),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_driverName ?? tr('السائق', 'Driver'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Color(0xFF0E3A5F))),
            if (_updated != null) Text('${tr('آخر تحديث', 'Updated')}: $_updated', style: const TextStyle(fontSize: 11.5, color: Colors.grey)),
          ])),
          Container(width: 10, height: 10, decoration: const BoxDecoration(color: Color(0xFF16A34A), shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text(tr('مباشر', 'Live'), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF16A34A))),
        ]),
      );
}
