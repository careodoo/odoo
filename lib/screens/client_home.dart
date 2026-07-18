import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../models/models.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'facility_detail_screen.dart';
import 'work_order_detail_screen.dart';
import 'client_team_screen.dart';
import 'client_activity_screen.dart';
import 'client_structure_screen.dart';
import 'client_analytics_screen.dart';
import 'client_services_screen.dart';
import 'client_workorders_screen.dart';
import 'contracts_screen.dart';
import 'manage_screen.dart';
import 'requests_screen.dart';
import 'quality_screen.dart';
import 'shop_screen.dart';
import 'orders_screen.dart';
import 'invoices_screen.dart';
import 'client_security_screen.dart';
import 'client_agri_screen.dart';
import 'client_cleaning_screen.dart';
import 'client_facade_screen.dart';
import 'client_inventory_screen.dart';
import 'client_waste_screen.dart';
import 'schedules_screen.dart';
import 'attendance_screen.dart';
import 'notify_send_screen.dart';
import 'occupancy_screen.dart';

/// The client's cockpit — everything the module holds for this customer:
/// buildings, services, teams, live work-order activity. Fully data-driven, so
/// anything added in the backend appears here automatically.
class ClientHome extends StatefulWidget {
  const ClientHome({super.key});
  @override
  State<ClientHome> createState() => _ClientHomeState();
}

class _ClientHomeState extends State<ClientHome> {
  late Future<Map<String, dynamic>> _future;
  Set<String> _sections = {}; // enabled portal-section codes for this client
  List<dynamic> _facilities = const [];

