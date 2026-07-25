import '../petrol_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/widgets.dart';
import '../../core/app_version.dart';
import '../../core/account_deletion.dart';
import '../notifications_screen.dart';
import '../update_gate.dart';
import '../pms/pms_employee_file.dart';
import 'pms_shell.dart';

/// «المزيد» — the project-management shell's settings & account hub, replacing
/// the old Alerts tab. User header, quick preferences (language / theme /
/// notifications), account shortcuts, and help — the settings other apps have.
class PmsMoreScreen extends StatelessWidget {
  const PmsMoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    context.watch<LangProvider>();
    final p = auth.profile;
    final name = p?.name ?? '';
    final unread = p?.unreadNotifications ?? 0;
    final avatar = (p != null) ? auth.api.userAvatarUrl(p.userId) : null;
    final ifaces = auth.interfaces ?? const {};
    final systems = <(String, String, String, IconData, int)>[
      ('cafm', 'إدارة المرافق', 'Facilities (CAFM)', Icons.apartment_rounded, 0xFFC0392B),
      ('pms', 'إدارة المشاريع', 'Projects (PMS)', Icons.account_tree_rounded, 0xFF2563EB),
      ('c2c', 'CARE 2 CARE', 'CARE 2 CARE', Icons.home_repair_service_rounded, 0xFF0EA5A4),
      ('management', 'الإدارة الخلفية', 'Management', Icons.dashboard_customize_rounded, 0xFF714B67),
    ].where((s) => ifaces[s.$1] == true).toList();

    return Scaffold(
      backgroundColor: Pms.bg,
      body: ListView(padding: EdgeInsets.zero, children: [
        // ===== header =====
        Container(
          padding: const EdgeInsets.fromLTRB(20, 54, 20, 22),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [Pms.violet, Pms.deep, Color(0xFF3B0F73)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(shape: BoxShape.circle,
                  border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
              child: CircleAvatar(
                radius: 30, backgroundColor: Colors.white24,
                backgroundImage: avatar != null ? NetworkImage(avatar) : null,
                onBackgroundImageError: (_, __) {},
                child: avatar == null && name.isNotEmpty
                    ? Text(name.trim().characters.first,
                        style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900))
                    : null,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                child: Text(tr('إدارة المشاريع', 'Project management'),
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
              ),
            ])),
          ]),
        ),
        const SizedBox(height: 10),

        // ===== account =====
        _header(tr('حسابي', 'My account')),
        if (p?.employeeId != null)
          _tile(context, Icons.badge_rounded, tr('بياناتي', 'My data'), const Color(0xFF0D9488),
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => PmsEmployeeFileScreen(employeeId: p!.employeeId!, name: name)))),
        _tile(context, Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), const Color(0xFF6366F1),
            badge: unread,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()))),

        // ===== أدوات =====
        _header(tr('أدوات', 'Tools')),
        _tile(context, Icons.local_gas_station_rounded, tr('إدارة الوقود', 'Fuel management'), const Color(0xFFE8873B),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PetrolScreen()))),

        // ===== systems =====
        if (systems.length > 1) ...[
          _header(tr('الأنظمة المتاحة لك', 'Your systems')),
          for (final s in systems)
            _tile(context, s.$4, tr(s.$2, s.$3), Color(s.$5),
                onTap: () => auth.setAppMode(s.$1 == 'management' ? 'backend' : s.$1)),
          _tile(context, Icons.swap_horiz_rounded, tr('التبديل بين الأنظمة', 'System switcher'),
              const Color(0xFF6366F1), onTap: () => auth.setAppMode('choose')),
        ],

        // ===== preferences =====
        _header(tr('التفضيلات والإعدادات', 'Preferences & settings')),
        _tile(context, Icons.language_rounded, tr('اللغة', 'Language'), const Color(0xFF16A34A),
            onTap: () => showLanguagePicker(context)),
        _tile(context, Icons.dark_mode_rounded, tr('المظهر (فاتح/داكن)', 'Theme (light/dark)'), const Color(0xFF334155),
            onTap: () => _themeInfo(context)),
        _tile(context, Icons.system_update_rounded, tr('التحقق من التحديثات', 'Check for updates'), const Color(0xFF0891B2),
            onTap: () async { UpdateGate.reset(); await UpdateGate.check(context, silentWhenCurrent: false); }),

        // ===== help =====
        _header(tr('المساعدة والدعم', 'Help & support')),
        _tile(context, Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), const Color(0xFF16A34A),
            onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/privacy.html')),
        _tile(context, Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), const Color(0xFF64748B),
            onTap: () => _openUrl(context, 'https://ecare.care-kw.com/care_hr/static/legal/terms.html')),
        _tile(context, Icons.info_outline_rounded, tr('عن التطبيق', 'About'), const Color(0xFF0E3A5F),
            onTap: () => _about(context)),
        _tile(context, Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), const Color(0xFFE11D48),
            danger: true, onTap: () => auth.logout()),
        _tile(context, Icons.delete_forever_rounded, tr('حذف الحساب', 'Delete account'), const Color(0xFFB91C1C),
            danger: true, onTap: () => showDeleteAccountFlow(context)),

        const SizedBox(height: 22),
        Center(child: Text('CARE', style: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.w900, letterSpacing: 2))),
        const SizedBox(height: 3),
        Center(child: Text('v${AppVersion.value}',
            style: TextStyle(color: Colors.grey.shade400, fontSize: 11, fontWeight: FontWeight.w600))),
        const SizedBox(height: 28),
      ]),
    );
  }

  Widget _header(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 4),
        child: Align(alignment: Alignment.centerRight,
            child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15))),
      );

  Widget _tile(BuildContext context, IconData i, String t, Color c,
      {VoidCallback? onTap, bool danger = false, int badge = 0}) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          child: ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            leading: Container(width: 38, height: 38,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: Icon(i, color: c, size: 20)),
            title: Text(t, style: TextStyle(fontWeight: FontWeight.w700, color: danger ? const Color(0xFFE11D48) : null)),
            trailing: badge > 0
                ? Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: const BoxDecoration(color: Color(0xFFE11D48), shape: BoxShape.circle),
                    child: Text('$badge', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)))
                : const Icon(Icons.chevron_left_rounded, color: Colors.grey),
            onTap: onTap,
          ),
        ),
      );

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

  void _about(BuildContext context) => showAboutDialog(context: context,
        applicationName: 'CARE', applicationVersion: 'v${AppVersion.value}',
        applicationLegalese: '© CARE — care-kw.com',
        children: [Padding(padding: const EdgeInsets.only(top: 12),
          child: Text(tr('منصّة إدارة المشاريع والخدمات المتكاملة.', 'Integrated projects & services management platform.')))]);
}
