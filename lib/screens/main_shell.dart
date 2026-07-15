import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'home_screen.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'notifications_screen.dart';
import 'supervisor_screen.dart';
import 'more_screen.dart';
import 'client_analytics_screen.dart';
import 'client_workorders_screen.dart';
import 'client_waste_screen.dart';
import 'client_account_screen.dart';

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
    final notif = _Tab(Icons.notifications_rounded, tr('الإشعارات', 'Alerts'), const NotificationsScreen());
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
      return [
        home,
        _Tab(Icons.assignment_rounded, tr('أوامر العمل', 'Work orders'), const ClientWorkOrdersScreen()),
        _Tab(Icons.insights_rounded, tr('الإحصائيات', 'Analytics'), const ClientAnalyticsScreen()),
        notif, more,
      ];
    }
    if (profile.isAdmin) {
      return [
        home,
        _Tab(Icons.assignment_rounded, tr('الأعمال', 'Work'), const WorkOrdersScreen()),
        _Tab(Icons.dashboard_customize_rounded, tr('المشرف', 'Supervisor'), const SupervisorScreen()),
        notif, more,
      ];
    }
    // worker / security
    return [
      home,
      _Tab(Icons.assignment_rounded, tr('مهامي', 'My tasks'), const WorkOrdersScreen()),
      _Tab(Icons.qr_code_scanner_rounded, tr('مسح', 'Scan'), const ScanScreen()),
      notif, more,
    ];
  }

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<AuthProvider>().profile!;
    final tabs = _tabs(profile);
    final idx = _idx.clamp(0, tabs.length - 1);
    final auth = context.watch<AuthProvider>();
    final canSwitch = profile.isAdmin || auth.isImpersonating;
    return Scaffold(
      body: Column(children: [
        if (auth.isImpersonating) _banner(context, profile.name),
        // Build only the active tab so the scanner camera mounts only when shown.
        Expanded(child: tabs[idx].screen),
      ]),
      floatingActionButton: canSwitch
          ? FloatingActionButton.small(
              heroTag: 'switcher',
              backgroundColor: const Color(0xFF6366F1),
              onPressed: () => _openSwitcher(context),
              child: const Icon(Icons.switch_account),
            )
          : null,
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

  Widget _banner(BuildContext context, String name) => Material(
        color: const Color(0xFF6366F1),
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Row(children: [
              const Icon(Icons.visibility, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Expanded(child: Text('عرض تجريبي كـ: $name',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13))),
              TextButton(
                onPressed: () => context.read<AuthProvider>().exitImpersonation().then((_) => setState(() => _idx = 0)),
                child: const Text('رجوع للأدمن', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
              ),
            ]),
          ),
        ),
      );

  Future<void> _openSwitcher(BuildContext context) async {
    final auth = context.read<AuthProvider>();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.7, maxChildSize: 0.9,
        builder: (c, sc) => FutureBuilder<List<dynamic>>(
          future: auth.impersonatableUsers(),
          builder: (c, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
            final users = snap.data!;
            return ListView(controller: sc, children: [
              const Padding(padding: EdgeInsets.all(16),
                  child: Text('عرض التطبيق كـ (تجريبي)', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900))),
              for (final u in users)
                ListTile(
                  leading: CircleAvatar(child: Text('${u['name']}'.characters.first)),
                  title: Text('${u['name']}'),
                  subtitle: Text('${u['login']} · ${u['kind']}'),
                  onTap: () async {
                    Navigator.pop(c);
                    try {
                      await auth.impersonate('${u['login']}');
                      if (mounted) setState(() => _idx = 0);
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                    }
                  },
                ),
            ]);
          },
        ),
      ),
    );
  }
}
