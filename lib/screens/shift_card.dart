import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Geofenced shift open/close + availability status. Reads GPS and lets the
/// backend decide whether the worker is within a facility's fence.
class ShiftCard extends StatefulWidget {
  const ShiftCard({super.key});
  @override
  State<ShiftCard> createState() => _ShiftCardState();
}

class _ShiftCardState extends State<ShiftCard> {
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
    if (_loading) return const SizedBox.shrink();
    final open = _shift?['open'] != null;
    final c = open ? const Color(0xFF16A34A) : const Color(0xFF64748B);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.withValues(alpha: 0.4)),
      ),
      child: Row(children: [
        Icon(open ? Icons.check_circle : Icons.radio_button_unchecked, color: c, size: 34),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(open ? tr('متاح — وردية مفتوحة', 'Available — on shift') : tr('خارج الوردية', 'Off shift'),
              style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 15)),
          if (open && _shift!['open']?['facility'] != null)
            Text('${_shift!['open']['facility']}', style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
        ])),
        FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: open ? const Color(0xFFE5484D) : const Color(0xFF16A34A)),
          onPressed: _busy ? null : () => _toggle(!open),
          icon: Icon(open ? Icons.logout : Icons.login, size: 18),
          label: Text(_busy ? '...' : (open ? tr('إنهاء الوردية', 'End shift') : tr('بدء الوردية', 'Start shift'))),
        ),
      ]),
    );
  }
}
