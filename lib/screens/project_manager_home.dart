import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'live_stream_banner.dart';
// إدارة وخدمات ومتابعة (يُعاد استخدام شاشات المشرف/العميل القائمة)
import 'create_task_screen.dart';
import 'workorders_screen.dart';
import 'client_team_screen.dart';
import 'quality_screen.dart';
import 'schedules_screen.dart';
import 'requests_screen.dart';
import 'invoice_requests_screen.dart';
import 'maintenance_screen.dart';
import 'attendance_screen.dart';
import 'client_analytics_screen.dart';
import 'notify_send_screen.dart';
import 'chat_screen.dart';
import 'scan_screen.dart';
// أدوات العميل والمكان
import 'contracts_screen.dart';
import 'invoices_screen.dart';
import 'shop_screen.dart';
import 'orders_screen.dart';
import 'client_structure_screen.dart';
import 'client_activity_screen.dart';
import 'client_inventory_screen.dart';
import 'client_assets_screen.dart';
import 'occupancy_screen.dart';
import 'permits_screen.dart';
// أدوات الأمن لمدير مشروع الأمن (أيقونتان منفصلتان)
import 'security_supervisor_screen.dart';
import 'security_home.dart';

const _navy = Color(0xFF0E3A5F);
const _teal = Color(0xFF0D9488);

/// لوحة مدير المشروع: تجمع إدارة الخدمات والمتابعة (أدوات المشرف) + معظم أدوات
/// العميل (العقود/الفواتير/المتجر/المباني/الأصول) + بنر البثّ الأمني الحيّ.
class ProjectManagerHome extends StatefulWidget {
  const ProjectManagerHome({super.key});
  @override
  State<ProjectManagerHome> createState() => _ProjectManagerHomeState();
}

