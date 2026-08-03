import 'package:flutter/material.dart';
import 'client_activity_screen.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'home_screen.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'my_profile_screen.dart';
import 'supervisor_screen.dart';
import 'more_screen.dart';
import 'client_analytics_screen.dart';
import 'client_workorders_screen.dart';
import 'client_waste_screen.dart';
import 'client_account_screen.dart';

class _Tab {
  const _Tab(this.icon, this.label, this.screen, {this.live = false});
  final IconData icon;
  final String label;
  final Widget screen;
  final bool live; // renders a red "live" dot on the icon
}

/// Persistent bottom navigation shell — a nav bar with everything, role-aware.
class MainShell extends StatefulWidget {
  const MainShell({super.key});
  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _idx = 0;
  List<String> _serviceSections = []; // client's visible SERVICE section codes

  @override
  void initState() {
    super.initState();
    _loadSections();
  }

  Future<void> _loadSections() async {
    try {
      final s = await context.read<AuthProvider>().api.clientSections();
      final svc = <String>[];
      for (final sec in (s['sections'] as List? ?? [])) {
        if ((sec as Map)['service_type'] != null) svc.add('${sec['code']}');
      }
      if (mounted) setState(() { _serviceSections = svc; _idx = 0; });
    } catch (_) {}
  }

  List<_Tab> _tabs(profile) {
    final home = _Tab(Icons.home_rounded, tr('الرئيسية', 'Home'), const HomeScreen());
    // "إنجازاتي" — a rich personal dashboard replaces the plain alerts tab
    // (notifications stay reachable from its header bell and the home app bars).
    final mine = _Tab(Icons.workspace_premium_rounded, tr('إنجازاتي', 'My profile'), const MyProfileScreen());
    final more = _Tab(Icons.grid_view_rounded, tr('المزيد', 'More'), const MoreScreen());
    if (profile.role == 'client') {
      // waste-only client → a waste-tailored nav (orders / trips / stats)
      if (_serviceSections.length == 1 && _serviceSections.first == 'waste') {
        return [
          _Tab(Icons.recycling_rounded, tr('طلبات النقل', 'Collection'), const ClientWasteScreen(key: ValueKey('w_orders'), initialKind: 'orders', embedded: true)),
          _Tab(Icons.local_shipping_rounded, tr('الرحلات', 'Trips'), const ClientWasteScreen(key: ValueKey('w_trips'), initialKind: 'trips', embedded: true)),
          _Tab(Icons.insights_rounded, tr('الإحصائيات', 'Statistics'), const WasteStatsScreen()),
          _Tab(Icons.person_rounded, tr('حسابي', 'Account'), const ClientAccountScreen()),
        ];
      }
      // A client is an organisation, not one employee — "my achievements" makes
      // no sense for them. Give them a LIVE feed of what's happening on their
      // sites right now, with a red live dot.
      return [
        home,
        _Tab(Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'), const ClientWorkOrdersScreen()),
        _Tab(Icons.insights_rounded, tr('الإحصائيات', 'Analytics'), const ClientAnalyticsScreen()),
        _Tab(Icons.sensors_rounded, tr('لايف', 'Live'), const ClientActivityScreen(), live: true),
        more,
      ];
    }
    if (profile.isAdmin) {
      return [
        home,
        _Tab(Icons.assignment_rounded, tr('الأعمال', 'Work'), const WorkOrdersScreen()),
        _Tab(Icons.dashboard_customize_rounded, tr('المشرف', 'Supervisor'), const SupervisorScreen()),
        mine, more,
      ];
    }
    // worker / security
    return [
      home,
      _Tab(Icons.assignment_rounded, tr('مهامي', 'My tasks'), const WorkOrdersScreen()),
      _Tab(Icons.qr_code_scanner_rounded, tr('مسح', 'Scan'), const ScanScreen()),
      mine, more,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<AuthProvider>().profile!;
    final tabs = _tabs(profile);
    final idx = _idx.clamp(0, tabs.length - 1);
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      body: Column(children: [
        if (auth.isImpersonating) _banner(context, profile.name),
        // Build only the active tab so the scanner camera mounts only when shown.
        Expanded(child: tabs[idx].screen),
      ]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        destinations: [
          for (final t in tabs)
            NavigationDestination(
              icon: t.live
                  ? Stack(clipBehavior: Clip.none, children: [
                      Icon(t.icon),
                      Positioned(right: -3, top: -2, child: Container(
                        width: 9, height: 9,
                        decoration: BoxDecoration(
                          color: const Color(0xFFE11D48), shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 1.5),
                        ),
                      )),
                    ])
                  : Icon(t.icon),
              label: t.label,
            ),
        ],
      ),
    );
  }

  Widget _banner(BuildContext context, String name) => Material(
        color: const Color(0xFF6366F1),
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(children: [
              const Icon(Icons.visibility, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Expanded(child: Text(tr('عرض تجريبي كـ: $name', 'Demo view as: $name'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13))),
              TextButton(
                onPressed: () => context.read<AuthProvider>().exitImpersonation().then((_) => setState(() => _idx = 0)),
                child: Text(tr('رجوع للأدمن', 'Back to admin'), style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
              ),
            ]),
          ),
        ),
      );

}
