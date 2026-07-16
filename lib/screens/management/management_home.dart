import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_list.dart';

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

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.managementApps());

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
                      crossAxisCount: 2, childAspectRatio: 1.42, crossAxisSpacing: 10, mainAxisSpacing: 10),
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

  Widget _card(Map a) {
    final c = _tint['${a['key']}'] ?? Mgmt.slate;
    final n = (a['count'] as num?) ?? 0;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => ManagementListScreen(
                appKey: '${a['key']}',
                title: gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                icon: '${a['icon']}',
                accent: c))),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(padding: const EdgeInsets.all(9),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                  child: Text('${a['icon']}', style: const TextStyle(fontSize: 20))),
              const Spacer(),
              Icon(Icons.chevron_left_rounded, color: c.withValues(alpha: 0.5)),
            ]),
            const Spacer(),
            Text(_fmt(n), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 24, color: c, height: 1)),
            const SizedBox(height: 2),
            Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
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