class _ProjectManagerHomeState extends State<ProjectManagerHome> {
  Map<String, dynamic>? _stats;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final s = await context.read<AuthProvider>().api.stats();
      if (mounted) setState(() => _stats = s); } catch (_) {}
  }

  int _n(List<String> keys) {
    final s = _stats;
    if (s == null) return 0;
    for (final k in keys) {
      final v = s[k];
      if (v is num) return v.toInt();
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    void go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

    final manage = <(IconData, String, Color, VoidCallback)>[
      (Icons.add_task_rounded, tr('مهمة جديدة', 'New task'), _teal, () => go(const CreateTaskScreen())),
      (Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'), _navy, () => go(const WorkOrdersScreen())),
      (Icons.groups_rounded, tr('الفريق', 'Team'), const Color(0xFF6366F1), () => go(const ClientTeamScreen())),
      (Icons.fact_check_rounded, tr('الجودة', 'Quality'), const Color(0xFF0EA5A4), () => go(const QualityScreen())),
      (Icons.event_repeat_rounded, tr('الجدولة', 'Schedules'), const Color(0xFF0D9488), () => go(const SchedulesScreen())),
      (Icons.inbox_rounded, tr('طلبات الخدمة', 'Requests'), const Color(0xFFE6295C), () => go(const RequestsScreen())),
      if (p.riCreator || p.riManager || p.riFinance)
        (Icons.request_quote_rounded, tr('طلبات الفواتير', 'Invoice requests'), const Color(0xFF123A6B), () => go(const InvoiceRequestsScreen())),
      (Icons.handyman_rounded, tr('الصيانة', 'Maintenance'), const Color(0xFFF7A23B), () => go(const MaintenanceScreen())),
      (Icons.fingerprint_rounded, tr('الحضور', 'Attendance'), const Color(0xFF7C3AED), () => go(const AttendanceScreen())),
      (Icons.insights_rounded, tr('التحليلات', 'Analytics'), const Color(0xFF2563EB), () => go(const ClientAnalyticsScreen())),
      (Icons.campaign_rounded, tr('إشعار الفريق', 'Notify'), const Color(0xFFEA580C), () => go(const NotifySendScreen())),
      (Icons.forum_rounded, tr('التواصل', 'Messages'), const Color(0xFF0E7490), () => go(const ChatHubScreen())),
      (Icons.qr_code_scanner_rounded, tr('مسح موقع', 'Scan'), const Color(0xFF0891B2), () => go(const ScanScreen())),
      (Icons.badge_rounded, tr('التصاريح', 'Permits'), const Color(0xFF9333EA), () => go(const PermitsScreen())),
    ];

    final clientTools = <(IconData, String, Color, VoidCallback)>[
      (Icons.apartment_rounded, tr('المباني والمواقع', 'Buildings'), const Color(0xFF334155), () => go(const ClientStructureScreen())),
      (Icons.podcasts_rounded, tr('النشاط الحيّ', 'Live activity'), const Color(0xFFDC2626), () => go(const ClientActivityScreen())),
      (Icons.description_rounded, tr('العقود', 'Contracts'), const Color(0xFF0369A1), () => go(const ContractsScreen())),
      (Icons.receipt_long_rounded, tr('الفواتير', 'Invoices'), const Color(0xFF15803D), () => go(const InvoicesScreen())),
      (Icons.storefront_rounded, tr('المتجر', 'Shop'), const Color(0xFF7C3AED), () => go(const ShopScreen())),
      (Icons.shopping_bag_rounded, tr('طلباتي', 'Orders'), const Color(0xFFB45309), () => go(const OrdersScreen())),
      (Icons.inventory_2_rounded, tr('المخزون', 'Inventory'), const Color(0xFF0D9488), () => go(const ClientInventoryScreen())),
      (Icons.precision_manufacturing_rounded, tr('الأصول', 'Assets'), const Color(0xFF475569), () => go(const ClientAssetsScreen())),
      (Icons.meeting_room_rounded, tr('الإشغال', 'Occupancy'), const Color(0xFF9333EA), () => go(const OccupancyScreen())),
    ];

    // أيقونات الأمن — تظهر فقط لمدير مشروع الأمن (أو مشرف/مدير أمن).
    // كل أيقونة منفصلة: «المشرف» (أدوات المشرف الأمني) و«إدارة الأمن» (لوحة الأمن).
    final security = <(IconData, String, Color, VoidCallback)>[
      if (p.isSecuritySupervisor)
        (Icons.shield_moon_rounded, tr('المشرف', 'Supervisor'), const Color(0xFF0D9488),
            () => go(const SecuritySupervisorScreen())),
      if (p.isSecurityManager)
        (Icons.security_rounded, tr('إدارة الأمن', 'Security mgmt'), const Color(0xFF15213B),
            () => go(const SecurityHome())),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: RefreshIndicator(
        color: _teal,
        onRefresh: _load,
        child: ListView(padding: EdgeInsets.zero, children: [
          _header(p.name),
          const Padding(padding: EdgeInsets.fromLTRB(12, 10, 12, 0), child: LiveStreamBanner(isClient: true)),
          _kpiRow(),
          if (security.isNotEmpty) ...[
            _section(tr('الأمن', 'Security')),
            _grid(security),
          ],
          _section(tr('إدارة الخدمات والمتابعة', 'Services & follow-up')),
          _grid(manage),
          _section(tr('أدوات العميل والمكان', 'Client & place tools')),
          _grid(clientTools),
          const SizedBox(height: 24),
        ]),
      ),
    );
  }

  Widget _header(String name) => Container(
        padding: const EdgeInsets.fromLTRB(18, 52, 18, 20),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: Row(children: [
          CircleAvatar(radius: 26, backgroundColor: Colors.white.withValues(alpha: 0.18),
              child: Text(name.isNotEmpty ? name.characters.first : '؟', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22))),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
            const SizedBox(height: 5),
            Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.workspace_premium_rounded, color: Colors.white, size: 14), const SizedBox(width: 5),
                  Text(tr('مدير المشروع', 'Project manager'), style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
                ])),
          ])),
        ]),
      );

  Widget _kpiRow() {
    final items = [
      (tr('أوامر مفتوحة', 'Open WOs'), _n(['open', 'open_wo', 'workorders_open', 'wo_open']), const Color(0xFFE6295C)),
      (tr('قيد التنفيذ', 'In progress'), _n(['in_progress', 'wip', 'ongoing']), const Color(0xFF2563EB)),
      (tr('منجزة', 'Done'), _n(['done', 'completed', 'closed']), const Color(0xFF16A34A)),
      (tr('متأخرة', 'Overdue'), _n(['overdue', 'late', 'sla_breached']), const Color(0xFFF59E0B)),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 2),
      child: Row(children: [
        for (final it in items) Expanded(child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2))]),
          child: Column(children: [
            Text('${it.$2}', style: TextStyle(color: it.$3, fontWeight: FontWeight.w900, fontSize: 20)),
            const SizedBox(height: 3),
            Text(it.$1, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10, fontWeight: FontWeight.w600)),
          ]),
        )),
      ]),
    );
  }

  Widget _section(String title) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 8),
        child: Row(children: [
          Container(width: 4, height: 18, decoration: BoxDecoration(color: _teal, borderRadius: BorderRadius.circular(2))),
          const SizedBox(width: 8),
          Text(title, style: const TextStyle(color: _navy, fontWeight: FontWeight.w900, fontSize: 15)),
        ]),
      );

  Widget _grid(List<(IconData, String, Color, VoidCallback)> items) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: GridView.count(
          crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.86,
          children: [
            for (final it in items) InkWell(
              onTap: it.$4, borderRadius: BorderRadius.circular(16),
              child: Container(
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                    boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 2))]),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Container(width: 42, height: 42, decoration: BoxDecoration(color: it.$3.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                      child: Icon(it.$1, color: it.$3, size: 22)),
                  const SizedBox(height: 7),
                  Padding(padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Text(it.$2, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Color(0xFF1E293B), fontSize: 10.5, fontWeight: FontWeight.w700))),
                ]),
              ),
            ),
          ],
        ),
      );
}
