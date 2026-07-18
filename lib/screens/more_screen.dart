import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import '../core/app_version.dart';
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
import 'quality_screen.dart';
import 'odoo_backend_screen.dart';
import 'c2c/mode_switch.dart';

/// A polished home for everything this user can reach — styled like the CARE 2
/// CARE account page: a vibrant header, the systems rail (top icons) for
/// switching interfaces, then grouped tiles. Nothing is more than two taps away.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  static const _red = Color(0xFFC0392B);
  static const _redBright = Color(0xFFE24A3B);
  static const _redDeep = Color(0xFF8E241B);
  static const _navy = Color(0xFF0E3A5F);

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    context.watch<LangProvider>();
    final name = p.name;
    final items = <Widget>[];

    void tile(IconData i, String t, Widget? screen, {required Color c, VoidCallback? onTap, bool danger = false}) {
      items.add(Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          child: ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            leading: Container(width: 38, height: 38,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: Icon(i, color: c, size: 20)),
            title: Text(t, style: TextStyle(fontWeight: FontWeight.w700, color: danger ? _red : null)),
            trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
            onTap: onTap ?? (screen == null ? null : () => Navigator.push(context, MaterialPageRoute(builder: (_) => screen))),
          ),
        ),
      ));
    }

    void header(String t) => items.add(Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 4),
          child: Align(alignment: Alignment.centerRight,
              child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: _navy, fontSize: 15))),
        ));

    // ===== Work =====
    header(tr('العمل', 'Work'));
    tile(Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'), const WorkOrdersScreen(), c: _navy);
    tile(Icons.fact_check_rounded, tr('الجودة والجولات', 'Quality & rounds'), const QualityScreen(), c: const Color(0xFF0EA5A4));
    if (p.role != 'client') tile(Icons.qr_code_scanner_rounded, tr('مسح رمز الموقع', 'Scan location'), const ScanScreen(), c: const Color(0xFF0891B2));
    if (p.role != 'client') tile(Icons.dashboard_customize_rounded, tr('لوحة أودو الكاملة', 'Full Odoo backend'), const OdooBackendScreen(), c: const Color(0xFF714B67));
    tile(Icons.apartment_rounded, tr('المبنى ثلاثي الأبعاد — إشغال حيّ', '3D building — live occupancy'), const OccupancyScreen(), c: const Color(0xFF6366F1));

    if (p.role == 'cleaning') { header(tr('النظافة', 'Cleaning')); tile(Icons.cleaning_services_rounded, tr('تدقيق الجودة', 'Quality audits'), const ServiceScreen(kind: 'cleaning', title: 'تدقيق النظافة'), c: const Color(0xFF0EA5E9)); }
    if (p.role == 'agriculture') { header(tr('الزراعة', 'Agriculture')); tile(Icons.grass_rounded, tr('مناطق الريّ', 'Irrigation zones'), ServiceScreen(kind: 'agri', title: tr('مناطق الريّ', 'Irrigation zones')), c: const Color(0xFF16A34A)); }
    if (p.role == 'facade') { header(tr('الواجهات', 'Facades')); tile(Icons.cleaning_services_rounded, tr('تصاريح الارتفاع', 'Height permits'), const ServiceScreen(kind: 'facade', title: 'تصاريح الواجهات'), c: const Color(0xFF7C3AED)); }

    if (p.role == 'security') {
      header(tr('الأمن', 'Security'));
      tile(Icons.report_rounded, tr('البلاغات الأمنية', 'Incidents'), const SecurityIncidentsScreen(), c: const Color(0xFFE5484D));
      tile(Icons.route_rounded, tr('الدوريات', 'Patrols'), SecurityListScreen(kind: 'patrols', title: tr('الدوريات', 'Patrols')), c: const Color(0xFF0891B2));
      tile(Icons.vpn_key_rounded, tr('عهدة المفاتيح', 'Key custody'), SecurityListScreen(kind: 'keys', title: tr('عهدة المفاتيح', 'Key custody')), c: const Color(0xFFF59E0B));
      tile(Icons.badge_rounded, tr('تصاريح البوابة', 'Gate passes'), SecurityListScreen(kind: 'gatepasses', title: tr('تصاريح البوابة', 'Gate passes')), c: const Color(0xFF16A34A));
    }

    if (p.isSupervisor || p.isAdmin) {
      header(tr('الإدارة', 'Management'));
      tile(Icons.dashboard_customize_rounded, tr('لوحة المشرف — إسناد', 'Supervisor board'), const SupervisorScreen(), c: const Color(0xFF0D9488));
      if (p.isAdmin) tile(Icons.business_rounded, tr('لوحة الشركة', 'Company dashboard'), const AdminHome(), c: const Color(0xFF6366F1));
    }

    header(tr('العقود والإدارة', 'Contracts & management'));
    tile(Icons.inbox_rounded, tr('طلبات الخدمة', 'Service requests'), const RequestsScreen(), c: const Color(0xFFE6295C));
    tile(Icons.description_rounded, tr('العقود', 'Contracts'), const ContractsScreen(), c: const Color(0xFF0B6EA8));
    if (p.canAddWorkers) {
      tile(Icons.settings_suggest_rounded, tr('إدارة المنشأة', 'Manage facility'), const ManageScreen(), c: const Color(0xFF6366F1));
      tile(Icons.person_add_rounded, tr('إضافة عامل', 'Add worker'), const AddWorkerScreen(), c: const Color(0xFF16A34A));
    }
    if (p.role != 'client') tile(Icons.star_rounded, tr('تقييم الأداء', 'Performance'), const AppraisalScreen(), c: const Color(0xFFF59E0B));

    // ===== Account =====
    header(tr('الحساب', 'Account'));
    tile(Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), const NotificationsScreen(), c: const Color(0xFF6366F1));
    tile(Icons.language_rounded, tr('اللغة', 'Language'), null, c: const Color(0xFF16A34A), onTap: () => showLanguagePicker(context));
    tile(Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), null, c: _red, danger: true,
        onTap: () => context.read<AuthProvider>().logout());

    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      body: ListView(padding: EdgeInsets.zero, children: [
        // ===== vibrant header =====
        SizedBox(
          height: 196,
          child: Stack(children: [
            CustomPaint(
              painter: const BrandPattern(opacity: 0.07),
              child: Container(
                height: 176,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(colors: [_redBright, _red, _redDeep],
                      begin: Alignment.topRight, end: Alignment.bottomLeft),
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
                ),
              ),
            ),
            Positioned(top: 0, left: 0, right: 0, child: SafeArea(bottom: false, child: Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Column(children: [
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(shape: BoxShape.circle,
                      border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
                  child: CircleAvatar(radius: 34, backgroundColor: Colors.white,
                      child: Text(name.isNotEmpty ? name.trim().characters.first : '?',
                          style: const TextStyle(color: _navy, fontSize: 28, fontWeight: FontWeight.w900))),
                ),
                const SizedBox(height: 8),
                Text(name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                Text(_roleLabel(p.role), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5)),
              ]),
            ))),
          ]),
        ),
        // ===== systems rail (top icons) — replaces the old "back to C2C" text =====
        const ModeSwitchRail(current: 'cafm'),
        ...items,
        const SizedBox(height: 22),
        Center(child: Text('CARE', style: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.w900, letterSpacing: 2))),
        const SizedBox(height: 3),
        Center(child: Text('v${AppVersion.value}',
            style: TextStyle(color: Colors.grey.shade400, fontSize: 11, fontWeight: FontWeight.w600))),
        const SizedBox(height: 28),
      ]),
    );
  }

  String _roleLabel(String role) {
    switch (role) {
      case 'client': return tr('عميل', 'Client');
      case 'cleaning': return tr('فريق النظافة', 'Cleaning crew');
      case 'agriculture': return tr('فريق الزراعة', 'Agriculture crew');
      case 'facade': return tr('فريق الواجهات', 'Facade crew');
      case 'security': return tr('فريق الأمن', 'Security team');
      default: return tr('فريق العمل', 'Workforce');
    }
  }
}
