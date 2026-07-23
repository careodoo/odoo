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
import 'cleaning_audit_screen.dart';
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
import 'chat_screen.dart';
import 'nfc_provision_screen.dart';
import 'material_policy_screen.dart';
import 'support_screen.dart';
import 'valet_screen.dart';
import 'hospitality_screen.dart';
import 'hosp_suppliers_screen.dart';
import 'update_gate.dart';
import '../core/account_deletion.dart';

/// A polished home for everything this user can reach — styled like the CARE 2
/// CARE account page: a vibrant header, the systems rail (top icons) for
/// switching interfaces, then grouped tiles. Nothing is more than two taps away.
import 'service_settings_screen.dart';

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
    // Three tiers, so every user only sees what their role actually owns:
    //  • client  — the estate/contract consoles for their own facilities
    //  • boss    — supervisor/admin: operations oversight, no client ownership
    //  • field   — a cleaner/guard: only their own tools
    final isClient = p.role == 'client';
    final isBoss = p.isSupervisor || p.isAdmin;
    final isField = !isClient && !isBoss && !p.canAddWorkers;
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


    // ===== Systems — for a user who can reach more than one interface =====
    final auth = context.read<AuthProvider>();
    final ifaces = auth.interfaces ?? const {};
    final systems = <(String, String, String, IconData, int)>[
      ('cafm', 'إدارة المرافق', 'Facilities (CAFM)', Icons.apartment_rounded, 0xFFC0392B),
      ('pms', 'إدارة المشاريع', 'Projects (PMS)', Icons.account_tree_rounded, 0xFF2563EB),
      ('c2c', 'CARE 2 CARE', 'CARE 2 CARE', Icons.home_repair_service_rounded, 0xFF0EA5A4),
      ('management', 'الإدارة الخلفية', 'Management', Icons.dashboard_customize_rounded, 0xFF714B67),
    ].where((s) => ifaces[s.$1] == true).toList();
    if (systems.length > 1) {
      header(tr('الأنظمة المتاحة لك', 'Your systems'));
      for (final s in systems) {
        tile(s.$4, tr(s.$2, s.$3), null, c: Color(s.$5),
            onTap: () => auth.setAppMode(s.$1 == 'management' ? 'backend' : s.$1));
      }
      tile(Icons.swap_horiz_rounded, tr('شاشة التبديل بين الأنظمة', 'System switcher'), null,
          c: const Color(0xFF6366F1), onTap: () => auth.setAppMode('choose'));
    }

    // ===== Work & operations =====
    header(tr('العمل والعمليات', 'Work & operations'));
    tile(Icons.assignment_rounded, isField ? tr('مهامي', 'My tasks') : tr('أوامر العمل', 'Work orders'), const WorkOrdersScreen(), c: _navy);
    tile(Icons.forum_rounded, tr('التواصل والمحادثات', 'Messages & directory'), const ChatHubScreen(), c: const Color(0xFF0E7490));
    tile(Icons.fact_check_rounded, tr('الجودة والجولات', 'Quality & rounds'), const QualityScreen(), c: const Color(0xFF0EA5A4));
    if (!isField) tile(Icons.inbox_rounded, tr('طلبات الخدمة', 'Service requests'), const RequestsScreen(), c: const Color(0xFFE6295C));
    tile(Icons.event_repeat_rounded, tr('جدولة الأعمال', 'Work schedules'), const SchedulesScreen(), c: const Color(0xFF0D9488));
    if (!isField) tile(Icons.handyman_rounded, tr('الصيانة', 'Maintenance'), const MaintenanceScreen(), c: const Color(0xFFF7A23B));
    tile(Icons.directions_car_rounded, tr('صف السيارات', 'Valet parking'), const ValetScreen(), c: const Color(0xFFB45309));
    tile(Icons.local_cafe_rounded, tr('الضيافة', 'Hospitality'), const HospitalityScreen(), c: const Color(0xFF8A6D3B));
    if (p.canAddWorkers)
      tile(Icons.campaign_rounded, tr('مركز الإشعارات', 'Notification center'), const NotifySendScreen(), c: const Color(0xFFEA580C));
    // everyone — including clients — can scan a location's QR or tap its NFC
    // tag to jump straight to it (the picker handles both).
    tile(Icons.qr_code_scanner_rounded, tr('مسح موقع (QR / NFC)', 'Scan location (QR / NFC)'), const ScanScreen(), c: const Color(0xFF0891B2));

    // ===== Estate & assets (client / back-office only) =====
    if (!isField) {
      header(tr('المنشآت والأصول', 'Estate & assets'));
      tile(Icons.location_city_rounded, tr('المباني والمرافق', 'Buildings & facilities'), const ClientStructureScreen(), c: const Color(0xFFC0392B));
      tile(Icons.precision_manufacturing_rounded, tr('الأصول', 'Assets'), const ClientAssetsScreen(), c: const Color(0xFF0891B2));
    }
    // ===== My tools (everyone) — a worker still needs stock + attendance =====
    header(isField ? tr('أدواتي', 'My tools') : tr('المخزون والحضور', 'Inventory & attendance'));
    tile(Icons.inventory_2_rounded, isField ? tr('صرف مواد', 'Issue materials') : tr('المخزون', 'Inventory'), const ClientInventoryScreen(), c: const Color(0xFF0E3A5F));
    tile(Icons.fingerprint_rounded, tr('الحضور والانصراف', 'Attendance'), const AttendanceScreen(), c: const Color(0xFF7C3AED));
    if (!isField) tile(Icons.insights_rounded, tr('التحليلات والتقارير', 'Analytics & reports'), const ClientAnalyticsScreen(), c: const Color(0xFF2563EB));

    // role-specific service consoles
    if (p.role == 'cleaning') { header(tr('النظافة', 'Cleaning')); tile(Icons.cleaning_services_rounded, tr('تدقيق الجودة', 'Quality audits'), const CleaningAuditScreen(), c: const Color(0xFF0EA5E9)); }
    if (p.role == 'agriculture') { header(tr('الزراعة', 'Agriculture')); tile(Icons.grass_rounded, tr('مناطق الريّ', 'Irrigation zones'), ServiceScreen(kind: 'agri', title: tr('مناطق الريّ', 'Irrigation zones')), c: const Color(0xFF16A34A)); }
    if (p.role == 'facade') { header(tr('الواجهات', 'Facades')); tile(Icons.cleaning_services_rounded, tr('تصاريح الارتفاع', 'Height permits'), const ServiceScreen(kind: 'facade', title: 'تصاريح الواجهات'), c: const Color(0xFF7C3AED)); }
    if (p.role == 'security') {
      header(tr('الأمن', 'Security'));
      tile(Icons.report_rounded, tr('البلاغات الأمنية', 'Incidents'), const SecurityIncidentsScreen(), c: const Color(0xFFE5484D));
      tile(Icons.route_rounded, tr('الدوريات', 'Patrols'), SecurityListScreen(kind: 'patrols', title: tr('الدوريات', 'Patrols')), c: const Color(0xFF0891B2));
      tile(Icons.vpn_key_rounded, tr('عهدة المفاتيح', 'Key custody'), SecurityListScreen(kind: 'keys', title: tr('عهدة المفاتيح', 'Key custody')), c: const Color(0xFFF59E0B));
      tile(Icons.badge_rounded, tr('تصاريح البوابة', 'Gate passes'), SecurityListScreen(kind: 'gatepasses', title: tr('تصاريح البوابة', 'Gate passes')), c: const Color(0xFF16A34A));
    }

    // ===== Contracts & administration (client / back-office only) =====
    if (!isField) {
      header(tr('العقود والإدارة', 'Contracts & administration'));
      // contracts are the client's own commercial file — not a supervisor tool
      if (isClient || p.isAdmin) tile(Icons.description_rounded, tr('العقود', 'Contracts'), const ContractsScreen(), c: const Color(0xFF0B6EA8));
      // per-service settings — a client tunes notifications/reports per service
      if (isClient) tile(Icons.tune_rounded, tr('إعدادات الخدمات', 'Service settings'), const ServiceSettingsScreen(), c: const Color(0xFF6366F1));
      // hospitality pantry setup: suppliers + registered materials
      if (isClient || p.canAddWorkers) tile(Icons.storefront_rounded, tr('الموردون والمواد', 'Suppliers & materials'), const HospSuppliersScreen(), c: const Color(0xFF8A6D3B));
      if (p.canAddWorkers) {
        tile(Icons.settings_suggest_rounded, tr('إدارة المنشأة', 'Manage facility'), const ManageScreen(), c: const Color(0xFF6366F1));
        tile(Icons.nfc_rounded, tr('برمجة شرائح NFC', 'NFC tags'), const NfcProvisionScreen(), c: const Color(0xFF6D28D9));
        tile(Icons.rule_rounded, tr('سياسة صرف المواد', 'Material policy'), const MaterialPolicyScreen(), c: const Color(0xFF0E7490));
        tile(Icons.person_add_rounded, tr('إضافة عامل', 'Add worker'), const AddWorkerScreen(), c: const Color(0xFF16A34A));
      }
      if (p.isSupervisor || p.isAdmin) {
        tile(Icons.dashboard_customize_rounded, tr('لوحة المشرف — إسناد', 'Supervisor board'), const SupervisorScreen(), c: const Color(0xFF0D9488));
        if (p.isAdmin) tile(Icons.business_rounded, tr('لوحة الشركة', 'Company dashboard'), const AdminHome(), c: const Color(0xFF6366F1));
      }
    }
    // my own performance file (a worker may see theirs); back office stays hidden
    if (p.role != 'client') { header(tr('ملفي', 'My file')); tile(Icons.star_rounded, tr('تقييم أدائي', 'My performance'), const AppraisalScreen(), c: const Color(0xFFF59E0B)); }
    if (p.isAdmin) tile(Icons.dashboard_customize_rounded, tr('لوحة أودو الكاملة', 'Full Odoo backend'), const OdooBackendScreen(), c: const Color(0xFF714B67));

    // ===== Account & preferences =====
    header(tr('الحساب والتفضيلات', 'Account & preferences'));
    tile(Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), const NotificationsScreen(), c: const Color(0xFF6366F1));
    tile(Icons.language_rounded, tr('اللغة', 'Language'), null, c: const Color(0xFF16A34A), onTap: () => showLanguagePicker(context));
    tile(Icons.dark_mode_rounded, tr('المظهر (فاتح/داكن)', 'Theme (light/dark)'), null, c: const Color(0xFF334155),
        onTap: () => _themeInfo(context));

    // ===== Help & support (client-friendly extras) =====
    header(tr('المساعدة والدعم', 'Help & support'));
    tile(Icons.support_agent_rounded, tr('الدعم الفني وطلباتي', 'Support & my tickets'), const SupportScreen(), c: const Color(0xFF0891B2));
    tile(Icons.help_outline_rounded, tr('كيف يعمل التطبيق', 'How the app works'), null, c: const Color(0xFF7C3AED),
        onTap: () => _howItWorks(context));
    tile(Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), null, c: const Color(0xFF16A34A),
        onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/privacy.html'));
    tile(Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), null, c: const Color(0xFF64748B),
        onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/terms.html'));
    tile(Icons.star_rate_rounded, tr('قيّم التطبيق', 'Rate the app'), null, c: const Color(0xFFF59E0B),
        onTap: () => _rateApp(context));
    tile(Icons.system_update_rounded, tr('التحقق من التحديثات', 'Check for updates'), null, c: const Color(0xFF0891B2),
        onTap: () => _checkUpdate(context));
    tile(Icons.info_outline_rounded, tr('عن التطبيق', 'About'), null, c: const Color(0xFF0E3A5F),
        onTap: () => _about(context));
    tile(Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), null, c: _red, danger: true,
        onTap: () => context.read<AuthProvider>().logout());
    tile(Icons.delete_forever_rounded, tr('حذف الحساب', 'Delete account'), null, c: const Color(0xFFB91C1C), danger: true,
        onTap: () => showDeleteAccountFlow(context));

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
                // polished header action icons
                _headerIcon(context, Icons.language_rounded, onTap: () => showLanguagePicker(context)),
                const SizedBox(width: 8),
                if (p.isAdmin || context.read<AuthProvider>().isImpersonating) ...[
                  _headerIcon(context, Icons.switch_account_rounded, onTap: () => _switchUser(context)),
                  const SizedBox(width: 8),
                ],
                _headerIcon(context, Icons.notifications_rounded,
                    badge: p.unreadNotifications,
                    onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()))),
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

  Widget _headerIcon(BuildContext context, IconData icon, {VoidCallback? onTap, int badge = 0}) => Stack(
        clipBehavior: Clip.none, children: [
          Material(
            color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(13),
            child: InkWell(
              borderRadius: BorderRadius.circular(13), onTap: onTap,
              child: Container(width: 40, height: 40, alignment: Alignment.center,
                  child: Icon(icon, color: Colors.white, size: 20)),
            ),
          ),
          if (badge > 0) Positioned(right: -4, top: -4, child: Container(
            padding: const EdgeInsets.all(4),
            decoration: const BoxDecoration(color: Color(0xFFFBBF24), shape: BoxShape.circle),
            child: Text('$badge', style: const TextStyle(color: Color(0xFF7C2D12), fontSize: 9, fontWeight: FontWeight.w900)),
          )),
        ],
      );

  /// Admin/demo: preview the app as any other user (impersonation switcher).
  void _switchUser(BuildContext context) {
    final auth = context.read<AuthProvider>();
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.75, minChildSize: 0.5, maxChildSize: 0.95,
        builder: (c, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [_redBright, _redDeep], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  const Icon(Icons.switch_account_rounded, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(child: Text(tr('عرض التطبيق كـ (تجريبي)', 'Preview app as (demo)'),
                      style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                ]),
              ])),
            Expanded(child: FutureBuilder<List<dynamic>>(
              future: auth.impersonatableUsers(),
              builder: (c, snap) {
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final users = snap.data!;
                return ListView(controller: sc, padding: const EdgeInsets.all(8), children: [
                  for (final u in users) Card(
                    margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: ListTile(
                      leading: CircleAvatar(backgroundColor: _navy, child: Text('${u['name']}'.characters.first, style: const TextStyle(color: Colors.white))),
                      title: Text('${u['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      subtitle: Text('${u['login']} · ${u['kind']}', style: const TextStyle(fontSize: 12)),
                      trailing: const Icon(Icons.login_rounded, color: _navy),
                      onTap: () async {
                        Navigator.pop(c);
                        try {
                          await auth.impersonate('${u['login']}');
                        } catch (e) {
                          if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                        }
                      },
                    ),
                  ),
                ]);
              },
            )),
          ]),
        ),
      ),
    );
  }

  Future<void> _openUrl(BuildContext context, String url) async {
    final u = Uri.parse(url);
    if (!await launchUrl(u, mode: LaunchMode.externalApplication) && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
    }
  }


  /// Ask for a rating in-app; anything 4★+ goes to the store listing, lower
  /// scores open a support ticket instead so the complaint reaches us first.
  void _rateApp(BuildContext context) {
    int stars = 0;
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(3))),
          const Text('⭐', style: TextStyle(fontSize: 34)),
          const SizedBox(height: 8),
          Text(tr('ما رأيك في تطبيق CARE؟', 'How do you rate CARE?'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy)),
          const SizedBox(height: 4),
          Text(tr('تقييمك يساعدنا على تحسينه', 'Your rating helps us improve it'),
              style: TextStyle(fontSize: 12.5, color: Colors.grey.shade600)),
          const SizedBox(height: 14),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (var i = 1; i <= 5; i++)
              IconButton(
                iconSize: 34,
                icon: Icon(i <= stars ? Icons.star_rounded : Icons.star_border_rounded,
                    color: const Color(0xFFF59E0B)),
                onPressed: () => setSt(() => stars = i),
              ),
          ]),
          const SizedBox(height: 10),
          SizedBox(width: double.infinity, child: FilledButton.icon(
            style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFF59E0B), minimumSize: const Size.fromHeight(50)),
            onPressed: stars == 0 ? null : () {
              Navigator.pop(ctx);
              if (stars >= 4) {
                _openUrl(context, 'https://play.google.com/store/apps/details?id=care.app');
              } else {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const SupportScreen()));
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text(tr('يهمّنا رأيك — أخبرنا بما يمكن تحسينه',
                                   'We want to hear you — tell us what to improve')),
                  backgroundColor: const Color(0xFF0891B2)));
              }
            },
            icon: const Icon(Icons.send_rounded),
            label: Text(stars >= 4 ? tr('قيّم على المتجر', 'Rate on the store') : tr('إرسال', 'Send'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          )),
        ]),
      )),
    );
  }

  Future<void> _checkUpdate(BuildContext context) async {
    UpdateGate.reset();
    await UpdateGate.check(context, silentWhenCurrent: false);
  }

  void _themeInfo(BuildContext context) => showDialog(context: context, builder: (_) => AlertDialog(
        title: Text(tr('المظهر', 'Theme')),
        content: Text(tr('يتبع التطبيق مظهر جهازك (فاتح/داكن) تلقائياً.', 'The app follows your device light/dark theme automatically.')),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('حسناً', 'OK')))],
      ));

  void _howItWorks(BuildContext context) => showDialog(context: context, builder: (_) => AlertDialog(
        title: Text(tr('كيف يعمل التطبيق', 'How the app works')),
        content: Text(tr(
          tr('من الرئيسية تتابع مبانيك وخدماتك وفِرَقك وأوامر العمل مباشرة. ارفع طلب خدمة أو ملاحظة جودة، وتابع تنفيذها حتى الإغلاق، واطبع التقارير أو صدّرها إلى Excel.', 'From here you follow your buildings, services, teams and work orders live. Raise a service request or a quality note, track it through to closure, and print or export the reports to Excel.'),
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
