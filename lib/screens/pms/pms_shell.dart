import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/widgets.dart';
import 'pms_projects.dart';
import 'pms_tasks.dart';
import '../my/my_screen.dart';
import 'pms_more.dart';

class Pms {
  // Brand identity: red with gray. `violet`/`deep` are the primary red pair
  // (name kept so the whole app follows from one place); surfaces are neutral gray.
  static const violet = Color(0xFFC0392B); // primary red
  static const deep = Color(0xFF8E2A20); // deep red (gradients)
  static const bg = Color(0xFFF3F4F6); // gray surface
  static const ink = Color(0xFF1F2933); // charcoal text
  static const slate = Color(0xFF6B7280); // gray accent
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
      _T(Icons.checklist_rounded, 'مهامي', 'My tasks', PmsTasksScreen(filter: 'mine', title: tr('مهامي', 'My tasks'))),
      const _T(Icons.account_circle_rounded, 'My', 'My', MyScreen(accent: Pms.violet)),
      const _T(Icons.more_horiz_rounded, 'المزيد', 'More', PmsMoreScreen()),
    ];
    final idx = _tab.clamp(0, tabs.length - 1);

    // «My» tab shows the signed-in user's avatar instead of a generic icon.
    final auth = context.watch<AuthProvider>();
    final p = auth.profile;
    final avatarUrl = p != null ? auth.api.userAvatarUrl(p.userId) : null;
    Widget myIcon(bool selected) => Container(
          padding: const EdgeInsets.all(1.5),
          decoration: BoxDecoration(shape: BoxShape.circle,
              border: Border.all(color: selected ? Pms.violet : Colors.transparent, width: 2)),
          child: CircleAvatar(
            radius: 12,
            backgroundColor: Pms.violet.withValues(alpha: 0.12),
            backgroundImage: avatarUrl != null ? NetworkImage(avatarUrl) : null,
            onBackgroundImageError: (_, __) {},
            child: avatarUrl == null
                ? Icon(Icons.account_circle_rounded, size: 20, color: selected ? Pms.violet : Pms.slate)
                : null,
          ),
        );

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
            for (var i = 0; i < tabs.length; i++)
              NavigationDestination(
                icon: i == 3 ? myIcon(false) : Icon(tabs[i].icon),
                selectedIcon: i == 3 ? myIcon(true) : Icon(tabs[i].icon, color: Pms.violet),
                label: gLang == 'en' ? tabs[i].en : tabs[i].ar),
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
              final total = numOf(d['tasks'], 0);
              final done = numOf(d['done'], 0);
              final pct = total > 0 ? (done / total).clamp(0.0, 1.0).toDouble() : 0.0;
              return Padding(
                padding: const EdgeInsets.fromLTRB(14, 16, 14, 22),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  _overviewCard(d, total.toInt(), done.toInt(), pct),
                  const SizedBox(height: 18),
                  _sectionLabel(tr('حالة المهام', 'Task status'), Icons.donut_large_rounded),
                  const SizedBox(height: 10),
                  _distributionBar(d, total),
                  const SizedBox(height: 12),
                  Row(children: [
                    _statTile(Icons.person_rounded, d['my_tasks'], tr('مهامي المفتوحة', 'My open'),
                        const Color(0xFF2563EB), () => _open(PmsTasksScreen(filter: 'mine', title: tr('مهامي', 'My tasks')))),
                    const SizedBox(width: 10),
                    _statTile(Icons.today_rounded, d['due_today'], tr('تستحق اليوم', 'Due today'),
                        Pms.amber, () => _open(PmsTasksScreen(filter: 'today', title: tr('تستحق اليوم', 'Due today')))),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: [
                    _statTile(Icons.local_fire_department_rounded, d['overdue'], tr('متأخرة', 'Overdue'),
                        Pms.red, () => _open(PmsTasksScreen(filter: 'overdue', title: tr('متأخرة', 'Overdue')))),
                    const SizedBox(width: 10),
                    _statTile(Icons.check_circle_rounded, d['done'], tr('منجزة', 'Done'),
                        Pms.green, () => _open(PmsTasksScreen(filter: 'done', title: tr('منجزة', 'Done')))),
                  ]),
                  const SizedBox(height: 18),
                  _sectionLabel(tr('إجراءات سريعة', 'Quick actions'), Icons.bolt_rounded),
                  const SizedBox(height: 10),
                  Row(children: [
                    _action(Icons.account_tree_rounded, tr('المشاريع', 'Projects'), Pms.violet,
                        () => _open(const PmsProjectsScreen())),
                    const SizedBox(width: 10),
                    _action(Icons.checklist_rounded, tr('كل المهام', 'All tasks'), const Color(0xFF0891B2),
                        () => _open(PmsTasksScreen(filter: '', title: tr('كل المهام', 'All tasks')))),
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

  Widget _sectionLabel(String t, IconData ic) => Row(children: [
        Icon(ic, size: 18, color: Pms.violet),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink)),
      ]);

  /// The headline card — overall completion as a ring, beside the two totals.
  Widget _overviewCard(Map d, int total, int done, double pct) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 14, offset: const Offset(0, 5))],
        ),
        child: Row(children: [
          SizedBox(
            width: 92, height: 92,
            child: Stack(alignment: Alignment.center, children: [
              SizedBox(
                width: 92, height: 92,
                child: CircularProgressIndicator(
                  value: pct, strokeWidth: 9, backgroundColor: Pms.violet.withValues(alpha: 0.12),
                  valueColor: const AlwaysStoppedAnimation(Pms.violet), strokeCap: StrokeCap.round),
              ),
              Column(mainAxisSize: MainAxisSize.min, children: [
                Text('${(pct * 100).round()}%',
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: Pms.ink, height: 1)),
                Text(tr('إنجاز', 'done'), style: const TextStyle(fontSize: 10, color: Pms.slate)),
              ]),
            ]),
          ),
          const SizedBox(width: 18),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _miniStat(Icons.account_tree_rounded, '${d['projects'] ?? 0}', tr('مشروع', 'projects'), Pms.violet,
                () => _open(const PmsProjectsScreen())),
            const Divider(height: 18),
            _miniStat(Icons.checklist_rounded, '$total', tr('إجمالي المهام', 'total tasks'), const Color(0xFF0891B2),
                () => _open(PmsTasksScreen(filter: '', title: tr('كل المهام', 'All tasks')))),
            const Divider(height: 18),
            _miniStat(Icons.check_circle_rounded, '$done', tr('مهمة منجزة', 'completed'), Pms.green,
                () => _open(PmsTasksScreen(filter: 'done', title: tr('منجزة', 'Done')))),
          ])),
        ]),
      );

  Widget _miniStat(IconData ic, String v, String label, Color c, VoidCallback onTap) => InkWell(
        onTap: onTap,
        child: Row(children: [
          Icon(ic, size: 18, color: c),
          const SizedBox(width: 9),
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: c)),
          const SizedBox(width: 6),
          Expanded(child: Text(label, style: const TextStyle(color: Pms.slate, fontSize: 12, fontWeight: FontWeight.w600))),
          Icon(Icons.chevron_left_rounded, size: 18, color: c.withValues(alpha: 0.4)),
        ]),
      );

  /// A stacked bar showing how the open workload splits — done / overdue /
  /// due-today / the rest — so the balance reads at a glance.
  Widget _distributionBar(Map d, num total) {
    final done = numOf(d['done'], 0).toDouble();
    final overdue = numOf(d['overdue'], 0).toDouble();
    final today = numOf(d['due_today'], 0).toDouble();
    final t = total <= 0 ? 1.0 : total.toDouble();
    final rest = (t - done - overdue - today).clamp(0.0, t);
    int flex(double v) => (v / t * 1000).round().clamp(0, 1000);
    Widget seg(double v, Color c) => v <= 0 ? const SizedBox.shrink()
        : Expanded(flex: flex(v) == 0 ? 1 : flex(v), child: Container(color: c));
    return Column(children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: SizedBox(height: 14, child: Row(children: [
          seg(done, Pms.green), seg(today, Pms.amber),
          seg(overdue, Pms.red), seg(rest, const Color(0xFFCBD5E1)),
        ])),
      ),
      const SizedBox(height: 8),
      Wrap(spacing: 14, runSpacing: 4, children: [
        _legend(Pms.green, tr('منجزة', 'Done')),
        _legend(Pms.amber, tr('اليوم', 'Today')),
        _legend(Pms.red, tr('متأخرة', 'Overdue')),
        _legend(const Color(0xFFCBD5E1), tr('قيد التنفيذ', 'In progress')),
      ]),
    ]);
  }

  Widget _legend(Color c, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 9, height: 9, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 5),
        Text(t, style: const TextStyle(fontSize: 10.5, color: Pms.slate, fontWeight: FontWeight.w700)),
      ]);

  Widget _statTile(IconData ic, dynamic v, String label, Color c, VoidCallback onTap) => Expanded(
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(16),
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.fromLTRB(14, 13, 12, 13),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.black.withValues(alpha: 0.05)),
                gradient: LinearGradient(colors: [c.withValues(alpha: 0.09), Colors.white],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
              ),
              child: Row(children: [
                Container(width: 4, height: 40, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
                const SizedBox(width: 11),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${v ?? 0}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 22, color: c, height: 1)),
                  const SizedBox(height: 3),
                  Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11.5, color: Pms.ink)),
                ])),
                Icon(ic, size: 20, color: c.withValues(alpha: 0.85)),
              ]),
            ),
          ),
        ),
      );

  Widget _action(IconData ic, String label, Color c, VoidCallback onTap) => Expanded(
        child: Material(
          color: c, borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Column(children: [
                Icon(ic, color: Colors.white, size: 22),
                const SizedBox(height: 6),
                Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12)),
              ]),
            ),
          ),
        ),
      );
}
