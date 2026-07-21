import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/i18n.dart';

/// In-app UPayments checkout. Opens the hosted payment page in a WebView and
/// pops with `true` (paid) / `false` (cancelled) the moment the gateway
/// redirects back to our return / cancel URL — so the card entry never leaves
/// the app.
class PaymentWebViewScreen extends StatefulWidget {
  final String url;
  const PaymentWebViewScreen({super.key, required this.url});
  @override
  State<PaymentWebViewScreen> createState() => _PaymentWebViewScreenState();
}

class _PaymentWebViewScreenState extends State<PaymentWebViewScreen> {
  late final WebViewController _wc;
  bool _loading = true;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    _wc = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFF4F6FA))
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (u) => _intercept(u),
        onPageFinished: (u) {
          if (mounted) setState(() => _loading = false);
          _intercept(u);
        },
        onNavigationRequest: (req) {
          if (_intercept(req.url)) return NavigationDecision.prevent;
          return NavigationDecision.navigate;
        },
      ))
      ..loadRequest(Uri.parse(widget.url));
  }

  /// Close as soon as the gateway hands control back to our server. We match on
  /// path so any query the gateway appends is irrelevant.
  bool _intercept(String url) {
    if (_done) return false;
    final paid = url.contains('/upay/return');
    final cancelled = url.contains('/upay/cancel');
    if (paid || cancelled) {
      _done = true;
      if (mounted) Navigator.of(context).pop(paid);
      return true;
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, _) {},
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: const Color(0xFF0E3A5F),
          foregroundColor: Colors.white,
          title: Text(tr('الدفع الآمن', 'Secure payment'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
          leading: IconButton(
            icon: const Icon(Icons.close_rounded),
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ),
        body: Stack(children: [
          WebViewWidget(controller: _wc),
          if (_loading)
            const Center(child: CircularProgressIndicator(color: Color(0xFF0E3A5F))),
        ]),
      ),
    );
  }
}
