import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import 'home_screen.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'notifications_screen.dart';
import 'supervisor_screen.dart';
import 'more_screen.dart';
import 'client_analytics_screen.dart';

class _Tab {
  const _Tab(this.icon, this.label, this.screen);
  final IconData icon;
  final String label;
  final Widget screen;
}

/// Persistent bottom navigation shell — a nav bar with everything, role-aware.
class MainShell extends StatefulWidget {
  const MainShell({super.key});
  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _idx = 0;

  List<_Tab> _tabs(profile) {
    const home = _Tab(Icons.home_rounded, 'الرئيسية', HomeScreen());
    const notif = _Tab(Icons.notifications_rounded, 'الإشعارات', NotificationsScreen());
    const more = _Tab(Icons.grid_view_rounded, 'المزيد', MoreScreen());
    if (profile.role == 'client') {
      return const [
        home,
        _Tab(Icons.insights_rounded, 'الإحصائيات', ClientAnalyticsScreen()),
        notif, more,
      ];
    }
    if (profile.isAdmin) {
      return const [
        home,
        _Tab(Icons.assignment_rounded, 'الأعمال', WorkOrdersScreen()),
        _Tab(Icons.dashboard_customize_rounded, 'المشرف', SupervisorScreen()),
        notif, more,
      ];
    }
    // worker / security
    return const [
      home,
      _Tab(Icons.assignment_rounded, 'مهامي', WorkOrdersScreen()),
      _Tab(Icons.qr_code_scanner_rounded, 'مسح', ScanScreen()),
      notif, more,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<AuthProvider>().profile!;
    final tabs = _tabs(profile);
    final idx = _idx.clamp(0, tabs.length - 1);
    return Scaffold(
      // Build only the active tab so the scanner camera mounts only when shown.
      body: tabs[idx].screen,
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        destinations: [
          for (final t in tabs)
            NavigationDestination(icon: Icon(t.icon), label: t.label),
        ],
      ),
    );
  }
}
