import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/auth.dart';
import '../../../core/i18n.dart';
import '../../driver_waste_trips.dart';
import '../../receiver_waste.dart';
import 'staff_jobs.dart';
import 'staff_team.dart';
import 'staff_dashboard.dart';

/// Crew (staff) palette — a distinct teal identity so field crew instantly
/// know they're in the work workspace, not the customer storefront.
class Crew {
  static const teal = Color(0xFF0D9488);
  static const deep = Color(0xFF115E59);
  static const bg = Color(0xFFF1F6F5);
  static const ink = Color(0xFF1E293B);
  static const slate = Color(0xFF64748B);
  static const amber = Color(0xFFD97706);
  static const green = Color(0xFF16A34A);
  static const blue = Color(0xFF2563EB);

  static Color stateColor(String s) => switch (s) {
        'in_progress' => amber,
        'done' => green,
        'assigned' => blue,
        'confirmed' => const Color(0xFF0891B2),
        'cancelled' => const Color(0xFF9CA3AF),
        _ => slate,
      };
}

/// Adaptive workspace for the five CARE 2 CARE field roles. It loads the
/// logged-in provider's role + capabilities from the API and assembles the
/// right set of tabs — a worker sees "My jobs", an ops manager sees the full
/// operations dashboard, team roster and assignment tools.
class StaffShell extends StatefulWidget {
  const StaffShell({super.key});
  @override
  State<StaffShell> createState() => _StaffShellState();
}

