import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_requests.dart';
import 'garage_browse.dart';

const kGrgNavy = Color(0xFF0A1F44);
const kGrgGold = Color(0xFFC9A227);
const kGrgBg = Color(0xFFF4F6FA);
const kGrgInk = Color(0xFF1F2A37);
const kGrgGrey = Color(0xFF6B7A8D);

String grgNum(dynamic v) {
  final d = (v as num?)?.toDouble() ?? 0;
  if (d >= 1000000) return '${(d / 1000000).toStringAsFixed(1)}M';
  if (d >= 1000) return '${(d / 1000).toStringAsFixed(1)}K';
  return d % 1 == 0 ? d.toInt().toString() : d.toStringAsFixed(1);
}

/// الشاشة الرئيسية لإدارة الكراج في التطبيق — مؤشّرات + تنقّل للأقسام.
class GarageHome extends StatefulWidget {
  const GarageHome({super.key});
  @override
  State<GarageHome> createState() => _GarageHomeState();
}

class _GarageHomeState extends State<GarageHome> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map<String, dynamic>? _d;
  String _role = '';
  bool _loading = true;
  bool _denied = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final me = await _api.grgMe();
      _role = '${me['role'] ?? ''}';
      final d = await _api.grgDashboard();
      if (mounted) setState(() => _d = d);
    } on ApiException catch (e) {
      if (mounted) setState(() => _denied = e.status == 403);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  String _roleLabel(String r) {
    switch (r) {
      case 'fleet_manager':
        return tr('مدير الفليت', 'Fleet manager');
      case 'manager':
        return tr('مدير الكراج', 'Garage manager');
      case 'coordinator':
        return tr('منسّق', 'Coordinator');
      default:
        return tr('فنّي', 'Technician');
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('إدارة الكراج', 'Garage')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
          : _denied
              ? Center(
                  child: Padding(
                  padding: const EdgeInsets.all(28),
                  child: Text(tr('هذا الحساب ليس من طاقم الكراج.', 'This account is not garage staff.'),
                      textAlign: TextAlign.center, style: const TextStyle(color: kGrgGrey, fontSize: 14)),
                ))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.fromLTRB(12, 14, 12, 28), children: [
                    _hero(),
                    const SizedBox(height: 16),
                    _kpis(),
                    const SizedBox(height: 18),
                    _navGrid(),
                  ]),
                ),
    );
  }

  Widget _hero() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [kGrgNavy, Color(0xFF12306E)]),
          borderRadius: BorderRadius.circular(16)),
      child: Row(children: [
        const Text('🏭', style: TextStyle(fontSize: 30)),
        const SizedBox(width: 12),
        Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('إدارة الكراج', 'Garage Management'),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          const SizedBox(height: 3),
          Text(tr('صيانة الأسطول · المستهلكات · الفنّيون', 'Fleet service · consumables · technicians'),
              style: const TextStyle(color: Colors.white70, fontSize: 11.5)),
        ])),
        if (_role.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
            child: Text(_roleLabel(_role),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11.5)),
          ),
      ]),
    );
  }

  Widget _kpis() {
    final d = _d ?? const {};
    final tiles = <(String, dynamic, Color, String)>[
      (tr('المركبات', 'Vehicles'), d['vehicles'], const Color(0xFF334155), '🚐'),
      (tr('طلبات مفتوحة', 'Open'), d['open_requests'], const Color(0xFFE08A00), '🧰'),
      (tr('متأخرة صيانة', 'Overdue'), d['overdue'], const Color(0xFFDC3030), '⏰'),
      (tr('طلبات الشهر', 'This month'), d['month_requests'], const Color(0xFF2563EB), '🗓️'),
      (tr('الفنّيون', 'Technicians'), d['tech_total'], const Color(0xFF7C3AED), '👨‍🔧'),
      (tr('قطع مركّبة', 'Installed'), d['installed_parts'], const Color(0xFF0E8A8A), '🔩'),
    ];
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 0.98,
      children: tiles
          .map((t) => Container(
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE2E8F0))),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(t.$4, style: const TextStyle(fontSize: 17)),
                  const Spacer(),
                  Text(grgNum(t.$2), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 21, color: t.$3)),
                  Text(t.$1, style: const TextStyle(color: kGrgGrey, fontSize: 10.5, fontWeight: FontWeight.w600)),
                ]),
              ))
          .toList(),
    );
  }

  Widget _navGrid() {
    final navs = <(IconData, String, Color, Widget)>[
      (Icons.build_circle_rounded, tr('طلبات الصيانة', 'Maintenance'), const Color(0xFFE08A00), const GarageRequestsScreen()),
      (Icons.directions_bus_rounded, tr('المركبات', 'Vehicles'), const Color(0xFF334155), const GarageVehiclesScreen()),
      (Icons.engineering_rounded, tr('الفنّيون', 'Technicians'), const Color(0xFF7C3AED), const GarageTechniciansScreen()),
      (Icons.inventory_2_rounded, tr('الأصناف', 'Items'), const Color(0xFF0E8A8A), const GarageItemsScreen()),
      (Icons.report_gmailerrorred_rounded, tr('القطع التالفة', 'Damaged parts'), const Color(0xFFDC3030),
          const GaragePartsScreen(state: 'damaged', title: 'القطع التالفة', titleEn: 'Damaged parts')),
      (Icons.gavel_rounded, tr('لجان الإتلاف', 'Disposals'), const Color(0xFF7A1020), const GarageDisposalsScreen()),
    ];
    return Column(children: [
      Align(
          alignment: Alignment.centerRight,
          child: Padding(
              padding: const EdgeInsets.only(right: 4, bottom: 8),
              child: Text(tr('الأقسام', 'Sections'),
                  style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy, fontSize: 14)))),
      ...navs.map((n) => Padding(
            padding: const EdgeInsets.only(bottom: 9),
            child: Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              child: ListTile(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                leading: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: n.$3.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                    child: Icon(n.$1, color: n.$3, size: 21)),
                title: Text(n.$2, style: const TextStyle(fontWeight: FontWeight.w700, color: kGrgInk)),
                trailing: const Icon(Icons.chevron_left_rounded, color: Color(0xFF64748B)),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => n.$4)),
              ),
            ),
          )),
    ]);
  }
}