  @override
  void initState() {
    super.initState();
    _load();
    _loadSections();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientOverview();

  Future<void> _loadSections() async {
    try {
      final s = await context.read<AuthProvider>().api.clientSections();
      if (mounted) setState(() => _sections = Set<String>.from((s['codes'] as List?)?.map((e) => '$e') ?? const []));
    } catch (_) {/* on failure, show everything (no restriction) */}
  }

  /// Section gate — before sections load (empty set) everything shows; once
  /// loaded, only enabled codes show. Always-on codes are included by the API.
  bool _has(String code) => _sections.isEmpty || _sections.contains(code);

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('بوابة العميل', 'Client portal')),
        actions: [
          NotifBell(unread: p.unreadNotifications),
          IconButton(icon: const Icon(Icons.logout), onPressed: () => context.read<AuthProvider>().logout()),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [const SizedBox(height: 120), Center(child: Text('خطأ: ${snap.error}', style: TextStyle(color: cs.outline)))]);
            }
            final d = snap.data!;
            final k = (d['kpis'] as Map);
            _facilities = (d['facilities'] as List?) ?? const [];
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              children: [
                _hero(d, k, cs),
                const SizedBox(height: 10),
                _miniBar(p),
                const SizedBox(height: 14),
                _cockpit(k),
                const SizedBox(height: 14),
                _quickAccess(cs),
                const SizedBox(height: 14),
                _building3dCard(),
                const SizedBox(height: 18),
                if (_has('facilities')) ...[
                  _section(tr('مبانيي ومرافقي', 'My buildings & facilities')),
                  for (final f in (d['facilities'] as List)) _facilityCard(f as Map, cs),
                  const SizedBox(height: 16),
                ],
                _section(tr('الخدمات المقدَّمة', 'Services provided')),
                _servicesWrap(d['services'] as List),
                const SizedBox(height: 16),
                if (_has('team')) ...[
                  _section(tr('فِرَق العمل', 'Teams'), onMore: () => _go(const ClientTeamScreen())),
                  for (final t in (d['teams'] as List)) _teamCard(t as Map, cs),
                  const SizedBox(height: 16),
                ],
                if (_has('workorders')) ...[
                  _section(tr('آخر الأعمال', 'Recent work'), onMore: () => _go(const ClientWorkOrdersScreen(initialFilter: 'all'))),
                  for (final w in (d['recent_workorders'] as List)) _woCard(w as Map, cs),
                ],
                const SizedBox(height: 24),
              ],
            );
          },
        ),
      ),
    );
  }

  /// The client identity band. It carries what the account actually is —
  /// contact, sites, and whether anything is on fire right now — instead of
  /// just repeating the name.
  Widget _hero(Map d, Map k, ColorScheme cs) {
    final client = d['client']?.toString() ?? '';
    final contact = d['contact']?.toString() ?? '';
    final overdue = (k['overdue'] ?? 0) as int;
    final present = (k['present_now'] ?? 0) as int;
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
            colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: const Color(0xFFC0392B).withValues(alpha: 0.32), blurRadius: 14, offset: const Offset(0, 6))],
      ),
      clipBehavior: Clip.antiAlias,
      child: CustomPaint(
        painter: const BrandPattern(opacity: 0.07),
        child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 15, 16, 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 48, height: 48, alignment: Alignment.center,
            decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withValues(alpha: 0.22))),
            child: Text(client.isNotEmpty ? client.trim().characters.first : '🏢',
                style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(client, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 17.5, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Row(children: [
              Icon(Icons.person_outline_rounded, size: 11, color: Colors.white.withValues(alpha: 0.6)),
              const SizedBox(width: 3),
              Flexible(child: Text(contact.isEmpty ? tr('بوابة العميل', 'Client portal') : contact,
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 11.5, fontWeight: FontWeight.w600))),
              if ((d['client_ref'] ?? '').toString().isNotEmpty) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(5)),
                  child: Text('${d['client_ref']}',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 9, fontWeight: FontWeight.w700)),
                ),
              ],
            ]),
          ])),
          // A live pulse of people actually on site — the thing a client asks
          // first thing in the morning.
          Column(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              decoration: BoxDecoration(
                  color: (present > 0 ? const Color(0xFF16A34A) : Colors.white).withValues(alpha: present > 0 ? 0.9 : 0.14),
                  borderRadius: BorderRadius.circular(20)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 6, height: 6, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle)),
                const SizedBox(width: 5),
                Text('$present', style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w900)),
              ]),
            ),
            const SizedBox(height: 2),
            Text(tr('بالموقع', 'on site'),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.55), fontSize: 8.5, fontWeight: FontWeight.w700)),
          ]),
        ]),
        // Only surfaces when something is actually late — an always-on banner
        // stops being read.
        if (overdue > 0) ...[
          const SizedBox(height: 11),
          InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: () => _go(const ClientWorkOrdersScreen(initialFilter: 'overdue')),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
              decoration: BoxDecoration(
                  color: const Color(0xFFE5484D).withValues(alpha: 0.22),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: const Color(0xFFE5484D).withValues(alpha: 0.5))),
              child: Row(children: [
                const Icon(Icons.warning_amber_rounded, color: Color(0xFFFCA5A5), size: 15),
                const SizedBox(width: 7),
                Expanded(child: Text(tr('$overdue أمر عمل تجاوز موعده', '$overdue work orders overdue'),
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800))),
                const Icon(Icons.chevron_left_rounded, color: Colors.white70, size: 17),
              ]),
            ),
          ),
        ],
      ]),
        ),
      ),
    );
  }

  /// Quality / contracts / manage: secondary destinations, so they get a
  /// compact bar under the header rather than three full-width buttons whose
  /// labels collided on a small screen.
  Widget _miniBar(Profile p) {
    final items = <(IconData, String, String, Color, Widget)>[
      (Icons.fact_check_outlined, 'الجودة', 'Quality', const Color(0xFF16A34A), const QualityScreen()),
      (Icons.description_outlined, 'العقود', 'Contracts', const Color(0xFF6366F1), const ContractsScreen()),
      if (p.canAddWorkers)
        (Icons.settings_suggest_outlined, 'إدارة المنشأة', 'Manage', const Color(0xFFF59E0B), const ManageScreen()),
    ];
    return Row(children: [
      for (final it in items) ...[
        Expanded(child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => _go(it.$5),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            decoration: BoxDecoration(
              color: it.$4.withValues(alpha: 0.09),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: it.$4.withValues(alpha: 0.22)),
            ),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(it.$1, size: 15, color: it.$4),
              const SizedBox(width: 5),
              Flexible(child: Text(tr(it.$2, it.$3),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: it.$4, fontSize: 10.5, fontWeight: FontWeight.w800))),
            ]),
          ),
        )),
        if (it != items.last) const SizedBox(width: 8),
      ],
    ]);
  }

  /// The cockpit strip: the numbers a client manager checks first, each one a
  /// link to the records behind it.
  Widget _cockpit(Map k) {
    final open = (k['open_workorders'] ?? 0) as int;
    final overdue = (k['overdue'] ?? 0) as int;
    final urgent = (k['urgent'] ?? 0) as int;
    final doneMonth = (k['done_month'] ?? 0) as int;
    final sla = (k['sla_rate'] ?? 0) is num ? (k['sla_rate'] as num).toDouble() : 0.0;
    final completion = (k['completion_rate'] ?? 0) is num ? (k['completion_rate'] as num).toDouble() : 0.0;
    final avgH = (k['avg_hours'] ?? 0) is num ? (k['avg_hours'] as num).toDouble() : 0.0;
    return Column(children: [
      // headline row — work state
      Row(children: [
        _big(tr('أعمال مفتوحة', 'Open'), '$open', Icons.build_rounded, const Color(0xFFF7A23B),
            () => _go(const ClientWorkOrdersScreen(initialFilter: 'open'))),
        const SizedBox(width: 9),
        _big(tr('متأخرة', 'Overdue'), '$overdue', Icons.running_with_errors_rounded, const Color(0xFFE5484D),
            () => _go(const ClientWorkOrdersScreen(initialFilter: 'overdue'))),
        const SizedBox(width: 9),
        _big(tr('عاجلة', 'Urgent'), '$urgent', Icons.priority_high_rounded, const Color(0xFFDC2626),
            () => _go(const ClientWorkOrdersScreen(initialFilter: 'urgent'))),
        const SizedBox(width: 9),
        _big(tr('أُنجزت (الشهر)', 'Done (mo.)'), '$doneMonth', Icons.task_alt_rounded, const Color(0xFF16A34A),
            () => _go(const ClientWorkOrdersScreen(initialFilter: 'done'))),
      ]),
      const SizedBox(height: 9),
      // rate row — quality of service
      Row(children: [
        _gauge(tr('التزام SLA', 'SLA'), sla, const Color(0xFF16A34A)),
        const SizedBox(width: 9),
        _gauge(tr('نسبة الإنجاز', 'Completion'), completion, const Color(0xFF2F6DF6)),
        const SizedBox(width: 9),
        Expanded(child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _go(const ClientAnalyticsScreen()),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
            decoration: BoxDecoration(
                color: const Color(0xFF0891B2).withValues(alpha: 0.09),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFF0891B2).withValues(alpha: 0.2))),
            child: Column(children: [
              const Icon(Icons.timer_outlined, size: 15, color: Color(0xFF0891B2)),
              const SizedBox(height: 4),
              Text(avgH >= 24 ? tr('${(avgH / 24).toStringAsFixed(1)} يوم', '${(avgH / 24).toStringAsFixed(1)}d')
                              : tr('${avgH.toStringAsFixed(1)} س', '${avgH.toStringAsFixed(1)}h'),
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Color(0xFF0891B2))),
              Text(tr('متوسط الإنجاز', 'Avg. close'),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
            ]),
          ),
        )),
      ]),
      const SizedBox(height: 9),
      // estate row — what we look after. These open the records themselves.
      _kpiGrid(k),
    ]);
  }

  Widget _big(String label, String v, IconData ic, Color c, VoidCallback onTap) => Expanded(
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.22)!],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: c.withValues(alpha: 0.30), blurRadius: 7, offset: const Offset(0, 3))],
            ),
            child: Column(children: [
              Icon(ic, size: 15, color: Colors.white.withValues(alpha: 0.9)),
              const SizedBox(height: 3),
              Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 8.5, fontWeight: FontWeight.w700)),
            ]),
          ),
        ),
      );

  Widget _gauge(String label, double pct, Color c) => Expanded(
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _go(const ClientAnalyticsScreen()),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
            decoration: BoxDecoration(
                color: c.withValues(alpha: 0.09),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: c.withValues(alpha: 0.2))),
            child: Column(children: [
              SizedBox(
                width: 30, height: 30,
                child: Stack(alignment: Alignment.center, children: [
                  CircularProgressIndicator(
                      value: (pct / 100).clamp(0.0, 1.0), strokeWidth: 3.5,
                      backgroundColor: c.withValues(alpha: 0.15),
                      valueColor: AlwaysStoppedAnimation(c)),
                  Text('${pct.round()}',
                      style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: c)),
                ]),
              ),
              const SizedBox(height: 4),
              Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
            ]),
          ),
        ),
      );

  void _go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

  Widget _quickAccess(ColorScheme cs) {
    // (emoji, ar, en, color, screen, sectionCode) — sectionCode null = always
    final specs = <(String, String, String, int, Widget, String?)>[
      ('📥', 'طلب خدمة', 'Request', 0xFFE6295C, const RequestsScreen(), null),
      ('👷', 'الفريق', 'Team', 0xFF2F6DF6, const ClientTeamScreen(), 'team'),
      ('📡', 'النشاط', 'Live', 0xFF16A34A, const ClientActivityScreen(), 'workorders'),
      ('🏢', 'المباني', 'Buildings', 0xFF6366F1, const ClientStructureScreen(), 'facilities'),
      ('🛒', 'المتجر', 'Shop', 0xFF0EA5E9, const ShopScreen(), 'shop'),
      ('📦', 'طلباتي', 'Orders', 0xFFF59E0B, const OrdersScreen(), null),
      ('💳', 'الفواتير', 'Invoices', 0xFF7A1340, const InvoicesScreen(), null),
      ('✅', 'الجودة', 'Quality', 0xFF16A34A, const QualityScreen(), null),
      ('🛡️', 'الأمن', 'Security', 0xFFE11D48, const ClientSecurityScreen(), 'security'),
      ('🔁', 'الجدولة', 'Schedules', 0xFF0D9488, const SchedulesScreen(), 'workorders'),
      ('🕐', 'الحضور', 'Attendance', 0xFF0891B2, const AttendanceScreen(), 'team'),
      ('📣', 'إشعار', 'Notify', 0xFF6366F1, const NotifySendScreen(), null),
      ('🧼', 'النظافة', 'Cleaning', 0xFF0891B2, const ClientCleaningScreen(), 'cleaning'),
      ('🌳', 'الزراعة', 'Landscape', 0xFF15803D, const ClientAgriScreen(), 'agriculture'),
      ('🏙️', 'الواجهات', 'Facade', 0xFF8B5CF6, const ClientFacadeScreen(), 'facade'),
      ('📦', 'المخزون', 'Inventory', 0xFF0E3A5F, const ClientInventoryScreen(), 'inventory'),
      ('♻️', 'النفايات', 'Waste', 0xFF16A34A, const ClientWasteScreen(), 'waste'),
    ];
    final shown = specs.where((s) => s.$6 == null || _has(s.$6!)).toList();
    Widget tile((String, String, String, int, Widget, String?) s) {
      final c = Color(s.$4);
      return InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _go(s.$5),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(16)),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(s.$1, style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 6),
            Text(tr(s.$2, s.$3), style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12), textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis),
          ]),
        ),
      );
    }

    return GridView.count(
      crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 10, mainAxisSpacing: 10, childAspectRatio: 0.92,
      children: [for (final s in shown) tile(s)],
    );
  }

  Widget _kpiGrid(Map k) {
    final items = [
      (tr('المرافق', 'Facilities'), k['facilities'] ?? 0, const Color(0xFFC0392B), Icons.location_city_rounded, () => _go(const ClientStructureScreen(focus: 'facilities'))),
      (tr('المباني', 'Buildings'), k['buildings'] ?? 0, const Color(0xFFE67E22), Icons.apartment_rounded, () => _go(const ClientStructureScreen(focus: 'buildings'))),
      (tr('المواقع', 'Locations'), k['locations'] ?? 0, const Color(0xFF0EA5E9), Icons.pin_drop_rounded, () => _go(const ClientStructureScreen(focus: 'locations'))),
      (tr('العمال', 'Workers'), k['workers'] ?? 0, const Color(0xFF0D9488), Icons.engineering_rounded, () => _go(const ClientTeamScreen())),
      (tr('الخدمات', 'Services'), k['services'] ?? 0, const Color(0xFF16A34A), Icons.design_services_rounded, () => _go(const ClientServicesScreen())),
      (tr('الفِرَق', 'Teams'), k['teams'] ?? 0, const Color(0xFF14B8A6), Icons.groups_rounded, () => _go(const ClientTeamScreen())),
    ];
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 9,
      crossAxisSpacing: 9,
      childAspectRatio: 1.05,
      children: [for (final it in items) StatCard(label: it.$1, value: it.$2 as int, color: it.$3, icon: it.$4, onTap: it.$5)],
    );
  }

  /// Estate KPIs open the estate itself. With a single facility there is no
  /// list worth showing — go straight to that record.
  void _openEstate() {
    if (_facilities.length == 1) {
      final f = _facilities.first as Map;
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => FacilityDetailScreen(facilityId: f['id'] as int, name: '${f['name']}')));
    } else {
      _go(const ClientStructureScreen());
    }
  }

  /// A distinctive, prominent entry to the live 3D building view — with a
  /// pulsing "live" badge so it reads as a real-time feed.
  Widget _building3dCard() {
    return GestureDetector(
      onTap: () => _go(const OccupancyScreen()),
      child: CustomPaint(
        painter: const BrandPattern(opacity: 0.08),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 15, 14, 15),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF3B2F80), Color(0xFF4338CA), Color(0xFF1E1B4B)],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: const Color(0xFF4338CA).withValues(alpha: 0.35), blurRadius: 14, offset: const Offset(0, 7))],
          ),
          child: Row(children: [
            Container(
              width: 52, height: 52, alignment: Alignment.center,
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(15)),
              child: const Icon(Icons.view_in_ar_rounded, color: Colors.white, size: 30),
            ),
            const SizedBox(width: 13),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text(tr('المبنى ثلاثي الأبعاد', '3D building'),
                    style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: const Color(0xFFE5484D), borderRadius: BorderRadius.circular(20)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 6, height: 6, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle)),
                    const SizedBox(width: 4),
                    Text(tr('بث حي', 'LIVE'), style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                  ]),
                ),
              ]),
              const SizedBox(height: 3),
              Text(tr('إشغال المبنى والطوابق لحظياً', 'Live building & floor occupancy'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
            ])),
            const Icon(Icons.chevron_left_rounded, color: Colors.white70),
          ]),
        ),
      ),
    );
  }

  Widget _section(String t, {VoidCallback? onMore}) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Row(children: [
          Text(t, style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900)),
          const Spacer(),
          if (onMore != null)
            GestureDetector(
              onTap: onMore,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
                decoration: BoxDecoration(
                    color: const Color(0xFFC0392B).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(tr('المزيد', 'More'),
                      style: const TextStyle(color: Color(0xFFC0392B), fontWeight: FontWeight.w800, fontSize: 11.5)),
                  const Icon(Icons.chevron_left_rounded, color: Color(0xFFC0392B), size: 16),
                ]),
              ),
            ),
        ]),
      );

  Widget _facilityCard(Map f, ColorScheme cs) => Card(
        child: ListTile(
          leading: CircleAvatar(backgroundColor: cs.primaryContainer, child: const Icon(Icons.apartment)),
          title: Text('${f['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: Text('${f['address'] ?? ''}\nمباني: ${f['buildings']} · مواقع: ${f['locations']} · أعمال مفتوحة: ${f['open_workorders']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          isThreeLine: true,
          trailing: const Icon(Icons.chevron_left),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => FacilityDetailScreen(facilityId: f['id'] as int, name: '${f['name']}'))),
        ),
      );

  static const _svcStyle = {
    'security': (Color(0xFFE5484D), '🛡️'),
    'cleaning': (Color(0xFF0EA5E9), '🧹'),
    'agriculture': (Color(0xFF16A34A), '🌿'),
    'facade': (Color(0xFF7C3AED), '🏙️'),
    'maintenance': (Color(0xFFF59E0B), '🔧'),
  };

  Widget _servicesWrap(List services) {
    if (services.isEmpty) return const SizedBox.shrink();
    return GridView.count(
      crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 2.6,
      children: [
        for (final s in services)
          Builder(builder: (_) {
            final m = s as Map;
            final style = _svcStyle[m['type']] ?? (const Color(0xFF334155), '•');
            final c = style.$1;
            return InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => _go(const ClientAnalyticsScreen()),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [c.withValues(alpha: 0.16), c.withValues(alpha: 0.04)],
                      begin: Alignment.topLeft, end: Alignment.bottomRight),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: c.withValues(alpha: 0.3)),
                ),
                child: Row(children: [
                  Container(
                    width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(12)),
                    child: Text('${m['icon'] ?? style.$2}', style: const TextStyle(fontSize: 22)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${m['name']}',
                      style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 13.5), maxLines: 2, overflow: TextOverflow.ellipsis)),
                ]),
              ),
            );
          }),
      ],
    );
  }

  Widget _teamCard(Map t, ColorScheme cs) => Card(
        child: ListTile(
          dense: true,
          leading: const Icon(Icons.groups, color: Color(0xFF14B8A6)),
          title: Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${t['service'] ?? ''} · مشرف: ${t['supervisor'] ?? '—'} · أعضاء: ${t['members']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
          // Open the team page focused on this team's service block.
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => ClientTeamScreen(focusTeamId: t['id'] as int?))),
        ),
      );

  Widget _woCard(Map w, ColorScheme cs) => Card(
        child: ListTile(
          dense: true,
          leading: const Icon(Icons.build_circle_outlined),
          title: Text('${w['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${w['service_type']} · ${w['facility']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: WoStateBadge('${w['state']}'),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => WorkOrderDetailScreen(id: w['id'] as int, title: '${w['title']}'))),
        ),
      );
}
