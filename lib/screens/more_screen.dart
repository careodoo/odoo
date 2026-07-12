import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'notifications_screen.dart';
import 'supervisor_screen.dart';
import 'admin_home.dart';
import 'security_incidents_screen.dart';
import 'security_list_screen.dart';

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

    header('العمل');
    tile(Icons.assignment, 'أوامر العمل', const WorkOrdersScreen());
    if (p.role != 'client') tile(Icons.qr_code_scanner, 'مسح رمز الموقع', const ScanScreen());

    if (p.role == 'security') {
      header('الأمن');
      tile(Icons.report, 'البلاغات الأمنية', const SecurityIncidentsScreen(), c: const Color(0xFFE5484D));
      tile(Icons.route, 'الدوريات', const SecurityListScreen(kind: 'patrols', title: 'الدوريات'));
      tile(Icons.vpn_key, 'عهدة المفاتيح', const SecurityListScreen(kind: 'keys', title: 'عهدة المفاتيح'));
      tile(Icons.badge, 'تصاريح البوابة', const SecurityListScreen(kind: 'gatepasses', title: 'تصاريح البوابة'));
    }

    if (p.isSupervisor || p.isAdmin) {
      header('الإدارة');
      tile(Icons.dashboard_customize, 'لوحة المشرف — إسناد', const SupervisorScreen());
      if (p.isAdmin) tile(Icons.business, 'لوحة الشركة', const AdminHome(), c: const Color(0xFF6366F1));
    }

    header('الحساب');
    tile(Icons.notifications, 'الإشعارات', const NotificationsScreen());
    tile(Icons.logout, 'تسجيل الخروج', null, c: const Color(0xFFE5484D),
        onTap: () => context.read<AuthProvider>().logout());

    return Scaffold(
      appBar: AppBar(title: const Text('المزيد')),
      body: ListView(padding: const EdgeInsets.all(14), children: items),
    );
  }
}
