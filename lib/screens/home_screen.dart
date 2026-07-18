import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import '../core/i18n.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'security_home.dart';
import 'supervisor_screen.dart';
import 'client_home.dart';
import 'admin_home.dart';
import 'service_screen.dart';
import 'shift_card.dart';
import 'client_inventory_screen.dart';
import 'my_profile_screen.dart';
import 'employee_attendance_screen.dart';
import 'notifications_screen.dart';

/// Role router: the same app opens a different face depending on who logs in.
/// A security guard lands on the security command screen; a cleaner/agri worker
/// on the task-and-scan worker screen.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<AuthProvider>().profile!;
    if (profile.isAdmin) return const AdminHome();
    if (profile.role == 'client') return const ClientHome();
    if (profile.role == 'security') return const SecurityHome();
    return const WorkerHome();
  }
}

/// Professional worker home: a branded identity header with live shift status,
/// a KPI row, and a clean grid of the actions a field worker actually needs —
/// tasks, check-in, quality rounds, issuing materials to any location, and their
/// own achievements file.
class WorkerHome extends StatelessWidget {
  const WorkerHome({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final p = auth.profile!;
    final st = ServiceTheme.of(p.role);
    final accent = st.accent;
    void go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

    final actions = <(IconData, String, String, Color, VoidCallback)>[
      (Icons.assignment_rounded, 'مهامي', 'My tasks', accent, () => go(const WorkOrdersScreen())),
      (Icons.qr_code_scanner_rounded, 'مسح حضور', 'Check-in', const Color(0xFF0891B2), () => go(const ScanScreen())),
      if (p.role == 'cleaning')
        (Icons.fact_check_rounded, 'تدقيق النظافة', 'Cleaning audit', const Color(0xFF0EA5E9), () => go(const ServiceScreen(kind: 'cleaning', title: 'تدقيق النظافة'))),
      if (p.role == 'agriculture')
        (Icons.grass_rounded, 'مناطق الريّ', 'Irrigation', const Color(0xFF16A34A), () => go(const ServiceScreen(kind: 'agri', title: 'مناطق الريّ'))),
      if (p.role == 'facade')
        (Icons.roofing_rounded, 'تصاريح الارتفاع', 'Height permits', const Color(0xFF7C3AED), () => go(const ServiceScreen(kind: 'facade', title: 'تصاريح الواجهات'))),
      (Icons.inventory_2_rounded, 'صرف مواد', 'Issue materials', const Color(0xFF0E7490), () => go(const ClientInventoryScreen())),
      (Icons.workspace_premium_rounded, 'إنجازاتي', 'My achievements', const Color(0xFFF59E0B), () => go(const MyProfileScreen())),
      if (p.employeeId != null)
        (Icons.fingerprint_rounded, 'حضوري', 'My attendance', const Color(0xFF6D28D9), () => go(EmployeeAttendanceScreen(employeeId: p.employeeId!, name: p.name))),
      if (p.isSupervisor)
        (Icons.dashboard_customize_rounded, 'لوحة المشرف', 'Supervisor', const Color(0xFF0D9488), () => go(const SupervisorScreen())),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: ListView(padding: EdgeInsets.zero, children: [
        // ===== branded identity header =====
        CustomPaint(
          painter: const BrandPattern(opacity: 0.07),
          child: Container(
            padding: const EdgeInsets.fromLTRB(18, 0, 10, 18),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [accent, Color.lerp(accent, Colors.black, 0.42)!], begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(26)),
            ),
            child: SafeArea(bottom: false, child: Column(children: [
              Row(children: [
                Text(st.icon, style: const TextStyle(fontSize: 22)),
                const SizedBox(width: 8),
                Expanded(child: Text(st.label, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                IconButton(icon: const Icon(Icons.notifications_rounded, color: Colors.white),
                    onPressed: () => go(const NotificationsScreen())),
                IconButton(icon: const Icon(Icons.logout_rounded, color: Colors.white),
                    onPressed: () => context.read<AuthProvider>().logout()),
              ]),
              const SizedBox(height: 4),
              Row(children: [
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
                  child: CircleAvatar(radius: 28, backgroundColor: Colors.white,
                      child: Text(p.name.isNotEmpty ? p.name.trim().characters.first : '?',
                          style: TextStyle(color: accent, fontSize: 24, fontWeight: FontWeight.w900))),
                ),
                const SizedBox(width: 14),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 6),
                  Row(children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                      child: Text(tr('مهامي المفتوحة', 'Open tasks') + ': ${p.openWorkOrders}',
                          style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
                    ),
                  ]),
                ])),
              ]),
              const SizedBox(height: 12),
              const ShiftToggle(),
            ])),
          ),
        ),
        // ===== KPI row =====
        Padding(padding: const EdgeInsets.fromLTRB(12, 14, 12, 4), child: MyStatsRow(counts: p.counts)),
        // ===== primary action: check-in =====
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: accent, minimumSize: const Size.fromHeight(54)),
            onPressed: () => go(const ScanScreen()),
            icon: const Icon(Icons.qr_code_scanner_rounded),
            label: Text(tr('امسح رمز الموقع — إثبات الحضور', 'Scan location — check in'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          ),
        ),
        // ===== action grid =====
        Padding(
          padding: const EdgeInsets.all(12),
          child: GridView.count(
            crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.98,
            children: [for (final a in actions) _ActionTile(icon: a.$1, ar: a.$2, en: a.$3, color: a.$4, onTap: a.$5)],
          ),
        ),
        const SizedBox(height: 20),
      ]),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.icon, required this.ar, required this.en, required this.color, required this.onTap});
  final IconData icon;
  final String ar, en;
  final Color color;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16), onTap: onTap,
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(width: 44, height: 44, alignment: Alignment.center,
                  decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(13)),
                  child: Icon(icon, color: color, size: 22)),
              const SizedBox(height: 8),
              Text(tr(ar, en), textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, color: Color(0xFF0E3A5F))),
            ]),
          ),
        ),
      );
}

