import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/i18n.dart';

/// An in-app interactive map for a place, rendered from a text query (facility /
/// location name + address) via an embedded Google Maps view — no API key and no
/// device coordinates needed. A button hands off to the device's maps app for
/// turn-by-turn when the user actually wants to drive there.
class InAppMapScreen extends StatefulWidget {
  const InAppMapScreen({super.key, required this.query, this.title});
  final String query;
  final String? title;

  @override
  State<InAppMapScreen> createState() => _InAppMapScreenState();
}

class _InAppMapScreenState extends State<InAppMapScreen> {
  late final WebViewController _c;
  bool _loading = true;

  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    final q = Uri.encodeComponent(widget.query);
    _c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onPageFinished: (_) { if (mounted) setState(() => _loading = false); },
      ))
      ..loadRequest(Uri.parse('https://maps.google.com/maps?q=$q&z=16&output=embed'));
  }

  Future<void> _openExternal() async {
    final q = Uri.encodeComponent(widget.query);
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$q');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('تعذّر فتح الخريطة', 'Could not open maps'))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white,
        title: Text(widget.title ?? tr('الموقع', 'Location'), overflow: TextOverflow.ellipsis),
      ),
      body: Stack(children: [
        WebViewWidget(controller: _c),
        if (_loading) const Center(child: CircularProgressIndicator(color: _navy)),
        Positioned(
          left: 14, right: 14, bottom: 16,
          child: SafeArea(child: SizedBox(
            height: 52,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: _navy,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
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
