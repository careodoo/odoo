import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/widgets.dart';
import '../notifications_screen.dart';
import 'pms_projects.dart';
import 'pms_tasks.dart';
import '../my/my_screen.dart';

class Pms {
  static const violet = Color(0xFF7C3AED);
  static const deep = Color(0xFF5B21B6);
  static const bg = Color(0xFFF6F5FB);
  static const ink = Color(0xFF1E1B33);
  static const slate = Color(0xFF64748B);
  static const amber = Color(0xFFF59E0B);
  static const red = Color(0xFFE11D48);
  static const green = Color(0xFF16A34A);
}

/// Native project management. This replaces a WebView on /my/pm.
class PmsShell extends StatefulWidget {
  const PmsShell({super.key});
  @override
  State<PmsShell> createState() => _PmsShellState();
}

class _PmsShellState extends State<PmsShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final tabs = [
      const _T(Icons.space_dashboard_rounded, 'لوحة المشاريع', 'Dashboard', PmsDashboard()),
      const _T(Icons.account_tree_rounded, 'المشاريع', 'Projects', PmsProjectsScreen()),
      const _T(Icons.checklist_rounded, 'مهامي', 'My tasks', PmsTasksScreen(filter: 'mine', title: 'مهامي')),
      const _T(Icons.account_circle_rounded, 'My', 'My', MyScreen(accent: Pms.violet)),
      const _T(Icons.notifications_rounded, 'الإشعارات', 'Alerts', NotificationsScreen()),
    ];
    final idx = _tab.clamp(0, tabs.length - 1);
    return Scaffold(
      backgroundColor: Pms.bg,
      body: IndexedStack(index: idx, children: [for (final t in tabs) t.body]),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: Colors.white,
          indicatorColor: Pms.violet.withValues(alpha: 0.14),
          labelTextStyle: WidgetStateProperty.all(const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
        ),
        child: NavigationBar(
          height: 62,
          selectedIndex: idx,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: [
            for (final t in tabs)
              NavigationDestination(icon: Icon(t.icon), selectedIcon: Icon(t.icon, color: Pms.violet),
                  label: gLang == 'en' ? t.en : t.ar),
          ],
        ),
      ),
    );
  }
}

class _T {
  const _T(this.icon, this.ar, this.en, this.body);
  final IconData icon;
  final String ar, en;
  final Widget body;
}

/// KPI dashboard — every number opens the matching task list.
class PmsDashboard extends StatefulWidget {
  const PmsDashboard({super.key});
  @override
  State<PmsDashboard> createState() => _PmsDashboardState();
}

class _PmsDashboardState extends State<PmsDashboard> {
  late Future<Map<String, dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.pmsOverview());

  @override
  Widget build(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    return Scaffold(
      backgroundColor: Pms.bg,
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: ListView(padding: EdgeInsets.zero, children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 54, 20, 24),
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [Pms.violet, Pms.deep, Color(0xFF3B0F73)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(28))),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('إدارة المشاريع', 'Project management'),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 21)),
                const SizedBox(height: 3),
                Text(name.isEmpty ? tr('المشاريع والمهام', 'Projects & tasks') : tr('مرحبًا $name', 'Hi $name'),
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 12.5)),
              ])),
              IconButton(
                tooltip: tr('تبديل الوضع', 'Switch mode'),
                icon: const Icon(Icons.swap_horiz_rounded, color: Colors.white),
                onPressed: () => context.read<AuthProvider>().setAppMode('choose')),
              IconButton(
                tooltip: tr('اللغة', 'Language'),
                icon: const Icon(Icons.language_rounded, color: Colors.white),
                onPressed: () => showLanguagePicker(context, onChanged: () => setState(() {}))),
            ]),
          ),
          FutureBuilder<Map<String, dynamic>>(
            future: _f,
            builder: (_, snap) {
              if (snap.hasError) {
                return Padding(padding: const EdgeInsets.all(30),
                    child: Center(child: Text('${snap.error}', textAlign: TextAlign.center,
                        style: const TextStyle(color: Pms.slate))));
              }
              if (!snap.hasData) {
                return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
              }
              final d = snap.data!;
              return Padding(
                padding: const EdgeInsets.all(12),
                child: Column(children: [
                  Row(children: [
                    _kpi('📁', d['projects'], tr('المشاريع', 'Projects'), Pms.violet,
                        () => _open(const PmsProjectsScreen())),
                    const SizedBox(width: 10),
                    _kpi('🧾', d['tasks'], tr('كل المهام', 'All tasks'), const Color(0xFF0891B2),
                        () => _open(const PmsTasksScreen(filter: '', title: 'كل المهام'))),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: [
                    _kpi('👤', d['my_tasks'], tr('مهامي المفتوحة', 'My open'), const Color(0xFF2563EB),
                        () => _open(const PmsTasksScreen(filter: 'mine', title: 'مهامي'))),
                    const SizedBox(width: 10),
                    _kpi('⏰', d['due_today'], tr('تستحق اليوم', 'Due today'), Pms.amber,
                        () => _open(const PmsTasksScreen(filter: 'today', title: 'تستحق اليوم'))),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: [
                    _kpi('🔥', d['overdue'], tr('متأخرة', 'Overdue'), Pms.red,
                        () => _open(const PmsTasksScreen(filter: 'overdue', title: 'متأخرة'))),
                    const SizedBox(width: 10),
                    _kpi('✅', d['done'], tr('منجزة', 'Done'), Pms.green,
                        () => _open(const PmsTasksScreen(filter: 'done', title: 'منجزة'))),
                  ]),
                ]),
              );
            },
          ),
        ]),
      ),
    );
  }

  void _open(Widget w) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => w));
    _reload();
  }

  Widget _kpi(String ic, dynamic v, String label, Color c, VoidCallback onTap) => Expanded(
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(16),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
                      child: Text(ic, style: const TextStyle(fontSize: 15))),
                  const Spacer(),
                  Icon(Icons.chevron_left_rounded, color: c.withValues(alpha: 0.5), size: 18),
                ]),
                const SizedBox(height: 10),
                Text('${v ?? 0}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 23, color: c, height: 1)),
                const SizedBox(height: 2),
                Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Pms.ink)),
              ]),
            ),
          ),
        ),
      );
}
