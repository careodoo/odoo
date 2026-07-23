import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../my/my_screen.dart';
import 'management_list.dart';
import 'management_search.dart';
import 'housing_hub_screen.dart';
import 'management_analytics.dart';

/// Management app shell — Systems and the personal «My» hub, side by side.
class ManagementShell extends StatefulWidget {
  const ManagementShell({super.key});
  @override
  State<ManagementShell> createState() => _ManagementShellState();
}

class _ManagementShellState extends State<ManagementShell> {
  int _tab = 0;
  @override
  Widget build(BuildContext context) {
    final bodies = [const ManagementHome(), const MyScreen(accent: Mgmt.red)];
    final idx = _tab.clamp(0, bodies.length - 1);
    return Scaffold(
      backgroundColor: Mgmt.bg,
      body: IndexedStack(index: idx, children: bodies),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: Colors.white,
          indicatorColor: Mgmt.red.withValues(alpha: 0.14),
          labelTextStyle: WidgetStateProperty.all(
              const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
        ),
        child: NavigationBar(
          height: 62,
          selectedIndex: idx,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: [
            NavigationDestination(
                icon: const Icon(Icons.grid_view_rounded),
                selectedIcon: const Icon(Icons.grid_view_rounded, color: Mgmt.red),
                label: tr('الأنظمة', 'Systems')),
            NavigationDestination(
                icon: const Icon(Icons.account_circle_rounded),
                selectedIcon: const Icon(Icons.account_circle_rounded, color: Mgmt.red),
                label: 'My'),
          ],
        ),
      ),
    );
  }
}

class Mgmt {
  static const red = Color(0xFFC0392B);
  static const deep = Color(0xFF8E2A20);
  static const bg = Color(0xFFF5F6F8);
  static const ink = Color(0xFF1E293B);
  static const slate = Color(0xFF64748B);
}

/// Native management home — the company's back-office systems with live counts.
///
/// This replaces a launcher of /web links (web pages in a WebView): every system
/// here is real data over the API, and the server exposes only what the user's
/// Odoo permissions allow, so this list differs per user.
class ManagementHome extends StatefulWidget {
  const ManagementHome({super.key});
  @override
  State<ManagementHome> createState() => _ManagementHomeState();
}

class _ManagementHomeState extends State<ManagementHome> {
  late Future<List<dynamic>> _f;

  // per-system accent, keyed by the server's `key`
  static const _tint = {
    'purchases': Color(0xFF2563EB), 'sales': Color(0xFF16A34A), 'tenders': Color(0xFF7C3AED),
    'proposals': Color(0xFF0891B2), 'employees': Color(0xFFF59E0B), 'documents': Color(0xFF64748B),
    'experience': Color(0xFFD97706), 'fleet': Color(0xFF0D9488), 'crm': Color(0xFFDB2777),
    'invoices': Color(0xFF4F46E5), 'projects': Color(0xFF15803D),
  };

  Map<String, dynamic>? _me;

  @override
  void initState() {
    super.initState();
    _reload();
    _loadMe();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.managementApps());

  Future<void> _loadMe() async {
    try {
      final me = await context.read<AuthProvider>().api.managementMe();
      if (mounted) setState(() => _me = me);
    } catch (_) {/* header stats are optional */}
  }

