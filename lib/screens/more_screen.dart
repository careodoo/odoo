import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
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
import 'add_worker_screen.dart';
import 'contracts_screen.dart';
import 'manage_screen.dart';
import 'requests_screen.dart';
import 'quality_screen.dart';
import 'odoo_backend_screen.dart';
import 'client_structure_screen.dart';
import 'client_assets_screen.dart';
import 'client_inventory_screen.dart';
import 'attendance_screen.dart';
import 'client_analytics_screen.dart';
import 'schedules_screen.dart';
import 'notify_send_screen.dart';
import 'maintenance_screen.dart';

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
    var toolCount = 0;

    void tile(IconData i, String t, Widget? screen, {required Color c, VoidCallback? onTap, bool danger = false}) {
      toolCount++;
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


    // ===== Work & operations =====
    header(tr('العمل والعمليات', 'Work & operations'));
    tile(Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'), const WorkOrdersScreen(), c: _navy);
    tile(Icons.fact_check_rounded, tr('الجودة والجولات', 'Quality & rounds'), const QualityScreen(), c: const Color(0xFF0EA5A4));
    tile(Icons.inbox_rounded, tr('طلبات الخدمة', 'Service requests'), const RequestsScreen(), c: const Color(0xFFE6295C));
    tile(Icons.event_repeat_rounded, tr('جدولة الأعمال', 'Work schedules'), const SchedulesScreen(), c: const Color(0xFF0D9488));
    tile(Icons.handyman_rounded, tr('الصيانة', 'Maintenance'), const MaintenanceScreen(), c: const Color(0xFFF7A23B));
    if (p.canAddWorkers)
      tile(Icons.campaign_rounded, tr('مركز الإشعارات', 'Notification center'), const NotifySendScreen(), c: const Color(0xFFEA580C));
    if (p.role != 'client') tile(Icons.qr_code_scanner_rounded, tr('مسح رمز الموقع', 'Scan location'), const ScanScreen(), c: const Color(0xFF0891B2));

    // ===== Estate & assets =====
    header(tr('المنشآت والأصول', 'Estate & assets'));
    tile(Icons.location_city_rounded, tr('المباني والمرافق', 'Buildings & facilities'), const ClientStructureScreen(), c: const Color(0xFFC0392B));
    tile(Icons.precision_manufacturing_rounded, tr('الأصول', 'Assets'), const ClientAssetsScreen(), c: const Color(0xFF0891B2));
    tile(Icons.inventory_2_rounded, tr('المخزون', 'Inventory'), const ClientInventoryScreen(), c: const Color(0xFF0E3A5F));
    tile(Icons.fingerprint_rounded, tr('الحضور والانصراف', 'Attendance'), const AttendanceScreen(), c: const Color(0xFF7C3AED));
    tile(Icons.insights_rounded, tr('التحليلات والتقارير', 'Analytics & reports'), const ClientAnalyticsScreen(), c: const Color(0xFF2563EB));

    // role-specific service consoles
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

    // ===== Contracts & administration =====
    header(tr('العقود والإدارة', 'Contracts & administration'));
    tile(Icons.description_rounded, tr('العقود', 'Contracts'), const ContractsScreen(), c: const Color(0xFF0B6EA8));
    if (p.canAddWorkers) {
      tile(Icons.settings_suggest_rounded, tr('إدارة المنشأة', 'Manage facility'), const ManageScreen(), c: const Color(0xFF6366F1));
      tile(Icons.person_add_rounded, tr('إضافة عامل', 'Add worker'), const AddWorkerScreen(), c: const Color(0xFF16A34A));
    }
    if (p.isSupervisor || p.isAdmin) {
      tile(Icons.dashboard_customize_rounded, tr('لوحة المشرف — إسناد', 'Supervisor board'), const SupervisorScreen(), c: const Color(0xFF0D9488));
      if (p.isAdmin) tile(Icons.business_rounded, tr('لوحة الشركة', 'Company dashboard'), const AdminHome(), c: const Color(0xFF6366F1));
    }
    if (p.role != 'client') tile(Icons.star_rounded, tr('تقييم الأداء', 'Performance'), const AppraisalScreen(), c: const Color(0xFFF59E0B));
    if (p.role != 'client') tile(Icons.dashboard_customize_rounded, tr('لوحة أودو الكاملة', 'Full Odoo backend'), const OdooBackendScreen(), c: const Color(0xFF714B67));

    // ===== Account & preferences =====
    header(tr('الحساب والتفضيلات', 'Account & preferences'));
    tile(Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), const NotificationsScreen(), c: const Color(0xFF6366F1));
    tile(Icons.language_rounded, tr('اللغة', 'Language'), null, c: const Color(0xFF16A34A), onTap: () => showLanguagePicker(context));
    tile(Icons.dark_mode_rounded, tr('المظهر (فاتح/داكن)', 'Theme (light/dark)'), null, c: const Color(0xFF334155),
        onTap: () => _themeInfo(context));

    // ===== Help & support (client-friendly extras) =====
    header(tr('المساعدة والدعم', 'Help & support'));
    tile(Icons.support_agent_rounded, tr('تواصل مع الدعم', 'Contact support'), null, c: const Color(0xFF0891B2),
        onTap: () => _contactSupport(context));
    tile(Icons.help_outline_rounded, tr('كيف يعمل التطبيق', 'How the app works'), null, c: const Color(0xFF7C3AED),
        onTap: () => _howItWorks(context));
    tile(Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), null, c: const Color(0xFF16A34A),
        onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/privacy.html'));
    tile(Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), null, c: const Color(0xFF64748B),
        onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/terms.html'));
    tile(Icons.info_outline_rounded, tr('عن التطبيق', 'About'), null, c: const Color(0xFF0E3A5F),
        onTap: () => _about(context));
    tile(Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), null, c: _red, danger: true,
        onTap: () => context.read<AuthProvider>().logout());

    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      body: ListView(padding: EdgeInsets.zero, children: [
        // ===== rich, professional header =====
        Stack(children: [
          CustomPaint(
            painter: const BrandPattern(opacity: 0.08),
            child: Container(
              height: 230,
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_redBright, _red, _redDeep],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
              ),
            ),
          ),
          SafeArea(bottom: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
            child: Column(children: [
              Row(children: [
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(shape: BoxShape.circle,
                      border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
                  child: CircleAvatar(radius: 30, backgroundColor: Colors.white,
                      child: Text(name.isNotEmpty ? name.trim().characters.first : '?',
                          style: const TextStyle(color: _navy, fontSize: 24, fontWeight: FontWeight.w900))),
                ),
                const SizedBox(width: 13),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.verified_user_rounded, size: 12, color: Colors.white),
                      const SizedBox(width: 5),
                      Text(_roleLabel(p.role), style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
                    ]),
                  ),
                ])),
                // notifications
                Stack(clipBehavior: Clip.none, children: [
                  Container(
                    width: 40, height: 40, alignment: Alignment.center,
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(13)),
                    child: const Icon(Icons.notifications_rounded, color: Colors.white, size: 20),
                  ),
                  if (p.unreadNotifications > 0)
                    Positioned(right: -4, top: -4, child: Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(color: Color(0xFFFBBF24), shape: BoxShape.circle),
                      child: Text('${p.unreadNotifications}', style: const TextStyle(color: Color(0xFF7C2D12), fontSize: 9, fontWeight: FontWeight.w900)),
                    )),
                ]),
              ]),
              const SizedBox(height: 16),
              // glass info strip — "many data" at a glance
              Container(
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
                ),
                child: Row(children: [
                  _hInfo(Icons.apps_rounded, '$toolCount', tr('أداة', 'Tools')),
                  _hDiv(),
                  _hInfo(Icons.notifications_active_rounded, '${p.unreadNotifications}', tr('إشعار', 'Alerts')),
                  _hDiv(),
                  _hInfo(p.isAdmin ? Icons.admin_panel_settings_rounded : (p.canAddWorkers ? Icons.manage_accounts_rounded : Icons.badge_rounded),
                      p.isAdmin ? tr('مدير', 'Admin') : (p.isSupervisor ? tr('مشرف', 'Super') : tr('مستخدم', 'User')),
                      tr('الصلاحية', 'Access')),
                  _hDiv(),
                  _hInfo(Icons.apartment_rounded, 'CAFM', tr('النظام', 'System')),
                ]),
              ),
            ]),
          )),
        ]),
        const SizedBox(height: 6),
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

  Future<void> _openUrl(BuildContext context, String url) async {
    final u = Uri.parse(url);
    if (!await launchUrl(u, mode: LaunchMode.externalApplication) && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
    }
  }

  void _themeInfo(BuildContext context) => showDialog(context: context, builder: (_) => AlertDialog(
        title: Text(tr('المظهر', 'Theme')),
        content: Text(tr('يتبع التطبيق مظهر جهازك (فاتح/داكن) تلقائياً.', 'The app follows your device light/dark theme automatically.')),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('حسناً', 'OK')))],
      ));

  void _contactSupport(BuildContext context) => showModalBottomSheet(context: context, backgroundColor: Colors.transparent, builder: (_) => Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [const Icon(Icons.support_agent_rounded, color: Color(0xFF0891B2)), const SizedBox(width: 8),
            Text(tr('تواصل مع الدعم', 'Contact support'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))]),
          const SizedBox(height: 14),
          ListTile(leading: const Icon(Icons.phone_rounded, color: Color(0xFF16A34A)), title: const Text('+965 1880 011'),
            onTap: () => _openUrl(context, 'tel:+9651880011')),
          ListTile(leading: const Icon(Icons.email_rounded, color: Color(0xFFC0392B)), title: const Text('info@care-kw.com'),
            onTap: () => _openUrl(context, 'mailto:info@care-kw.com')),
          ListTile(leading: const Icon(Icons.language_rounded, color: Color(0xFF0891B2)), title: const Text('care-kw.com'),
            onTap: () => _openUrl(context, 'https://care-kw.com')),
        ]),
      ));

  void _howItWorks(BuildContext context) => showDialog(context: context, builder: (_) => AlertDialog(
        title: Text(tr('كيف يعمل التطبيق', 'How the app works')),
        content: Text(tr(
          'من الرئيسية تتابع مبانيك وخدماتك وفِرَقك وأوامر العمل مباشرة. ارفع طلب خدمة أو ملاحظة جودة، وتابع تنفيذها حتى الإغلاق، واطبع التقارير أو صدّرها إلى Excel.',
          'From the home screen you follow your buildings, services, teams and work orders live. Raise a service request or quality note, track it to closure, and print or export reports to Excel.'),
          style: const TextStyle(height: 1.6)),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('حسناً', 'OK')))],
      ));

  void _about(BuildContext context) => showAboutDialog(context: context,
        applicationName: 'CARE', applicationVersion: 'v${AppVersion.value}',
        applicationLegalese: '© CARE — care-kw.com',
        children: [Padding(padding: const EdgeInsets.only(top: 12),
          child: Text(tr('منصّة إدارة المرافق والخدمات المتكاملة.', 'Integrated facilities & services management platform.')))]);

  Widget _hInfo(IconData ic, String v, String l) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 17),
        const SizedBox(height: 3),
        Text(v, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900)),
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _hDiv() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.18));

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
