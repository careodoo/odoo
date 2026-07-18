import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:nfc_manager/nfc_manager.dart';
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

  /// Some locations carry an NFC tag instead of (or as well as) a QR sticker —
  /// tapping the phone on it proves presence exactly the same way.
  Future<void> _scanNfc() async {
    try {
      final available = await NfcManager.instance.isAvailable();
      if (!available) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('NFC غير متاح على هذا الجهاز', 'NFC is not available on this device'))));
        }
        return;
      }
      if (!mounted) return;
      showDialog(context: context, barrierDismissible: true, builder: (_) => AlertDialog(
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.nfc_rounded, size: 46, color: Color(0xFF0E3A5F)),
          const SizedBox(height: 12),
          Text(tr('قرّب الجهاز من وسم الموقع…', 'Hold the phone near the location tag…'),
              textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700)),
        ]),
      ));
      NfcManager.instance.startSession(onDiscovered: (tag) async {
        String? code;
        try {
          final ndef = Ndef.from(tag);
          final rec = ndef?.cachedMessage?.records.first;
          if (rec != null && rec.payload.isNotEmpty) {
            // NDEF text records start with a status byte + language code
            final bytes = rec.payload;
            final langLen = bytes.first & 0x3F;
            code = String.fromCharCodes(bytes.skip(1 + langLen));
          }
        } catch (_) {}
        // fall back to the tag's hardware id
        code ??= (tag.data['nfca']?['identifier'] as List?)
            ?.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
        await NfcManager.instance.stopSession();
        if (!mounted || code == null || code.isEmpty || _done) return;
        _done = true;
        _c?.stop();
        Navigator.pop(context); // close the "hold near tag" dialog
        Navigator.pop(context, code);
      });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  void dispose() {
    try { NfcManager.instance.stopSession(); } catch (_) {}
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black, foregroundColor: Colors.white,
        title: Text(tr('إثبات الحضور — QR أو NFC', 'Prove presence — QR or NFC')),
        actions: [
          IconButton(
            icon: const Icon(Icons.nfc_rounded),
            tooltip: tr('مسح NFC', 'Tap NFC'),
            onPressed: _scanNfc,
          ),
        ],
      ),
      body: _denied
          ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(
              mainAxisSize: MainAxisSize.min, children: [
                Text(tr('صلاحية الكاميرا مطلوبة لمسح QR — أو استخدم NFC.',
                        'Camera permission is required for QR — or use NFC.'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 16),
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F)),
                  onPressed: _scanNfc,
                  icon: const Icon(Icons.nfc_rounded),
                  label: Text(tr('إثبات الحضور بـ NFC', 'Prove presence with NFC')),
                ),
              ])))
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
                    const SizedBox(height: 14),
                    // the location may carry an NFC tag instead of a sticker
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Colors.white54),
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      ),
                      onPressed: _scanNfc,
                      icon: const Icon(Icons.nfc_rounded),
                      label: Text(tr('أو قرّب الجهاز من وسم NFC', 'Or tap an NFC tag'),
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ])),
                ]),
    );
  }
}