  String _fmt(num n) {
    if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(n >= 10000 ? 0 : 1)}k';
    return '$n';
  }

  @override
  Widget build(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    return Scaffold(
      backgroundColor: Mgmt.bg,
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: CustomScrollView(slivers: [
          SliverAppBar(
            pinned: true, expandedHeight: 128, backgroundColor: Mgmt.deep,
            foregroundColor: Colors.white, automaticallyImplyLeading: false,
            actions: [
              IconButton(
                tooltip: tr('لوحة التحليلات', 'Analytics'),
                icon: const Icon(Icons.insights_rounded),
                onPressed: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const ManagementAnalyticsScreen())),
              ),
              IconButton(
                tooltip: tr('بحث شامل', 'Global search'),
                icon: const Icon(Icons.search_rounded),
                onPressed: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const ManagementSearchScreen())),
              ),
              IconButton(
                tooltip: tr('تبديل الوضع', 'Switch mode'),
                icon: const Icon(Icons.swap_horiz_rounded),
                onPressed: () => context.read<AuthProvider>().setAppMode('choose'),
              ),
              IconButton(
                tooltip: tr('تسجيل الخروج', 'Sign out'),
                icon: const Icon(Icons.logout_rounded),
                onPressed: () => context.read<AuthProvider>().logout(),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(fit: StackFit.expand, children: [
                const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [Mgmt.red, Mgmt.deep, Color(0xFF5B1810)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft))),
                SafeArea(child: Padding(
                  padding: const EdgeInsets.fromLTRB(18, 10, 18, 0),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text(tr('الإدارة', 'Management'),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22)),
                    const SizedBox(height: 3),
                    Text(name.isEmpty ? tr('أنظمة الشركة', 'Company systems')
                                      : tr('مرحبًا $name', 'Hi $name'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 12.5)),
                  ]),
                )),
              ]),
            ),
          ),
          if (_me != null) SliverToBoxAdapter(child: _meBand(_me!)),
          FutureBuilder<List<dynamic>>(
            future: _f,
            builder: (_, snap) {
              if (snap.hasError) {
                return SliverFillRemaining(child: _msg(Icons.error_outline_rounded,
                    tr('تعذّر تحميل الأنظمة', 'Could not load systems'), '${snap.error}'));
              }
              if (!snap.hasData) {
                return const SliverFillRemaining(child: Center(child: CircularProgressIndicator()));
              }
              final apps = snap.data!;
              if (apps.isEmpty) {
                return SliverFillRemaining(child: _msg(Icons.lock_outline_rounded,
                    tr('لا أنظمة متاحة لحسابك', 'No systems available'),
                    tr('صلاحياتك في أودو تحدّد ما يظهر هنا', 'Your Odoo permissions decide what appears here')));
              }
              return SliverPadding(
                padding: const EdgeInsets.fromLTRB(12, 14, 12, 24),
                sliver: SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2, childAspectRatio: 1.55, crossAxisSpacing: 10, mainAxisSpacing: 10),
                  delegate: SliverChildBuilderDelegate(
                    (_, i) => _card(apps[i] as Map),
                    childCount: apps.length,
                  ),
                ),
              );
            },
          ),
        ]),
      ),
    );
  }

  Widget _meBand(Map me) {
    final stats = ((me['stats'] as List?) ?? const []).cast<Map>();
    final initial = '${me['name'] ?? '?'}'.trim();
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 14, 12, 0),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 12, offset: const Offset(0, 4))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _avatar(me, initial),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${me['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15.5, color: Mgmt.ink)),
            if (me['job'] != null || me['department'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text([me['job'], me['department']].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Mgmt.slate, fontSize: 12)),
              ),
          ])),
          if (me['is_manager'] == true)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(color: Mgmt.red.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
              child: Text(tr('مدير', 'Manager'),
                  style: const TextStyle(color: Mgmt.red, fontWeight: FontWeight.w800, fontSize: 10.5)),
            ),
        ]),
        if (stats.isNotEmpty) ...[
          const SizedBox(height: 14),
          Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
            for (var i = 0; i < stats.length; i++) ...[
              if (i > 0) Container(width: 1, height: 40, color: Colors.grey.shade200),
              Expanded(child: _statCell(stats[i])),
            ],
          ]),
        ],
      ]),
    );
  }

  Widget _avatar(Map me, String initial) {
    final b64 = '${me['avatar_b64'] ?? ''}';
    Widget fallback() => Container(
        width: 52, height: 52,
        decoration: BoxDecoration(color: Mgmt.red.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(28)),
        alignment: Alignment.center,
        child: Text(initial.isEmpty ? '?' : initial.characters.first,
            style: const TextStyle(color: Mgmt.red, fontWeight: FontWeight.w900, fontSize: 20)));
    return ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: b64.isEmpty
          ? fallback()
          : Image.memory(base64Decode(b64),
              width: 52, height: 52, fit: BoxFit.cover, gaplessPlayback: true,
              errorBuilder: (_, __, ___) => fallback()),
    );
  }

  // Stat cell: value + label. The label wraps to two lines so long Arabic
  // captions ("بانتظار اعتمادك") never spill past the divider.
  Widget _statCell(Map s) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text('${s['value'] ?? 0}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: Mgmt.ink)),
        const SizedBox(height: 3),
        SizedBox(
          height: 26,
          child: Text(gLang == 'en' ? '${s['en'] ?? ''}' : '${s['ar'] ?? ''}',
              maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
              style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700, height: 1.2)),
        ),
      ]);

  Widget _card(Map a) {
    final c = _tint['${a['key']}'] ?? Mgmt.slate;
    final n = numOf(a['count'], 0);
    final pending = numOf(a['pending'], 0).toInt();
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => '${a['key']}' == 'hostels'
                ? HousingHubScreen(accent: c)
                : ManagementListScreen(
                    appKey: '${a['key']}',
                    title: gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                    icon: '${a['icon']}',
                    accent: c))),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 8, offset: const Offset(0, 3))],
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // ---- icon + record count side by side; small red badge in corner
            Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
              Container(
                width: 32, height: 32, alignment: Alignment.center,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
                child: Text('${a['icon']}', style: const TextStyle(fontSize: 15)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(_fmt(n), maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 19, color: c, height: 1)),
              ),
              if (pending > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(color: const Color(0xFFE11D48), borderRadius: BorderRadius.circular(9)),
                  child: Text(pending > 99 ? '99+' : '$pending',
                      style: const TextStyle(color: Colors.white, fontSize: 8.5, fontWeight: FontWeight.w900)),
                ),
            ]),
            const Spacer(),
            // ---- label (wraps to two lines, never spills out)
            Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink, height: 1.15)),
            if (pending > 0)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(tr('بانتظار إجراء', 'Need action'),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Color(0xFFE11D48), fontSize: 9, fontWeight: FontWeight.w700)),
              ),
          ]),
        ),
      ),
    );
  }

  Widget _msg(IconData i, String t, String s) => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(i, size: 46, color: Mgmt.slate),
            const SizedBox(height: 12),
            Text(t, textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: Mgmt.ink)),
            const SizedBox(height: 6),
            Text(s, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate, fontSize: 12)),
          ]),
        ),
      );
}
