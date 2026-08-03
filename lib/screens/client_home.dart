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
import 'live_stream_banner.dart';
import 'manage_screen.dart';
import 'requests_screen.dart';
import 'quality_screen.dart';
import 'shop_screen.dart';
import 'orders_screen.dart';
import 'invoices_screen.dart';
import 'client_security_screen.dart';
import 'client_agri_screen.dart';
import 'maintenance_screen.dart';
import 'valet_screen.dart';
import 'hospitality_screen.dart';
import 'specialty_service_screen.dart';
import 'handling_screen.dart';
import 'client_cleaning_screen.dart';
import 'client_facade_screen.dart';
import 'client_inventory_screen.dart';
import 'client_assets_screen.dart';
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
              return ListView(children: [const SizedBox(height: 120), Center(child: Text(tr('خطأ: ${snap.error}', 'Error: ${snap.error}'), style: TextStyle(color: cs.outline)))]);
            }
            final d = snap.data!;
            final k = (d['kpis'] as Map);
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
              children: [
                _hero(d, k, cs),
                const SizedBox(height: 10),
                const LiveStreamBanner(isClient: true),
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
          const SizedBox(width: 10),
          // A live, pulsing count of people actually on site — the thing a client
          // asks first thing in the morning. Fixed-width column so it never
          // crowds the client name beside it.
          SizedBox(
            width: 62,
            child: Column(children: [
              PulseBadge(
                color: present > 0 ? const Color(0xFF34D399) : Colors.white,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                      color: (present > 0 ? const Color(0xFF16A34A) : Colors.white).withValues(alpha: present > 0 ? 0.95 : 0.14),
                      borderRadius: BorderRadius.circular(20)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 6, height: 6, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle)),
                    const SizedBox(width: 5),
                    Text('$present', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w900)),
                  ]),
                ),
              ),
              const SizedBox(height: 4),
              Text(tr('بالموقع', 'on site'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.6), fontSize: 8.5, fontWeight: FontWeight.w700)),
            ]),
          ),
        ]),
        // Only surfaces when something is actually late — an always-on banner
        // stops being read.
        if (overdue > 0) ...[
          const SizedBox(height: 11),
          InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: () => _go(const ClientWorkOrdersScreen(initialFilter: 'overdue')),
            child: Container(
              // On the red header a red alert disappears — use a distinctive
              // amber so overdue work reads instantly.
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
              decoration: BoxDecoration(
                  color: const Color(0xFFFBBF24),
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: [BoxShadow(color: const Color(0xFFB45309).withValues(alpha: 0.35), blurRadius: 8, offset: const Offset(0, 3))]),
              child: Row(children: [
                const Icon(Icons.warning_amber_rounded, color: Color(0xFF7C2D12), size: 17),
                const SizedBox(width: 7),
                Expanded(child: Text(tr('$overdue أمر عمل تجاوز موعده', '$overdue work orders overdue'),
                    style: const TextStyle(color: Color(0xFF7C2D12), fontSize: 12, fontWeight: FontWeight.w900))),
                const Icon(Icons.chevron_left_rounded, color: Color(0xFF7C2D12), size: 18),
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
      (Icons.fact_check_outlined, tr('الجودة', 'Quality'), 'Quality', const Color(0xFF16A34A), const QualityScreen()),
      (Icons.description_outlined, tr('العقود', 'Contracts'), 'Contracts', const Color(0xFF6366F1), const ContractsScreen()),
      if (p.canAddWorkers)
        (Icons.settings_suggest_outlined, tr('إدارة المنشأة', 'Facility management'), 'Manage', const Color(0xFFF59E0B), const ManageScreen()),
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
    // Twenty-five identical tinted squares in one grid gave a service the same
    // weight as a shortcut, so nothing led. They are grouped now, and each
    // group is drawn the way its job deserves.
    // (emoji, ar, en, colour, screen, sectionCode) — sectionCode null = always
    final act = <(IconData, String, String, int, Widget, String?)>[
      (Icons.add_task_rounded, 'طلب خدمة', 'Request', 0xFFC0392B, const RequestsScreen(), null),
      (Icons.verified_rounded, 'الجودة', 'Quality', 0xFF16A34A, const QualityScreen(), null),
      (Icons.sensors_rounded, 'النشاط', 'Live', 0xFF0891B2, const ClientActivityScreen(), 'workorders'),
      (Icons.event_repeat_rounded, 'الجدولة', 'Schedules', 0xFF0D9488, const SchedulesScreen(), 'workorders'),
    ];
    final services = <(IconData, String, String, int, Widget, String?)>[
      (Icons.cleaning_services_rounded, 'النظافة', 'Cleaning', 0xFF0EA5E9, const ClientCleaningScreen(), 'cleaning'),
      (Icons.shield_rounded, 'الأمن', 'Security', 0xFFE11D48, const ClientSecurityScreen(), 'security'),
      (Icons.park_rounded, 'الزراعة', 'Landscaping', 0xFF16A34A, const ClientAgriScreen(), 'agriculture'),
      (Icons.apartment_rounded, 'الواجهات', 'Facade', 0xFF8B5CF6, const ClientFacadeScreen(), 'facade'),
      (Icons.handyman_rounded, 'الصيانة', 'Maintenance', 0xFFF59E0B, const MaintenanceScreen(), 'maintenance'),
      (Icons.recycling_rounded, 'النفايات', 'Waste', 0xFF16A34A, const ClientWasteScreen(), 'waste'),
      (Icons.local_cafe_rounded, 'الضيافة', 'Hospitality', 0xFF8A6D3B, const HospitalityScreen(), 'hospitality'),
      (Icons.directions_car_rounded, 'صف السيارات', 'Valet', 0xFFB45309, const ValetScreen(), 'valet'),
      (Icons.pest_control_rounded, 'مكافحة الحشرات', 'Pest', 0xFF7C3AED,
          const SpecialtyServiceScreen(spec: ServiceSpec.pest), 'pest'),
      (Icons.sanitizer_rounded, 'التعقيم', 'Disinfection', 0xFF0EA5A5,
          const SpecialtyServiceScreen(spec: ServiceSpec.disinfection), 'disinfection'),
      (Icons.pool_rounded, 'المسابح', 'Pools', 0xFF0891B2,
          const SpecialtyServiceScreen(spec: ServiceSpec.pool), 'pool'),
      (Icons.water_drop_rounded, 'خزانات المياه', 'Water tanks', 0xFF0E7A5F,
          const SpecialtyServiceScreen(spec: ServiceSpec.watertank), 'watertank'),
      (Icons.local_shipping_rounded, 'المناولة', 'Handling', 0xFF0D9488,
          const HandlingScreen(), 'handling'),
    ];
    final place = <(IconData, String, String, int, Widget, String?)>[
      (Icons.business_rounded, 'المباني', 'Buildings', 0xFF4F46E5, const ClientStructureScreen(), 'facilities'),
      (Icons.precision_manufacturing_rounded, 'الأصول', 'Assets', 0xFF0E7490, const ClientAssetsScreen(), null),
      (Icons.inventory_2_rounded, 'المخزون', 'Inventory', 0xFF7C3AED, const ClientInventoryScreen(), 'inventory'),
      (Icons.schedule_rounded, 'الحضور', 'Attendance', 0xFF0891B2, const AttendanceScreen(), 'team'),
      (Icons.groups_rounded, 'الفريق', 'Team', 0xFF2563EB, const ClientTeamScreen(), 'team'),
      (Icons.meeting_room_rounded, 'الإشغال', 'Occupancy', 0xFF0E7A5F, const OccupancyScreen(), 'facilities'),
      (Icons.insights_rounded, 'تحليلات المكان', 'Site analytics', 0xFF4338CA, const ClientAnalyticsScreen(), null),
      (Icons.campaign_rounded, 'إشعار', 'Notify', 0xFFDB2777, const NotifySendScreen(), null),
    ];
    final money = <(IconData, String, String, int, Widget, String?)>[
      (Icons.storefront_rounded, 'المتجر', 'Shop', 0xFF0EA5E9, const ShopScreen(), 'shop'),
      (Icons.receipt_long_rounded, 'طلباتي', 'Orders', 0xFFEA580C, const OrdersScreen(), null),
      (Icons.credit_card_rounded, 'الفواتير', 'Invoices', 0xFF9D174D, const InvoicesScreen(), null),
      (Icons.description_rounded, 'العقود', 'Contracts', 0xFF0B6EA8, const ContractsScreen(), null),
    ];

    List<T> vis<T extends (IconData, String, String, int, Widget, String?)>(List<T> l) =>
        l.where((s) => s.$6 == null || _has(s.$6!)).toList();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _groupTitle(tr('ابدأ من هنا', 'Start here')),
      _actionRow(vis(act)),
      const SizedBox(height: 18),
      _groupTitle(tr('خدماتك المتعاقدة', 'Your contracted services')),
      _serviceWrap(vis(services)),
      const SizedBox(height: 18),
      _groupTitle(tr('المكان والفريق', 'Place & people')),
      _compactGrid(vis(place)),
      const SizedBox(height: 18),
      _groupTitle(tr('المتجر والفواتير', 'Shop & billing')),
      _compactGrid(vis(money)),
    ]);
  }

  Widget _groupTitle(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(children: [
          Container(width: 3, height: 15,
              decoration: BoxDecoration(color: const Color(0xFFC0392B),
                  borderRadius: BorderRadius.circular(2))),
          const SizedBox(width: 8),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5,
              color: Color(0xFF14202B))),
        ]),
      );

  /// The things people came to do: full-width, high contrast, unmissable.
  Widget _actionRow(List<(IconData, String, String, int, Widget, String?)> items) => Row(
        children: [
          for (final s in items)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => _go(s.$5),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                          colors: [Color(s.$4), Color(s.$4).withValues(alpha: 0.78)],
                          begin: Alignment.topRight, end: Alignment.bottomLeft),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [BoxShadow(color: Color(s.$4).withValues(alpha: 0.28),
                          blurRadius: 10, offset: const Offset(0, 5))],
                    ),
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(s.$1, size: 24, color: Colors.white),
                      const SizedBox(height: 7),
                      Text(tr(s.$2, s.$3), textAlign: TextAlign.center, maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900,
                              fontSize: 11.5)),
                    ]),
                  ),
                ),
              ),
            ),
        ],
      );

  /// Services read as a row of cards carrying their own colour on a leading
  /// stripe — a contracted service is not a shortcut and should not look like one.
  /// Services fill the row in two even columns — a fixed-width Wrap left a
  /// ragged gap down the side and made the section look unfinished.
  Widget _serviceWrap(List<(IconData, String, String, int, Widget, String?)> items) =>
      GridView.count(
        crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 9, mainAxisSpacing: 9, childAspectRatio: 3.0,
        children: [
          for (final s in items)
            InkWell(
              borderRadius: BorderRadius.circular(13),
              onTap: () => _go(s.$5),
              child: Container(
                padding: const EdgeInsets.fromLTRB(11, 10, 10, 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(13),
                  border: Border.all(color: Colors.grey.shade200),
                  boxShadow: const [BoxShadow(color: Color(0x0D000000), blurRadius: 6,
                      offset: Offset(0, 2))],
                ),
                child: Row(children: [
                  Container(width: 3.5, height: 30,
                      decoration: BoxDecoration(color: Color(s.$4),
                          borderRadius: BorderRadius.circular(3))),
                  const SizedBox(width: 10),
                  Icon(s.$1, size: 19, color: Color(s.$4)),
                  const SizedBox(width: 9),
                  Expanded(
                    child: Text(tr(s.$2, s.$3), maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5,
                            height: 1.2, color: Color(s.$4))),
                  ),
                ]),
              ),
            ),
        ],
      );

  /// Supporting destinations. These were flat grey boxes with a small grey
  /// icon — uniform to the point of being unreadable at a glance, because
  /// nothing distinguished one from the next. Each now carries its own colour
  /// in a proper icon chip, on a white card, at a size you can actually see.
  Widget _compactGrid(List<(IconData, String, String, int, Widget, String?)> items) =>
      GridView.count(
        crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        crossAxisSpacing: 9, mainAxisSpacing: 9, childAspectRatio: 0.86,
        children: [
          for (final s in items)
            InkWell(
              borderRadius: BorderRadius.circular(15),
              onTap: () => _go(s.$5),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: Colors.grey.shade200),
                  boxShadow: const [BoxShadow(color: Color(0x0D000000), blurRadius: 6,
                      offset: Offset(0, 2))],
                ),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Container(
                    width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color(s.$4).withValues(alpha: 0.16),
                                 Color(s.$4).withValues(alpha: 0.07)],
                        begin: Alignment.topRight, end: Alignment.bottomLeft,
                      ),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: Icon(s.$1, size: 23, color: Color(s.$4)),
                  ),
                  const SizedBox(height: 7),
                  Text(tr(s.$2, s.$3), textAlign: TextAlign.center, maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11,
                          color: Color(0xFF14202B))),
                ]),
              ),
            ),
        ],
      );

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
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      childAspectRatio: 1.02,
      children: [for (final it in items) _estateCard(it.$1, it.$2 as int, it.$3, it.$4, it.$5)],
    );
  }

  /// A polished estate tile: a tinted card with a gradient icon badge, a large
  /// figure and a corner accent — reads as a premium stat, not a plain button.
  Widget _estateCard(String label, int value, Color c, IconData ic, VoidCallback onTap) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: c.withValues(alpha: 0.18)),
          boxShadow: [BoxShadow(color: c.withValues(alpha: 0.10), blurRadius: 9, offset: const Offset(0, 4))],
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(children: [
          // soft corner accent
          Positioned(top: -14, left: -14, child: Container(
            width: 46, height: 46,
            decoration: BoxDecoration(shape: BoxShape.circle, color: c.withValues(alpha: 0.08)),
          )),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(
                width: 42, height: 42, alignment: Alignment.center,
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.28)!],
                      begin: Alignment.topRight, end: Alignment.bottomLeft),
                  borderRadius: BorderRadius.circular(13),
                  boxShadow: [BoxShadow(color: c.withValues(alpha: 0.35), blurRadius: 7, offset: const Offset(0, 3))],
                ),
                child: Icon(ic, color: Colors.white, size: 22),
              ),
              const SizedBox(height: 8),
              Text('$value', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: c, height: 1)),
              const SizedBox(height: 1),
              Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: Color(0xFF334155))),
            ]),
          ),
        ]),
      ),
    );
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
          subtitle: Text(tr('${f['address'] ?? ''}\nمباني: ${f['buildings']} · مواقع: ${f['locations']} · أعمال مفتوحة: ${f['open_workorders']}', '${f['address'] ?? ''}\nBuildings: ${f['buildings']} · Locations: ${f['locations']} · Open work: ${f['open_workorders']}'),
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

  /// Each service opens its OWN dedicated page (header stats + teams + records
  /// for that service), not the shared analytics dashboard.
  void _openService(String type) {
    switch (type) {
      case 'security':
        _go(const ClientSecurityScreen()); break;
      case 'cleaning':
        _go(const ClientCleaningScreen()); break;
      case 'agriculture':
      case 'landscape':
        _go(const ClientAgriScreen()); break;
      case 'facade':
        _go(const ClientFacadeScreen()); break;
      case 'waste':
        _go(const ClientWasteScreen()); break;
      default:
        // maintenance / general services → the service's work orders, filtered.
        _go(ClientWorkOrdersScreen(initialFilter: 'all', serviceType: type));
    }
  }

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
              onTap: () => _openService('${m['type']}'),
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
          subtitle: Text(tr('${t['service'] ?? ''} · مشرف: ${t['supervisor'] ?? '—'} · أعضاء: ${t['members']}', '${t['service'] ?? ''} · Supervisor: ${t['supervisor'] ?? '—'} · Members: ${t['members']}'),
              style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
          // Open the team page focused on this team's service block.
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => ClientTeamScreen(focusTeamId: t['id'] as int?))),
        ),
      );

  /// One wrench for every service told the reader nothing — a cleaning job
  /// and a security incident looked identical in the list they scan fastest.
  static const _svcIcon = <String, (IconData, int)>{
    'cleaning': (Icons.cleaning_services_rounded, 0xFF0EA5E9),
    'security': (Icons.shield_rounded, 0xFFE11D48),
    'agriculture': (Icons.park_rounded, 0xFF16A34A),
    'landscape': (Icons.park_rounded, 0xFF16A34A),
    'maintenance': (Icons.handyman_rounded, 0xFF1E5F8C),
    'facade': (Icons.apartment_rounded, 0xFF8B5CF6),
    'waste': (Icons.recycling_rounded, 0xFF16A34A),
    'hospitality': (Icons.local_cafe_rounded, 0xFF8A6D3B),
    'valet': (Icons.directions_car_rounded, 0xFFB45309),
    'pest': (Icons.pest_control_rounded, 0xFF7C3AED),
    'pool': (Icons.pool_rounded, 0xFF0891B2),
    'watertank': (Icons.water_drop_rounded, 0xFF0EA5E9),
    'disinfection': (Icons.sanitizer_rounded, 0xFF0EA5A5),
  };

  Widget _woCard(Map w, ColorScheme cs) {
    final sv = _svcIcon['${w['service_type'] ?? ''}'] ??
        (Icons.build_circle_outlined, 0xFF64748B);
    return Card(
        child: ListTile(
          dense: true,
          leading: Container(
            width: 34, height: 34,
            decoration: BoxDecoration(
                color: Color(sv.$2).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10)),
            child: Icon(sv.$1, size: 18, color: Color(sv.$2)),
          ),
          title: Text('${w['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${w['service_type']} · ${w['facility']}',
              style: TextStyle(color: cs.outline, fontSize: 12)),
          trailing: WoStateBadge('${w['state']}'),
          onTap: () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => WorkOrderDetailScreen(id: w['id'] as int, title: '${w['title']}'))),
        ),
      );
  }
}
