import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/auth.dart';
import '../../../core/i18n.dart';
import 'staff_shell.dart';

/// Operations dashboard for managers (team-leader / supervisor / ops-manager) —
/// live KPIs + quick entry into the jobs list. Scoped by the caller's role.
class StaffDashboard extends StatefulWidget {
  const StaffDashboard({super.key, required this.me, required this.onOpenJobs});
  final Map<String, dynamic> me;
  final VoidCallback onOpenJobs;
  @override
  State<StaffDashboard> createState() => _StaffDashboardState();
}

class _StaffDashboardState extends State<StaffDashboard> {
  Future<Map<String, dynamic>>? _kpi;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _kpi = context.read<AuthProvider>().api.c2cStaffOverview());

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        color: Crew.teal,
        onRefresh: () async => _load(),
        child: ListView(padding: const EdgeInsets.all(16), children: [
          // greeting header
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(gradient: const LinearGradient(colors: [Crew.teal, Crew.deep], begin: Alignment.topRight, end: Alignment.bottomLeft), borderRadius: BorderRadius.circular(20), boxShadow: [BoxShadow(color: Crew.teal.withValues(alpha: 0.3), blurRadius: 14, offset: const Offset(0, 6))]),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${widget.me['role_label']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5, fontWeight: FontWeight.w700)),
                const SizedBox(height: 3),
                Text('${widget.me['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
                const SizedBox(height: 3),
                Text(tr('لوحة العمليات المباشرة', 'Live operations board'), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
              ])),
              const Icon(Icons.insights_rounded, color: Colors.white, size: 40),
            ]),
          ),
          const SizedBox(height: 16),
          FutureBuilder<Map<String, dynamic>>(
            future: _kpi,
            builder: (_, snap) {
              if (!snap.hasData) return const Padding(padding: EdgeInsets.only(top: 40), child: Center(child: CircularProgressIndicator(color: Crew.teal)));
              final k = snap.data!;
              final canApprove = (((widget.me['caps'] as Map?)?['can'] as List?) ?? const [])
                  .any((c) => c == 'quality' || c == 'approve');
              final cards = [
                ['📋', '${k['today'] ?? 0}', tr('مهام اليوم', 'Today'), Crew.blue],
                ['🔧', '${k['in_progress'] ?? 0}', tr('قيد التنفيذ', 'Active'), Crew.amber],
                ['⏳', '${k['unassigned'] ?? 0}', tr('غير مُسندة', 'Unassigned'), const Color(0xFFC0392B)],
                // work the crew finished that is waiting on this manager
                if (canApprove)
                  ['🔍', '${k['review'] ?? 0}', tr('بانتظار اعتمادي', 'To approve'), const Color(0xFF7C3AED)],
                ['✅', '${k['done_today'] ?? 0}', tr('أُنجزت اليوم', 'Done today'), Crew.green],
                ['👥', '${k['team_available'] ?? 0}/${k['team_size'] ?? 0}', tr('الفريق المتاح', 'Team free'), Crew.teal],
              ];
              return GridView.count(
                crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.55, crossAxisSpacing: 12, mainAxisSpacing: 12,
                children: [for (final c in cards) _kpiCard(c[0] as String, c[1] as String, c[2] as String, c[3] as Color)],
              );
            },
          ),
          const SizedBox(height: 8),
          _quickTile(Icons.assignment_rounded, tr('عرض كل المهام', 'View all jobs'), tr('افتح قائمة المهام والفلاتر', 'Open the jobs list & filters'), widget.onOpenJobs),
          if (((widget.me['caps'] as Map?)?['can'] as List?)?.contains('unassigned') ?? true)
            _quickTile(Icons.hourglass_bottom_rounded, tr('مهام تحتاج إسناد', 'Needs assignment'), tr('وزّع المهام غير المُسندة على الفريق', 'Assign open jobs to your crew'), widget.onOpenJobs),
        ]),
      ),
    );
  }

  Widget _kpiCard(String ic, String v, String label, Color c) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))], border: Border(left: BorderSide(color: c, width: 4))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Row(children: [Text(ic, style: const TextStyle(fontSize: 20)), const Spacer(), Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 24, color: c))]),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Crew.slate)),
        ]),
      );

  Widget _quickTile(IconData ic, String title, String sub, VoidCallback onTap) => Container(
        margin: const EdgeInsets.only(top: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
        child: ListTile(
          leading: Container(padding: const EdgeInsets.all(9), decoration: BoxDecoration(color: Crew.teal.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)), child: Icon(ic, color: Crew.teal)),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
          subtitle: Text(sub, style: const TextStyle(fontSize: 11.5)),
          trailing: const Icon(Icons.chevron_left, color: Crew.slate),
          onTap: onTap,
        ),
      );
}
