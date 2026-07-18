import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:nfc_manager/nfc_manager.dart';
import '../core/i18n.dart';

/// A reusable location picker: a searchable list of the client's QR-tagged
/// locations, plus "scan QR" and "tap NFC" shortcuts that resolve a tag's code
/// straight to the matching location. Returns the chosen location Map (must
/// contain 'id', 'name', and ideally 'code').
class LocationPickerSheet extends StatefulWidget {
  const LocationPickerSheet({super.key, required this.locations, this.title});
  final List<Map> locations;
  final String? title;

  static Future<Map?> open(BuildContext context, {required List<Map> locations, String? title}) =>
      showModalBottomSheet<Map>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => LocationPickerSheet(locations: locations, title: title),
      );

  @override
  State<LocationPickerSheet> createState() => _LocationPickerSheetState();
}

class _LocationPickerSheetState extends State<LocationPickerSheet> {
  String _q = '';
  String? _msg;

  static const _accent = Color(0xFFC0392B);
  static const _navy = Color(0xFF0E3A5F);

  List<Map> get _filtered {
    if (_q.isEmpty) return widget.locations;
    final q = _q.toLowerCase();
    return widget.locations.where((l) =>
        '${l['name'] ?? ''}${l['code'] ?? ''}${l['building'] ?? ''}${l['floor'] ?? ''}'
            .toLowerCase().contains(q)).toList();
  }

  /// Match a scanned/tapped code to a location and return it, else flag it.
  void _resolveCode(String code) {
    final c = code.trim().toLowerCase();
    final hit = widget.locations.firstWhere(
      (l) => '${l['code'] ?? ''}'.toLowerCase() == c || '${l['name'] ?? ''}'.toLowerCase() == c,
      orElse: () => const {},
    );
    if (hit.isNotEmpty) {
      Navigator.pop(context, hit);
    } else {
      setState(() => _msg = tr('لا يوجد موقع بهذا الرمز: $code', 'No location with code: $code'));
    }
  }

  Future<void> _scanQr() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(
        builder: (_) => const _QrScanPage()));
    if (code != null && mounted) _resolveCode(code);
  }

  Future<void> _scanNfc() async {
    try {
      final available = await NfcManager.instance.isAvailable();
      if (!available) {
        if (mounted) setState(() => _msg = tr('NFC غير متاح على هذا الجهاز', 'NFC not available on this device'));
        return;
      }
      if (!mounted) return;
      showDialog(context: context, barrierDismissible: true, builder: (_) => AlertDialog(
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.nfc_rounded, size: 46, color: _navy),
          const SizedBox(height: 12),
          Text(tr('قرّب الجهاز من وسم الموقع…', 'Hold near the location tag…'),
              textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700)),
        ]),
      ));
      NfcManager.instance.startSession(onDiscovered: (tag) async {
        String? code;
        try {
          final ndef = Ndef.from(tag);
          final rec = ndef?.cachedMessage?.records.firstOrNull;
          if (rec != null) {
            // NDEF text/URI payload — skip the language/status byte heuristically.
            final payload = rec.payload;
            code = String.fromCharCodes(payload.length > 3 ? payload.sublist(3) : payload).trim();
          }
        } catch (_) {}
        code ??= (tag.data['nfca']?['identifier'] as List?)?.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
        await NfcManager.instance.stopSession();
        if (mounted) {
          Navigator.of(context, rootNavigator: true).pop(); // close the "hold near" dialog
          if (code != null && code.isNotEmpty) _resolveCode(code);
        }
      });
    } catch (e) {
      if (mounted) setState(() => _msg = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 12, 12, 14),
            decoration: BoxDecoration(gradient: LinearGradient(
                colors: [_navy, Color.lerp(_navy, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Column(children: [
              Row(children: [
                const Icon(Icons.pin_drop_rounded, color: Colors.white, size: 22),
                const SizedBox(width: 10),
                Expanded(child: Text(widget.title ?? tr('اختر الموقع', 'Choose location'),
                    style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
                IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
              ]),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: _scanBtn(Icons.qr_code_scanner_rounded, tr('مسح QR', 'Scan QR'), _scanQr)),
                const SizedBox(width: 10),
                Expanded(child: _scanBtn(Icons.nfc_rounded, tr('مسح NFC', 'Tap NFC'), _scanNfc)),
              ]),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
            child: TextField(
              autofocus: false,
              onChanged: (v) => setState(() { _q = v; _msg = null; }),
              decoration: InputDecoration(
                hintText: tr('ابحث بالاسم أو الرمز أو المبنى…', 'Search name, code or building…'),
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                isDense: true, filled: true, fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              ),
            ),
          ),
          if (_msg != null)
            Padding(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: Container(
                width: double.infinity, padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(color: _accent.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
                child: Text(_msg!, style: const TextStyle(color: _accent, fontSize: 11.5, fontWeight: FontWeight.w700)),
              )),
          Expanded(child: ListView.builder(
            controller: sc, padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
            itemCount: _filtered.length,
            itemBuilder: (_, i) {
              final l = _filtered[i];
              return Container(
                margin: const EdgeInsets.only(bottom: 7),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                child: ListTile(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  leading: Container(
                    width: 38, height: 38, alignment: Alignment.center,
                    decoration: BoxDecoration(color: _navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(11)),
                    child: const Icon(Icons.qr_code_2_rounded, color: _navy, size: 20),
                  ),
                  title: Text('${l['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
                  subtitle: Text([
                    if (l['code'] != null) '${l['code']}',
                    if (l['building'] != null) '${l['building']}',
                    if (l['floor'] != null) '${l['floor']}',
                  ].join(' · '), style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                  trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
                  onTap: () => Navigator.pop(context, l),
                ),
              );
            },
          )),
        ]),
      ),
    );
  }

  Widget _scanBtn(IconData ic, String label, VoidCallback onTap) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.25))),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(ic, color: Colors.white, size: 18),
            const SizedBox(width: 7),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5)),
          ]),
        ),
      );
}

/// Minimal full-screen QR scanner that pops the first decoded value.
class _QrScanPage extends StatelessWidget {
  const _QrScanPage();
  @override
  Widget build(BuildContext context) {
    var done = false;
    return Scaffold(
      appBar: AppBar(title: Text(tr('مسح رمز الموقع', 'Scan location QR')),
          backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white),
      body: MobileScanner(onDetect: (capture) {
        if (done) return;
        final code = capture.barcodes.firstOrNull?.rawValue;
        if (code != null && code.isNotEmpty) { done = true; Navigator.pop(context, code); }
      }),
    );
  }
}
