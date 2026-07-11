import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../models/models.dart';

/// Live QR scanner. Scanning a location code logs presence and shows the work
/// orders at that spot (the same QR every service shares).
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  bool _handling = false;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture cap) async {
    if (_handling) return;
    final code = cap.barcodes.isNotEmpty ? cap.barcodes.first.rawValue : null;
    if (code == null || code.isEmpty) return;
    setState(() => _handling = true);
    await _controller.stop();
    try {
      final data = await context.read<AuthProvider>().api.scan(code);
      if (mounted) setState(() => _result = data);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
        await _controller.start();
        setState(() => _handling = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('مسح رمز الموقع')),
      body: _result != null ? _resultView() : _scanView(),
    );
  }

  Widget _scanView() => Stack(
        alignment: Alignment.center,
        children: [
          MobileScanner(controller: _controller, onDetect: _onDetect),
          Container(
            height: 240,
            width: 240,
            decoration: BoxDecoration(
              border: Border.all(color: Colors.white, width: 3),
              borderRadius: BorderRadius.circular(20),
            ),
          ),
          const Positioned(
            bottom: 40,
            child: Text('وجّه الكاميرا نحو رمز QR',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700)),
          ),
        ],
      );

  Widget _resultView() {
    final loc = (_result!['location'] as Map);
    final wos = [for (final j in (_result!['workorders'] as List)) WorkOrder.fromJson(j as Map)];
    final cs = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  const Icon(Icons.check_circle, color: Color(0xFF16794A)),
                  const SizedBox(width: 8),
                  const Text('تم تسجيل الحضور', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                ]),
                const SizedBox(height: 10),
                Text('${loc['name']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                Text('${loc['facility']} · ${loc['code']}', style: TextStyle(color: cs.outline)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text('أوامر العمل عند هذا الموقع (${wos.length})',
            style: const TextStyle(fontWeight: FontWeight.w800)),
        for (final w in wos)
          Card(
            child: ListTile(
              title: Text(w.title),
              subtitle: Text('${w.name} · ${w.serviceType}'),
            ),
          ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: () {
            setState(() {
              _result = null;
              _handling = false;
            });
            _controller.start();
          },
          icon: const Icon(Icons.qr_code_scanner),
          label: const Text('مسح رمز آخر'),
        ),
      ],
    );
  }
}
