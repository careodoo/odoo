import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'notifications_screen.dart';
import 'supervisor_screen.dart';
import 'admin_home.dart';
import 'security_incidents_screen.dart';
import 'security_list_screen.dart';
import 'service_screen.dart';
import 'appraisal_screen.dart';
import 'occupancy_screen.dart';
import 'add_worker_screen.dart';
import 'contracts_screen.dart';
import 'manage_screen.dart';
import 'requests_screen.dart';

/// A single place that links to everything available to this user — so nothing
/// is more than two taps away.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final items = <Widget>[];

    void tile(IconData i, String t, Widget? screen, {Color? c, VoidCallback? onTap}) {
      items.add(Card(
        child: ListTile(
          leading: Icon(i, color: c ?? Theme.of(context).colorScheme.primary),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w700)),
          trailing: const Icon(Icons.chevron_left),
          onTap: onTap ?? (screen == null ? null : () => Navigator.push(context, MaterialPageRoute(builder: (_) => screen))),
        ),
      ));
    }

    void header(String t) => items.add(Padding(
          padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
          child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        ));

    header(tr('العمل', 'Work'));
    tile(Icons.assignment, tr('أوامر العمل', 'Work orders'), const WorkOrdersScreen());
    if (p.role != 'client') tile(Icons.qr_code_scanner, tr('مسح رمز الموقع', 'Scan location'), const ScanScreen());

    if (p.role == 'cleaning') { header(tr('النظافة', 'Cleaning')); tile(Icons.cleaning_services, tr('تدقيق الجودة', 'Quality audits'), const ServiceScreen(kind: 'cleaning', title: 'تدقيق النظافة')); }
    if (p.role == 'agriculture') { header(tr('الزراعة', 'Agriculture')); tile(Icons.grass, tr('مناطق الريّ', 'Irrigation zones'), ServiceScreen(kind: 'agri', title: tr('مناطق الريّ', 'Irrigation zones'))); }
    if (p.role == 'facade') { header(tr('الواجهات', 'Facades')); tile(Icons.cleaning_services, tr('تصاريح الارتفاع', 'Height permits'), const ServiceScreen(kind: 'facade', title: 'تصاريح الواجهات')); }

    if (p.role == 'security') {
      header(tr('الأمن', 'Security'));
      tile(Icons.report, tr('البلاغات الأمنية', 'Incidents'), const SecurityIncidentsScreen(), c: const Color(0xFFE5484D));
      tile(Icons.route, tr('الدوريات', 'Patrols'), SecurityListScreen(kind: 'patrols', title: tr('الدوريات', 'Patrols')));
      tile(Icons.vpn_key, tr('عهدة المفاتيح', 'Key custody'), SecurityListScreen(kind: 'keys', title: tr('عهدة المفاتيح', 'Key custody')));
      tile(Icons.badge, tr('تصاريح البوابة', 'Gate passes'), SecurityListScreen(kind: 'gatepasses', title: tr('تصاريح البوابة', 'Gate passes')));
    }

    if (p.isSupervisor || p.isAdmin) {
      header(tr('الإدارة', 'Management'));
      tile(Icons.dashboard_customize, tr('لوحة المشرف — إسناد', 'Supervisor board'), const SupervisorScreen());
      if (p.isAdmin) tile(Icons.business, tr('لوحة الشركة', 'Company dashboard'), const AdminHome(), c: const Color(0xFF6366F1));
    }
    header(tr('العقود والإدارة', 'Contracts & management'));
    tile(Icons.inbox, tr('طلبات الخدمة', 'Service requests'), const RequestsScreen(), c: const Color(0xFFE6295C));
    tile(Icons.description, tr('العقود', 'Contracts'), const ContractsScreen(), c: const Color(0xFF0B6EA8));
    if (p.canAddWorkers) {
      tile(Icons.settings_suggest, tr('إدارة المنشأة', 'Manage facility'), const ManageScreen(), c: const Color(0xFF6366F1));
      tile(Icons.person_add, tr('➕ إضافة عامل', '➕ Add worker'), const AddWorkerScreen(), c: const Color(0xFF16A34A));
    }

    if (p.role != 'client') tile(Icons.star, tr('تقييم الأداء', 'Performance'), const AppraisalScreen(), c: const Color(0xFFF59E0B));
    tile(Icons.apartment, tr('المبنى ثلاثي الأبعاد — إشغال حيّ', '3D building — live'), const OccupancyScreen(), c: const Color(0xFF6366F1));
    header(tr('الحساب', 'Account'));
    tile(Icons.notifications, tr('الإشعارات', 'Notifications'), const NotificationsScreen());
    // language toggle
    final lang = context.watch<LangProvider>();
    tile(Icons.language, lang.isArabic ? 'English' : 'العربية', null, c: const Color(0xFF0B6EA8),
        onTap: () => context.read<LangProvider>().toggle());
    tile(Icons.logout, tr('تسجيل الخروج', 'Sign out'), null, c: const Color(0xFFE5484D),
        onTap: () => context.read<AuthProvider>().logout());

    return Scaffold(
      appBar: AppBar(title: Text(tr('المزيد', 'More'))),
      body: ListView(padding: const EdgeInsets.all(14), children: items),
    );
  }
}
