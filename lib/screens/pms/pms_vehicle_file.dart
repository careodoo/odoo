import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/service_ui.dart';
import 'pms_shell.dart';

/// The vehicle file a project manager sees: identity, driver, odometer and its
/// fuel history. Server-scoped to the manager's own project departments.
class PmsVehicleFileScreen extends StatefulWidget {
  const PmsVehicleFileScreen({super.key, required this.vehicleId, required this.name});
  final int vehicleId;
  final String name;
  @override
  State<PmsVehicleFileScreen> createState() => _PmsVehicleFileScreenState();
}

class _PmsVehicleFileScreenState extends State<PmsVehicleFileScreen> {
  Future<Map<String, dynamic>>? _f;
  static const _c = Color(0xFFF7A23B);

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.pmsVehicleFile(widget.vehicleId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: _c, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.name, overflow: TextOverflow.ellipsis),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Padding(
              padding: const EdgeInsets.all(30),
              child: Text('${snap.error}', textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.grey)),
            ));
          }
          final d = snap.data ?? const {};
          final v = (d['vehicle'] as Map?) ?? const {};
          final fuel = (d['fuel'] as List?) ?? const [];
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            _identity(v, (d['fuel_total'] ?? 0)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white, borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: const [
                  Icon(Icons.local_gas_station_rounded, size: 15, color: Color(0xFFF7A23B)),
                  SizedBox(width: 6),
                  Text('سجل الوقود', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Pms.ink)),
                ]),
                const SizedBox(height: 4),
                MoreList(
                  items: fuel,
                  color: _c,
                  pageSize: 8,
                  emptyText: tr('لا تعبئات مسجّلة.', 'No fuel records.'),
                  itemBuilder: (_, r, __) {
                    final m = r as Map;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 5),
                      child: Row(children: [
                        const Icon(Icons.local_gas_station_outlined, size: 15, color: Color(0xFFF7A23B)),
                        const SizedBox(width: 8),
                        Expanded(child: Text('${m['date'] ?? '—'}',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
                        if (m['odometer'] != null)
                          Text(tr('${m['odometer']} كم', '${m['odometer']} km'),
                              style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
                        const SizedBox(width: 8),
                        Text(tr('${m['liters']} لتر', '${m['liters']} L'),
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: Color(0xFFF7A23B))),
                      ]),
                    );
                  },
                ),
              ]),
            ),
          ]);
        },
      ),
    );
  }

  Widget _identity(Map v, dynamic fuelTotal) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_c, Color.lerp(_c, Colors.black, 0.32)!],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 48, height: 48, alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(14)),
              child: const Icon(Icons.directions_car_rounded, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${v['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 15.5, fontWeight: FontWeight.w900)),
              if (v['plate'] != null)
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                      color: Colors.white, borderRadius: BorderRadius.circular(6)),
                  child: Text('${v['plate']}',
                      style: const TextStyle(color: Color(0xFF0E3A5F), fontSize: 12, fontWeight: FontWeight.w900)),
                ),
            ])),
          ]),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (v['model'] != null) _chip(Icons.category_rounded, '${v['model']}'),
            if (v['driver'] != null) _chip(Icons.person_rounded, '${v['driver']}'),
            if (v['department'] != null) _chip(Icons.apartment_rounded, '${v['department']}'),
            if (v['odometer'] != null) _chip(Icons.speed_rounded, tr('${v['odometer']} كم', '${v['odometer']} km')),
            _chip(Icons.local_gas_station_rounded, tr('إجمالي: $fuelTotal لتر', 'Total: $fuelTotal L')),
          ]),
        ]),
      );

  Widget _chip(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(9)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 12, color: Colors.white),
          const SizedBox(width: 5),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      );
}
