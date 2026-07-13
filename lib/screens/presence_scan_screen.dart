import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';
import '../core/i18n.dart';

/// Minimal QR scanner that pops the scanned raw code back to the caller.
/// Used for presence proof before a worker may start a task.
class PresenceScanScreen extends StatefulWidget {
  const PresenceScanScreen({super.key, this.expectedName});
  final String? expectedName;
  @override
  State<PresenceScanScreen> createState() => _PresenceScanScreenState();
}

class _PresenceScanScreenState extends State<PresenceScanScreen> {
  MobileScannerController? _c;
  bool _denied = false;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    _start();
  }

  Future<void> _start() async {
    var s = await Permission.camera.status;
    if (!s.isGranted) s = await Permission.camera.request();
    if (!s.isGranted) {
      if (mounted) setState(() => _denied = true);
      if (s.isPermanentlyDenied) openAppSettings();
      return;
    }
    setState(() => _c = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates));
  }

  void _onDetect(BarcodeCapture cap) {
    if (_done) return;
    final code = cap.barcodes.isNotEmpty ? cap.barcodes.first.rawValue : null;
    if (code == null || code.isEmpty) return;
    _done = true;
    _c?.stop();
    Navigator.pop(context, code);
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black, foregroundColor: Colors.white,
        title: Text(tr('إثبات الحضور — امسح رمز الموقع', 'Prove presence — scan location')),
      ),
      body: _denied
          ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(
              tr('صلاحية الكاميرا مطلوبة لإثبات الحضور.', 'Camera permission is required.'),
              textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70))))
          : _c == null
              ? const Center(child: CircularProgressIndicator(color: Colors.white))
              : Stack(children: [
                  MobileScanner(controller: _c!, onDetect: _onDetect,
                      errorBuilder: (_, __, ___) => Center(child: Text(
                          tr('تعذّر تشغيل الكاميرا', 'Camera unavailable'),
                          style: const TextStyle(color: Colors.white70)))),
                  // aiming frame
                  Center(child: Container(width: 230, height: 230, decoration: BoxDecoration(
                      border: Border.all(color: Colors.white, width: 3), borderRadius: BorderRadius.circular(18)))),
                  Positioned(left: 0, right: 0, bottom: 40, child: Column(children: [
                    if (widget.expectedName != null)
                      Container(
                        margin: const EdgeInsets.symmetric(horizontal: 30),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(12)),
                        child: Text('📍 ${widget.expectedName}', textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
                      ),
                    const SizedBox(height: 10),
                    Text(tr('وجّه الكاميرا نحو ملصق QR الخاص بالموقع', 'Point at the location QR sticker'),
                        style: const TextStyle(color: Colors.white70)),
                  ])),
                ]),
    );
  }
}
