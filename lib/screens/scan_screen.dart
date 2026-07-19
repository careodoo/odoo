import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../models/models.dart';

/// Scan a location — the worker chooses QR (camera) or NFC (tap the chip).
/// Both resolve the same location code via /scan.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

enum _Mode { choose, qr, nfc, result }

class _ScanScreenState extends State<ScanScreen> {
  _Mode _mode = _Mode.choose;
  MobileScannerController? _qr;
  bool _handling = false;
  String? _status;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _qr?.dispose();
    _stopNfc();
    super.dispose();
  }

  // ---- shared: resolve a scanned code -------------------------------------
  Future<void> _process(String code) async {
    if (_handling) return;
    setState(() => _handling = true);
    try {
      final data = await context.read<AuthProvider>().api.scan(code);
      if (mounted) setState(() { _result = data; _mode = _Mode.result; });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
        setState(() { _handling = false; });
        if (_mode == _Mode.qr) _qr?.start();
      }
    }
  }

  void _reset() {
    _qr?.dispose(); _qr = null; _stopNfc();
    setState(() { _mode = _Mode.choose; _handling = false; _result = null; _status = null; });
  }

  // ---- QR ------------------------------------------------------------------
  Future<void> _startQr() async {
    // Request the camera permission at runtime (Android 6+); without this the
    // scanner surface shows only an error icon.
    var status = await Permission.camera.status;
    if (!status.isGranted) status = await Permission.camera.request();
    if (!status.isGranted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(
            status.isPermanentlyDenied
                ? tr('صلاحية الكاميرا مرفوضة — فعّلها من الإعدادات', 'Camera permission denied — enable it in Settings')
                : tr('يجب السماح باستخدام الكاميرا', 'Camera access is required'))));
        if (status.isPermanentlyDenied) openAppSettings();
      }
      return;
    }
    _qr = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
    setState(() => _mode = _Mode.qr);
  }

  void _onDetect(BarcodeCapture cap) {
    final code = cap.barcodes.isNotEmpty ? cap.barcodes.first.rawValue : null;
    if (code == null || code.isEmpty) return;
    _qr?.stop();
    _process(code);
  }

  // ---- NFC -----------------------------------------------------------------
  Future<void> _startNfc() async {
    final available = await NfcManager.instance.isAvailable();
    if (!available) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('NFC غير متاح أو غير مُفعَّل على هذا الجهاز', 'NFC is unavailable or switched off on this device'))));
      return;
    }
    setState(() { _mode = _Mode.nfc; _status = tr('قرّب الجهاز من شريحة NFC…', 'Hold the phone near an NFC tag…'); });
    NfcManager.instance.startSession(onDiscovered: (NfcTag tag) async {
      String? code = _codeFromTag(tag);
      await _stopNfc();
      if (code != null && code.isNotEmpty) {
        _process(code);
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('لم أتمكّن من قراءة رمز من الشريحة', 'Could not read a code from the tag'))));
        setState(() => _mode = _Mode.choose);
      }
    });
  }

  Future<void> _stopNfc() async {
    try { await NfcManager.instance.stopSession(); } catch (_) {}
  }

  String? _codeFromTag(NfcTag tag) {
    final ndef = Ndef.from(tag);
    final msg = ndef?.cachedMessage;
    if (msg == null) return null;
    for (final rec in msg.records) {
      final payload = rec.payload;
      if (payload.isEmpty) continue;
      // NDEF Text record: first byte = status (bit0-5 = language length)
      final isText = rec.typeNameFormat == NdefTypeNameFormat.nfcWellknown &&
          rec.type.length == 1 && rec.type.first == 0x54; // 'T'
      if (isText) {
        final langLen = payload[0] & 0x3f;
        return String.fromCharCodes(payload.sublist(1 + langLen)).trim();
      }
      // URI or other: best-effort readable string
      final s = String.fromCharCodes(payload.where((b) => b >= 32 && b < 127)).trim();
      if (s.isNotEmpty) return s;
    }
    return null;
  }

  // ---- UI ------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('مسح الموقع', 'Scan location'))),
      body: switch (_mode) {
        _Mode.choose => _chooser(),
        _Mode.qr => _qrView(),
        _Mode.nfc => _nfcView(),
        _Mode.result => _resultView(),
      },
    );
  }

  Widget _chooser() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(tr('اختر طريقة المسح', 'Choose scan method'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 24),
          _method(Icons.qr_code_scanner, tr('مسح رمز QR', 'Scan QR code'), tr('بالكاميرا', 'Using the camera'), const Color(0xFF2F6DF6), _startQr),
          const SizedBox(height: 16),
          _method(Icons.nfc, tr('مسح شريحة NFC', 'Scan NFC tag'), tr('قرّب الجهاز من الشريحة', 'Hold the device near the tag'), const Color(0xFF37C98A), _startNfc),
        ],
      ),
    );
  }

  Widget _method(IconData ic, String t, String s, Color c, VoidCallback onTap) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: c.withValues(alpha: 0.4)),
        ),
        child: Row(children: [
          Icon(ic, size: 40, color: c),
          const SizedBox(width: 18),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
            Text(s, style: TextStyle(color: Theme.of(context).colorScheme.outline)),
          ])),
          const Icon(Icons.chevron_left),
        ]),
      ),
    );
  }

  Widget _qrView() => Stack(
        alignment: Alignment.center,
        children: [
          MobileScanner(
            controller: _qr!,
            onDetect: _onDetect,
            errorBuilder: (context, error, child) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.no_photography, color: Colors.white, size: 60),
                  const SizedBox(height: 12),
                  Text('تعذّر تشغيل الكاميرا: ${error.errorCode.name}',
                      textAlign: TextAlign.center, style: const TextStyle(color: Colors.white)),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: openAppSettings, child: Text(tr('فتح الإعدادات', 'Open settings'))),
                ]),
              ),
            ),
          ),
          Container(height: 240, width: 240, decoration: BoxDecoration(border: Border.all(color: Colors.white, width: 3), borderRadius: BorderRadius.circular(20))),
          Positioned(bottom: 40, child: FilledButton.icon(onPressed: _reset, icon: const Icon(Icons.close), label: Text(tr('إلغاء', 'Cancel')))),
        ],
      );

  Widget _nfcView() => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.nfc, size: 90, color: Color(0xFF37C98A)),
          const SizedBox(height: 16),
          Text(_status ?? '', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 24),
          const CircularProgressIndicator(),
          const SizedBox(height: 24),
          TextButton(onPressed: _reset, child: Text(tr('إلغاء', 'Cancel'))),
        ]),
      );

  Widget _resultView() {
    final loc = (_result!['location'] as Map);
    final wos = [for (final j in (_result!['workorders'] as List)) WorkOrder.fromJson(j as Map)];
    final cs = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [Icon(Icons.check_circle, color: Color(0xFF16794A)), SizedBox(width: 8), Text(tr('تم تسجيل الحضور', 'Attendance recorded'), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16))]),
            const SizedBox(height: 10),
            Text('${loc['name']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
            Text('${loc['facility']} · ${loc['code']}', style: TextStyle(color: cs.outline)),
          ]),
        )),
        const SizedBox(height: 8),
        Text('أوامر العمل عند هذا الموقع (${wos.length})', style: const TextStyle(fontWeight: FontWeight.w800)),
        for (final w in wos) Card(child: ListTile(title: Text(w.title), subtitle: Text('${w.name} · ${w.serviceType}'))),
        const SizedBox(height: 8),
        FilledButton.icon(onPressed: _reset, icon: const Icon(Icons.replay), label: Text(tr('مسح آخر', 'Last scan'))),
      ],
    );
  }
}
