import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Compact shift on/off toggle for the app-bar header. Geofenced open/close:
/// reads GPS and the backend decides whether the worker is within a fence.
class ShiftToggle extends StatefulWidget {
  const ShiftToggle({super.key, this.onSurface = false});
  /// true when placed on a dark/coloured app bar (use light text).
  final bool onSurface;
  @override
  State<ShiftToggle> createState() => _ShiftToggleState();
}

class _ShiftToggleState extends State<ShiftToggle> {
  Map<String, dynamic>? _shift;
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.shiftCurrent();
      if (mounted) setState(() { _shift = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<Position?> _pos() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      _snack(tr('فعّل خدمة الموقع (GPS)', 'Enable location service (GPS)'));
      return null;
    }
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
      _snack(tr('يجب السماح بالوصول للموقع', 'Location permission is required'));
      return null;
    }
    return Geolocator.getCurrentPosition();
  }

  void _snack(String m) {
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _toggle(bool open) async {
    setState(() => _busy = true);
    final api = context.read<AuthProvider>().api;
    try {
      final p = await _pos();
      if (p == null) { setState(() => _busy = false); return; }
      if (open) {
        await api.shiftOpen(p.latitude, p.longitude);
        _snack(tr('بدأت الوردية — أنت متاح الآن', 'Shift started — you are now available'));
      } else {
        await api.shiftClose(p.latitude, p.longitude);
        _snack(tr('انتهت الوردية', 'Shift ended'));
      }
      await _load();
    } catch (e) {
      _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final open = _shift?['open'] != null;
    final onC = widget.onSurface ? Colors.white : Theme.of(context).colorScheme.onSurface;
    final live = open ? const Color(0xFF22C55E) : (widget.onSurface ? Colors.white70 : const Color(0xFF94A3B8));
    return Tooltip(
      message: open ? tr('وردية مفتوحة — اضغط للإنهاء', 'On shift — tap to end')
                    : tr('خارج الوردية — اضغط للبدء', 'Off shift — tap to start'),
      child: InkWell(
        borderRadius: BorderRadius.circular(30),
        onTap: (_busy || _loading) ? null : () => _toggle(!open),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(width: 8, height: 8, decoration: BoxDecoration(color: live, shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Text(open ? tr('متاح', 'On') : tr('وردية', 'Shift'),
                style: TextStyle(color: onC, fontWeight: FontWeight.w800, fontSize: 12.5)),
            const SizedBox(width: 4),
            // switch track
            SizedBox(
              width: 40, height: 24,
              child: (_busy || _loading)
                  ? Center(child: SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2, color: onC)))
                  : AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      decoration: BoxDecoration(
                        color: open ? const Color(0xFF16A34A) : (widget.onSurface ? Colors.white24 : const Color(0xFFCBD5E1)),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: AnimatedAlign(
                        duration: const Duration(milliseconds: 180),
                        alignment: open ? Alignment.centerLeft : Alignment.centerRight, // RTL: open→left
                        child: Container(
                          width: 18, height: 18,
                          margin: const EdgeInsets.all(3),
                          decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                        ),
                      ),
                    ),
            ),
          ]),
        ),
      ),
    );
  }
}
