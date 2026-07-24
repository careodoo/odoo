import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// أدوات موقع موحّدة لكل الخرائط: جلب موقع المستخدم بشكل موثوق (خدمة + أذونات +
/// دقة عالية) + نقطة «موقعي» الزرقاء القياسية (كخرائط جوجل).
class Geo {
  /// يجلب موقع المستخدم الحالي بدقة عالية. يعيد null عند تعذّر (خدمة مغلقة أو
  /// إذن مرفوض)، مع الرجوع لآخر موقع معروف كحلّ أخير.
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

  /// علامة «موقعي» لطبقة العلامات (نقطة زرقاء نابضة قياسية).
  static Marker meMarker(LatLng at) => Marker(
        point: at, width: 34, height: 34,
        child: const MyLocationDot(),
      );
}

/// نقطة الموقع الزرقاء القياسية: هالة شفّافة نابضة + قرص أزرق بحدّ أبيض.
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
          // الهالة النابضة
          Container(
            width: 14 + 20 * t,
            height: 14 + 20 * t,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: blue.withValues(alpha: (1 - t) * 0.25),
            ),
          ),
          // القرص الأزرق بحدّ أبيض
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
