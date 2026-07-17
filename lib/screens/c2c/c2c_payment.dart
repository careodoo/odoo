import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// Hosted-checkout screen: opens a Upayment payment link in a WebView and
/// resolves true/false by watching for the app's own /c2c/pay/return or
/// /c2c/pay/cancel landing URL. Returns null if the user backs out.
class C2CPaymentScreen extends StatefulWidget {
  const C2CPaymentScreen({super.key, required this.url});
  final String url;
  @override
  State<C2CPaymentScreen> createState() => _C2CPaymentScreenState();
}

class _C2CPaymentScreenState extends State<C2CPaymentScreen> {
  late final WebViewController _c;
  bool _loading = true;
  bool _settled = false;

  @override
  void initState() {
    super.initState();
    _c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (u) => _check(u),
        onPageFinished: (u) { if (mounted) setState(() => _loading = false); _check(u); },
        onNavigationRequest: (r) { _check(r.url); return NavigationDecision.navigate; },
      ))
      ..loadRequest(Uri.parse(widget.url));
  }

  /// The return page carries the outcome in its path; resolve as soon as we see
  /// it, so the customer doesn't have to tap "back to app" themselves.
  void _check(String url) {
    if (_settled) return;
    if (url.contains('/c2c/pay/return')) {
      _settled = true;
      // the landing page marks paid unless it says otherwise
      final paid = !url.toLowerCase().contains('result=failed') &&
          !url.toLowerCase().contains('cancel');
      if (mounted) Navigator.pop(context, paid);
    } else if (url.contains('/c2c/pay/cancel')) {
      _settled = true;
      if (mounted) Navigator.pop(context, false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final leave = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
          title: Text(tr('إلغاء الدفع؟', 'Cancel payment?')),
          content: Text(tr('سيتم إلغاء عملية الدفع الحالية.', 'This will cancel the current payment.')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('متابعة الدفع', 'Keep paying'))),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: C2C.red),
                onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إلغاء', 'Cancel'))),
          ],
        ));
        if (leave == true && mounted) Navigator.pop(context, null);
      },
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: C2C.red, foregroundColor: Colors.white, elevation: 0,
          title: Row(children: [
            const Icon(Icons.lock_rounded, size: 16),
            const SizedBox(width: 6),
            Text(tr('دفع آمن', 'Secure payment')),
          ]),
        ),
        body: Stack(children: [
          WebViewWidget(controller: _c),
          if (_loading) const Center(child: CircularProgressIndicator(color: C2C.red)),
        ]),
      ),
    );
  }
}

/// Creates a payment link for [kind]/[id] and runs the checkout. Returns true on
/// success, false on failure/cancel, null if aborted before starting.
Future<bool?> runC2CPayment(BuildContext context, {required String kind, required int id}) async {
  try {
    final r = await context.read<AuthProvider>().api.c2cPayCreate(kind, id);
    final link = '${r['link'] ?? ''}';
    if (link.isEmpty || !context.mounted) return null;
    return await Navigator.push<bool>(context,
        MaterialPageRoute(builder: (_) => C2CPaymentScreen(url: link)));
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
    }
    return null;
  }
}
