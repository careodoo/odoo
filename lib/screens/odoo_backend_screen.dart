import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Full Odoo web backend inside the app via seamless token→session SSO.
/// Odoo's own groups gate what the signed-in user can see.
class OdooBackendScreen extends StatefulWidget {
  const OdooBackendScreen({super.key, this.path = '/web', this.title});
  final String path;
  final String? title;
  @override
  State<OdooBackendScreen> createState() => _OdooBackendScreenState();
}

class _OdooBackendScreenState extends State<OdooBackendScreen> {
  WebViewController? _wc;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    final api = context.read<AuthProvider>().api;
    final token = await api.token;
    final url = '${api.baseUrl}/api/v1/web/sso?token=${Uri.encodeQueryComponent(token ?? '')}'
        '&redirect=${Uri.encodeQueryComponent(widget.path)}';
    final c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFEEF4FB))
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) { if (mounted) setState(() => _loading = true); },
        onPageFinished: (_) { if (mounted) setState(() => _loading = false); },
      ))
      ..loadRequest(Uri.parse(url));
    if (mounted) setState(() => _wc = c);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF0E3A5F),
        foregroundColor: Colors.white,
        title: Text(widget.title ?? tr('لوحة أودو الكاملة', 'Odoo backend')),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () => _wc?.reload()),
        ],
      ),
      body: Stack(children: [
        if (_wc != null) WebViewWidget(controller: _wc!),
        if (_loading) const LinearProgressIndicator(minHeight: 3),
      ]),
    );
  }
}
