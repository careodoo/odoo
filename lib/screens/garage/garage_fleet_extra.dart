import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_home.dart' show kGrgNavy, kGrgBg, kGrgInk, kGrgGrey;

Color _sevColor(String s) {
  if (s.contains('جسيم') || s.toLowerCase().contains('crit')) return const Color(0xFFDC3030);
  if (s.contains('متوسّط') || s.toLowerCase().contains('major')) return const Color(0xFFE08A00);
  return const Color(0xFF2563EB);
}

// ============ D8 — فحص الفرق (عرض) ============
class GarageInspectionsScreen extends StatefulWidget {
  const GarageInspectionsScreen({super.key});
  @override
  State<GarageInspectionsScreen> createState() => _GarageInspectionsScreenState();
}

class _GarageInspectionsScreenState extends State<GarageInspectionsScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.grgInspections();
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('فحص الفرق بين تسليمين', 'Inspections')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _rows.isEmpty
              ? Center(child: Text(tr('لا توجد فحوصات', 'No inspections'), style: const TextStyle(color: kGrgGrey)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
                    itemCount: _rows.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final r = _rows[i] as Map;
                      return Material(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        child: ListTile(
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => _InspectionDetail(id: (r['id'] as num).toInt()))),
                          leading: Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(color: kGrgNavy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(11)),
                            child: const Icon(Icons.search_rounded, color: kGrgNavy),
                          ),
                          title: Text('${r['name']} · ${r['vehicle']}', style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk)),
                          subtitle: Text('${tr('أعطال', 'Faults')}: ${r['fault_count']}  ·  ${tr('تقدير', 'Est.')}: ${r['total_cost']}',
                              style: const TextStyle(color: kGrgGrey, fontSize: 12)),
                          trailing: Text('${r['km_diff']} ${tr('كم', 'km')}', style: const TextStyle(color: kGrgGrey, fontWeight: FontWeight.w700)),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}

class _InspectionDetail extends StatefulWidget {
  final int id;
  const _InspectionDetail({required this.id});
  @override
  State<_InspectionDetail> createState() => _InspectionDetailState();
}

class _InspectionDetailState extends State<_InspectionDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _d;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _api.grgInspection(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text(tr('تفاصيل الفحص', 'Inspection'))),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(gradient: const LinearGradient(colors: [kGrgNavy, Color(0xFF14306B)]), borderRadius: BorderRadius.circular(16)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${d['name']} · ${d['vehicle']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
                  const SizedBox(height: 6),
                  Text('${tr('السابق', 'Before')}: ${d['driver_before']}  →  ${tr('الحالي', 'After')}: ${d['driver_after']}',
                      style: const TextStyle(color: Colors.white70, fontSize: 12)),
                  const SizedBox(height: 4),
                  Text('${tr('المسافة', 'Distance')}: ${d['km_diff']} ${tr('كم', 'km')}  ·  ${tr('إجمالي التقدير', 'Total')}: ${d['total_cost']}',
                      style: const TextStyle(color: Colors.white)),
                ]),
              ),
              const SizedBox(height: 12),
              Text(tr('الأعطال المرصودة', 'Faults'), style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy)),
              const SizedBox(height: 8),
              ...((d['faults'] as List?) ?? []).map((f) {
                final m = f as Map;
                final sev = (m['severity'] ?? '').toString();
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    Container(width: 5, height: 40, decoration: BoxDecoration(color: _sevColor(sev), borderRadius: BorderRadius.circular(4))),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(m['name'].toString(), style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk)),
                        Text('${m['side']} · ${m['responsible']}', style: const TextStyle(color: kGrgGrey, fontSize: 12)),
                      ]),
                    ),
                    Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                      Text(sev, style: TextStyle(color: _sevColor(sev), fontWeight: FontWeight.w800, fontSize: 12)),
                      Text('${m['cost']}', style: const TextStyle(color: kGrgInk, fontWeight: FontWeight.w700)),
                    ]),
                  ]),
                );
              }),
              if ((d['notes'] ?? '').toString().isNotEmpty) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                  child: Text(d['notes'].toString()),
                ),
              ],
            ]),
    );
  }
}

// ============ D7 — صرف التأمين (عرض) ============
class GarageInsuranceScreen extends StatefulWidget {
  const GarageInsuranceScreen({super.key});
  @override
  State<GarageInsuranceScreen> createState() => _GarageInsuranceScreenState();
}

class _GarageInsuranceScreenState extends State<GarageInsuranceScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.grgInsuranceRequests();
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('صرف التأمين', 'Insurance')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _rows.isEmpty
              ? Center(child: Text(tr('لا توجد طلبات', 'No requests'), style: const TextStyle(color: kGrgGrey)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
                    itemCount: _rows.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final r = _rows[i] as Map;
                      return Material(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                        child: ListTile(
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => _InsuranceDetail(id: (r['id'] as num).toInt()))),
                          leading: Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(11)),
                            child: const Icon(Icons.shield_rounded, color: Color(0xFF16A34A)),
                          ),
                          title: Text('${r['name']} · ${r['type']}', style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk)),
                          subtitle: Text('${r['vehicle_count']} ${tr('مركبة', 'vehicles')}  ·  ${r['total']} ${tr('د.ك', 'KWD')}',
                              style: const TextStyle(color: kGrgGrey, fontSize: 12)),
                          trailing: Text((r['state_label'] ?? '').toString(), style: const TextStyle(color: kGrgGrey, fontSize: 11, fontWeight: FontWeight.w700)),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}

class _InsuranceDetail extends StatefulWidget {
  final int id;
  const _InsuranceDetail({required this.id});
  @override
  State<_InsuranceDetail> createState() => _InsuranceDetailState();
}

class _InsuranceDetailState extends State<_InsuranceDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _d;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _api.grgInsuranceRequest(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text(tr('طلب صرف تأمين', 'Insurance request'))),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(gradient: const LinearGradient(colors: [kGrgNavy, Color(0xFF14306B)]), borderRadius: BorderRadius.circular(16)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${d['name']} · ${d['type']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
                  const SizedBox(height: 6),
                  Text('${tr('الإجمالي', 'Total')}: ${d['total']} ${tr('د.ك', 'KWD')}  ·  ${d['vehicle_count']} ${tr('مركبة', 'vehicles')}',
                      style: const TextStyle(color: Colors.white)),
                  if ((d['custody'] ?? '').toString().isNotEmpty)
                    Text('${tr('العهدة', 'Custody')}: ${d['custody']}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
                ]),
              ),
              const SizedBox(height: 12),
              Text(tr('المركبات', 'Vehicles'), style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy)),
              const SizedBox(height: 8),
              ...((d['lines'] as List?) ?? []).map((l) {
                final m = l as Map;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(m['vehicle'].toString(), style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk)),
                        Text('${m['body_type']} · ${tr('بوليصة', 'Policy')}: ${m['policy']}', style: const TextStyle(color: kGrgGrey, fontSize: 12)),
                      ]),
                    ),
                    Text('${m['amount']}', style: const TextStyle(color: kGrgInk, fontWeight: FontWeight.w800)),
                  ]),
                );
              }),
            ]),
    );
  }
}
