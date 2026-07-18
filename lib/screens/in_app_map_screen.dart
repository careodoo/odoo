import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/i18n.dart';

/// An in-app interactive map for a place, rendered from a text query. Uses
/// OpenStreetMap tiles via flutter_map (NO API key, no Google billing) and the
/// free Nominatim geocoder to turn the facility/location name into coordinates.
/// A button hands off to the device's maps app for turn-by-turn directions.
class InAppMapScreen extends StatefulWidget {
  const InAppMapScreen({super.key, required this.query, this.title});
  final String query;
  final String? title;

  @override
  State<InAppMapScreen> createState() => _InAppMapScreenState();
}

class _InAppMapScreenState extends State<InAppMapScreen> {
  LatLng? _point;
  String? _error;
  bool _loading = true;

  static const _navy = Color(0xFF0E3A5F);
  // Kuwait City fallback centre so the map is never blank while/if geocoding fails.
  static const _fallback = LatLng(29.3759, 47.9774);

  @override
  void initState() {
    super.initState();
    _geocode();
  }

  Future<void> _geocode() async {
    try {
      final uri = Uri.parse('https://nominatim.openstreetmap.org/search'
          '?q=${Uri.encodeQueryComponent(widget.query)}&format=json&limit=1&countrycodes=kw');
      final res = await http.get(uri, headers: {'User-Agent': 'CareMobile/1.0 (care-kw.com)'});
      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List;
        if (list.isNotEmpty) {
          final m = list.first as Map;
          _point = LatLng(double.parse('${m['lat']}'), double.parse('${m['lon']}'));
        }
      }
      // Retry without the country filter if nothing matched.
      if (_point == null) {
        final uri2 = Uri.parse('https://nominatim.openstreetmap.org/search'
            '?q=${Uri.encodeQueryComponent(widget.query)}&format=json&limit=1');
        final res2 = await http.get(uri2, headers: {'User-Agent': 'CareMobile/1.0 (care-kw.com)'});
        if (res2.statusCode == 200) {
          final list = jsonDecode(res2.body) as List;
          if (list.isNotEmpty) {
            final m = list.first as Map;
            _point = LatLng(double.parse('${m['lat']}'), double.parse('${m['lon']}'));
          }
        }
      }
      if (_point == null) _error = tr('تعذّر تحديد الموقع على الخريطة', 'Could not locate this place');
    } catch (e) {
      _error = tr('تعذّر تحميل الخريطة', 'Could not load the map');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openExternal() async {
    // Prefer a geo: pin when we have coordinates; else fall back to a text search.
    final Uri uri = _point != null
        ? Uri.parse('https://www.google.com/maps/search/?api=1&query=${_point!.latitude},${_point!.longitude}')
        : Uri.parse('https://www.google.com/maps/search/?api=1&query=${Uri.encodeQueryComponent(widget.query)}');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('تعذّر فتح الخرائط', 'Could not open maps'))));
    }
  }

  @override
  Widget build(BuildContext context) {
    final center = _point ?? _fallback;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white,
        title: Text(widget.title ?? tr('الموقع', 'Location'), overflow: TextOverflow.ellipsis),
      ),
      body: Stack(children: [
        FlutterMap(
          options: MapOptions(initialCenter: center, initialZoom: _point != null ? 16 : 11),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.care.app',
              maxZoom: 19,
            ),
            if (_point != null)
              MarkerLayer(markers: [
                Marker(
                  point: _point!, width: 46, height: 46,
                  child: const Icon(Icons.location_on_rounded, color: Color(0xFFC0392B), size: 46),
                ),
              ]),
            // OSM attribution (required by the tile usage policy).
            const RichAttributionWidget(attributions: [
              TextSourceAttribution('OpenStreetMap contributors'),
            ]),
          ],
        ),
        if (_loading) const Center(child: CircularProgressIndicator(color: _navy)),
        if (!_loading && _error != null)
          Positioned(
            top: 12, left: 12, right: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.12), blurRadius: 8)]),
              child: Row(children: [
                const Icon(Icons.info_outline_rounded, size: 16, color: _navy),
                const SizedBox(width: 8),
                Expanded(child: Text('$_error · ${widget.query}',
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
              ]),
            ),
          ),
        Positioned(
          left: 14, right: 14, bottom: 16,
          child: SafeArea(child: SizedBox(
            height: 52,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _navy,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _openExternal,
              icon: const Icon(Icons.directions_rounded),
              label: Text(tr('فتح الاتجاهات في الخرائط', 'Open directions in Maps'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            ),
          )),
        ),
      ]),
    );
  }
}