class _StaffShellState extends State<StaffShell> {
  Future<Map<String, dynamic>>? _me;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _me = context.read<AuthProvider>().api.c2cStaffWhoami();
  }

  void _reload() => setState(() => _me = context.read<AuthProvider>().api.c2cStaffWhoami());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _me,
      builder: (_, snap) {
        if (!snap.hasData) {
          return const Scaffold(backgroundColor: Crew.bg, body: Center(child: CircularProgressIndicator(color: Crew.teal)));
        }
        final me = snap.data!;
        final caps = (me['caps'] as Map?) ?? {};
        final can = List<String>.from((caps['can'] as List?) ?? []);
        final scope = '${caps['scope']}';
        final isManager = scope == 'team' || scope == 'area' || scope == 'all';
        final hasTeam = can.contains('assign') || can.contains('manage_team');

        // assemble tabs by role
        final tabs = <_StaffTab>[
          _StaffTab(
            isManager ? Icons.space_dashboard_rounded : Icons.today_rounded,
            isManager ? tr('العمليات', 'Operations') : (me['role'] == 'driver' ? tr('مساري', 'My route') : tr('مهام اليوم', 'Today')),
            isManager ? StaffDashboard(me: me, onOpenJobs: () => setState(() => _tab = 1)) : StaffJobsScreen(me: me, embedded: true, defaultFilter: 'today'),
          ),
          _StaffTab(Icons.assignment_rounded, tr('المهام', 'Jobs'), StaffJobsScreen(me: me, embedded: true)),
          // short labels: a nav bar of 5-6 destinations cannot fit long Arabic
          // titles — they wrap and collide under the icons.
          if (me['role'] == 'driver' || me['role'] == 'ops_manager')
            _StaffTab(Icons.local_shipping_rounded, tr('النفايات', 'Trips'), const DriverWasteTripsScreen()),
          if (me['role'] == 'worker' || me['role'] == 'supervisor' || me['role'] == 'ops_manager')
            _StaffTab(Icons.factory_rounded, tr('المركز', 'Intake'), const ReceiverWasteScreen()),
          if (hasTeam) _StaffTab(Icons.groups_rounded, tr('الفريق', 'Team'), StaffTeamScreen(me: me)),
          _StaffTab(Icons.person_rounded, tr('حسابي', 'Me'), _AccountTab(me: me, onChanged: _reload)),
        ];
        final idx = _tab.clamp(0, tabs.length - 1);

        return Scaffold(
          backgroundColor: Crew.bg,
          body: IndexedStack(index: idx, children: [for (final t in tabs) t.body]),
          bottomNavigationBar: NavigationBarTheme(
            data: NavigationBarThemeData(
              backgroundColor: Colors.white,
              indicatorColor: Crew.teal.withValues(alpha: 0.14),
              labelTextStyle: WidgetStateProperty.all(const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            ),
            child: NavigationBar(
              selectedIndex: idx,
              height: 66,
              // With 5+ destinations (an ops manager gets six) every label no
              // longer fits side by side, so show only the active one — the
              // icons then sit centred in their own slot instead of colliding.
              labelBehavior: tabs.length > 4
                  ? NavigationDestinationLabelBehavior.onlyShowSelected
                  : NavigationDestinationLabelBehavior.alwaysShow,
              onDestinationSelected: (i) => setState(() => _tab = i),
              destinations: [
                for (final t in tabs)
                  NavigationDestination(
                    icon: Icon(t.icon, color: Crew.slate),
                    selectedIcon: Icon(t.icon, color: Crew.teal),
                    label: t.label,
                    tooltip: t.label,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _StaffTab {
  _StaffTab(this.icon, this.label, this.body);
  final IconData icon;
  final String label;
  final Widget body;
}

/// Crew account tab — identity, availability toggle, and switch-mode / logout.
class _AccountTab extends StatefulWidget {
  const _AccountTab({required this.me, required this.onChanged});
  final Map<String, dynamic> me;
  final VoidCallback onChanged;
  @override
  State<_AccountTab> createState() => _AccountTabState();
}

class _AccountTabState extends State<_AccountTab> {
  late bool _available = widget.me['available'] == true;
  bool _busy = false;

  Future<void> _toggle(bool v) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.c2cStaffAvailable(v);
      setState(() => _available = v);
    } catch (_) {} finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = widget.me;
    final team = (me['team'] as List?) ?? [];
    return SafeArea(
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(gradient: const LinearGradient(colors: [Crew.teal, Crew.deep], begin: Alignment.topRight, end: Alignment.bottomLeft), borderRadius: BorderRadius.circular(20), boxShadow: [BoxShadow(color: Crew.teal.withValues(alpha: 0.3), blurRadius: 14, offset: const Offset(0, 6))]),
          child: Row(children: [
            CircleAvatar(radius: 30, backgroundColor: Colors.white.withValues(alpha: 0.2), backgroundImage: me['image'] != null ? NetworkImage('${me['image']}') : null, child: me['image'] == null ? const Icon(Icons.person, color: Colors.white, size: 30) : null),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${me['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
              const SizedBox(height: 4),
              Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)), child: Text('${me['role_label']}', style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800))),
            ])),
          ]),
        ),
        const SizedBox(height: 14),
        Container(
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
          child: Column(children: [
            SwitchListTile(
              value: _available, activeColor: Crew.green,
              onChanged: _busy ? null : _toggle,
              secondary: Icon(_available ? Icons.check_circle : Icons.do_not_disturb_on, color: _available ? Crew.green : Crew.slate),
              title: Text(tr('متاح للعمل', 'Available for work'), style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(_available ? tr('يظهر اسمك عند إسناد المهام', 'Assignable to new jobs') : tr('لن تُسند لك مهام جديدة', 'Not assignable'), style: const TextStyle(fontSize: 11.5)),
            ),
            if (me['leader'] != null) ...[const Divider(height: 1), ListTile(leading: const Icon(Icons.supervisor_account_outlined, color: Crew.slate), title: Text(tr('قائد الفريق', 'Team leader')), trailing: Text('${me['leader']}', style: const TextStyle(fontWeight: FontWeight.w700)))],
            if (me['supervisor'] != null) ...[const Divider(height: 1), ListTile(leading: const Icon(Icons.shield_outlined, color: Crew.slate), title: Text(tr('المشرف', 'Supervisor')), trailing: Text('${me['supervisor']}', style: const TextStyle(fontWeight: FontWeight.w700)))],
            if (team.isNotEmpty) ...[const Divider(height: 1), ListTile(leading: const Icon(Icons.groups_outlined, color: Crew.slate), title: Text(tr('حجم الفريق', 'Team size')), trailing: Text('${team.length}', style: const TextStyle(fontWeight: FontWeight.w800, color: Crew.teal)))],
          ]),
        ),
        const SizedBox(height: 14),
        OutlinedButton.icon(
          onPressed: () => context.read<AuthProvider>().setAppMode('choose'),
          icon: const Icon(Icons.swap_horiz_rounded, color: Crew.teal),
          label: Text(tr('تبديل الوضع', 'Switch workspace'), style: const TextStyle(color: Crew.teal, fontWeight: FontWeight.w800)),
          style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50), side: const BorderSide(color: Crew.teal), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
        ),
        const SizedBox(height: 10),
        TextButton.icon(
          onPressed: () => context.read<AuthProvider>().logout(),
          icon: const Icon(Icons.logout_rounded, color: Color(0xFFC0392B)),
          label: Text(tr('تسجيل الخروج', 'Log out'), style: const TextStyle(color: Color(0xFFC0392B), fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }
}
