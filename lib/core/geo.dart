import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Unified location utilities for all maps: fetch the user's location reliably (service + permissions +
/// high accuracy) + the standard blue «my location» dot (like Google Maps).
class Geo {
  /// Fetches the user's current location at high accuracy. Returns null when unavailable (service off or
  /// permission denied), falling back to the last known location as a last resort.
  static Future<LatLng?> current() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return await _lastKnown();
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        return await _lastKnown();
      }
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 12),
        ),
      );
      return LatLng(p.latitude, p.longitude);
    } catch (_) {
      return await _lastKnown();
    }
  }

  static Future<LatLng?> _lastKnown() async {
    try {
      final l = await Geolocator.getLastKnownPosition();
      return l != null ? LatLng(l.latitude, l.longitude) : null;
    } catch (_) {
      return null;
    }
  }

  /// «My location» marker for the markers layer (a standard pulsing blue dot).
  static Marker meMarker(LatLng at) => Marker(
        point: at, width: 34, height: 34,
        child: const MyLocationDot(),
      );
}

/// The standard blue location dot: a translucent pulsing halo + a blue disc with a white border.
class MyLocationDot extends StatefulWidget {
  const MyLocationDot({super.key});
  @override
  State<MyLocationDot> createState() => _MyLocationDotState();
}

class _MyLocationDotState extends State<MyLocationDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const blue = Color(0xFF1A73E8);
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        final t = _c.value; // 0..1
        return Stack(alignment: Alignment.center, children: [
          // The pulsing halo
          Container(
            width: 14 + 20 * t,
            height: 14 + 20 * t,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: blue.withValues(alpha: (1 - t) * 0.25),
            ),
          ),
          // The blue disc with a white border
          Container(
            width: 16, height: 16,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: blue,
              border: Border.all(color: Colors.white, width: 2.5),
              boxShadow: [BoxShadow(color: blue.withValues(alpha: .5), blurRadius: 4)],
            ),
          ),
        ]);
      },
    );
  }
}
