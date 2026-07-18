import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'create_task_screen.dart';
import 'workorders_screen.dart';
import 'quality_screen.dart';
import 'schedules_screen.dart';
import 'attendance_screen.dart';
import 'client_analytics_screen.dart';
import 'notify_send_screen.dart';
import 'notifications_screen.dart';
import 'chat_screen.dart';
import 'my_profile_screen.dart';
import 'client_team_screen.dart';
import 'requests_screen.dart';
import 'maintenance_screen.dart';
import 'scan_screen.dart';

const _navy = Color(0xFF0E3A5F);
const _teal = Color(0xFF0D9488);

/// The supervisor's cockpit AS the home screen: a statistics header, a wide grid
/// of executive options, and the board itself (unassigned backlog with one-tap
/// assignment + live team load) right on the first screen.
class SupervisorHome extends StatefulWidget {
  const SupervisorHome({super.key});
  @override
  State<SupervisorHome> createState() => _SupervisorHomeState();
}

class _SupervisorHomeState extends State<SupervisorHome> {
  Future<_SupData>? _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _period = 'month';

  void _load() {
    final api = context.read<AuthProvider>().api;
    setState(() {
      _future = Future.wait([
        api.stats(), api.assignable(), api.team(), api.employees(),
        api.meSupervisor(period: _period),
      ]).then((r) => _SupData(r[0] as Map<String, dynamic>, r[1] as List, r[2] as List, r[3] as List,
          r[4] as Map<String, dynamic>));
    });
  }

  Future<void> _assign(int woId, List employees) async {
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  const Icon(Icons.person_add_alt_rounded, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(child: Text(tr('إسناد المهمة إلى', 'Assign task to'), style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                ]),
              ])),
            Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(10), children: [
              for (final e in employees) Card(
                margin: const EdgeInsets.symmetric(vertical: 4),
                child: ListTile(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  leading: CircleAvatar(backgroundColor: _navy, child: Text('${e['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
                  title: Text('${e['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text('${e['job_title'] ?? '—'}'),
                  trailing: const Icon(Icons.check_circle_outline_rounded, color: _teal),
                  onTap: () => Navigator.pop(context, e['id'] as int),
                ),
              ),
            ])),
          ]),
        ),
      ),
    );
    if (chosen == null) return;
    try {
      await context.read<AuthProvider>().api.assign(woId, chosen);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✔ تم إسناد المهمة', '✔ Task assigned')), backgroundColor: const Color(0xFF16A34A)));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    void go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

    final options = <(IconData, String, String, Color, VoidCallback)>[
      (Icons.add_task_rounded, 'مهمة جديدة', 'New task', _teal, () async {
        final c = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const CreateTaskScreen()));
        if (c == true) _load();
      }),
      (Icons.assignment_rounded, 'أوامر العمل', 'Work orders', _navy, () => go(const WorkOrdersScreen())),
      (Icons.groups_rounded, 'الفريق', 'Team', const Color(0xFF6366F1), () => go(const ClientTeamScreen())),
      (Icons.fact_check_rounded, 'الجودة', 'Quality', const Color(0xFF0EA5A4), () => go(const QualityScreen())),
      (Icons.event_repeat_rounded, 'الجدولة', 'Schedules', const Color(0xFF0D9488), () => go(const SchedulesScreen())),
      (Icons.inbox_rounded, 'طلبات الخدمة', 'Requests', const Color(0xFFE6295C), () => go(const RequestsScreen())),
      (Icons.handyman_rounded, 'الصيانة', 'Maintenance', const Color(0xFFF7A23B), () => go(const MaintenanceScreen())),
      (Icons.fingerprint_rounded, 'الحضور', 'Attendance', const Color(0xFF7C3AED), () => go(const AttendanceScreen())),
      (Icons.insights_rounded, 'التحليلات', 'Analytics', const Color(0xFF2563EB), () => go(const ClientAnalyticsScreen())),
      (Icons.campaign_rounded, 'إشعار للفريق', 'Notify team', const Color(0xFFEA580C), () => go(const NotifySendScreen())),
      (Icons.forum_rounded, 'التواصل', 'Messages', const Color(0xFF0E7490), () => go(const ChatHubScreen())),
      (Icons.qr_code_scanner_rounded, 'مسح موقع', 'Scan', const Color(0xFF0891B2), () => go(const ScanScreen())),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: RefreshIndicator(
        color: _teal,
        onRefresh: () async => _load(),
        child: FutureBuilder<_SupData>(
          future: _future,
          builder: (_, snap) {
            final d = snap.data;
            final s = d?.stats ?? const {};
            return ListView(padding: EdgeInsets.zero, children: [
              _header(context, p, s, d),
              // ===== executive options =====
              Padding(padding: const EdgeInsets.fromLTRB(12, 14, 12, 4), child: Row(children: [
                const Icon(Icons.grid_view_rounded, size: 17, color: _navy), const SizedBox(width: 7),
                Text(tr('الإجراءات التنفيذية', 'Executive actions'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
              ])),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: GridView.count(
                  crossAxisCount: 4, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 9, crossAxisSpacing: 9, childAspectRatio: 0.85,
                  children: [for (final o in options) _opt(o.$1, o.$2, o.$3, o.$4, o.$5)],
                ),
              ),
              if (snap.connectionState == ConnectionState.waiting)
                const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: _teal)))
              else if (d != null) ...[
                // ===== the board, right on the home screen =====
                _sectionTitle(Icons.pending_actions_rounded, tr('بانتظار الإسناد', 'Awaiting assignment'), d.assignable.length),
                if (d.assignable.isEmpty)
                  _empty(tr('لا مهام بانتظار الإسناد ✓', 'Nothing awaiting assignment ✓'))
                else
                  for (final w in d.assignable) _assignCard(w as Map, d.employees),
                // ===== quality queue — distribute to the crew =====
                _sectionTitle(Icons.fact_check_rounded, tr('ملاحظات الجودة — للتوزيع', 'Quality — to distribute'), d.quality.length),
                if (d.quality.isEmpty) _empty(tr('لا ملاحظات جودة مفتوحة ✓', 'No open quality notes ✓'))
                else for (final q in d.quality.take(8)) _qualityCard(q as Map, d.employees),
                // ===== crew: live load + achievements per member =====
                _sectionTitle(Icons.groups_rounded, tr('فريقي — الأداء والأحمال', 'My crew — load & performance'), d.crew.length),
                if (d.crew.isEmpty) _empty(tr('لا أعضاء فريق', 'No team members'))
                else for (final m in d.crew) _crewCard(m as Map),
              ],
              const SizedBox(height: 26),
            ]);
          },
        ),
      ),
    );
  }

  Widget _header(BuildContext context, dynamic p, Map s, _SupData? d) => CustomPaint(
        painter: const BrandPattern(opacity: 0.07),
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 0, 10, 18),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [_teal, Color(0xFF0F766E), _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
          ),
          child: SafeArea(bottom: false, child: Column(children: [
            Row(children: [
              const Text('🧭', style: TextStyle(fontSize: 20)),
              const SizedBox(width: 8),
              Expanded(child: Text(tr('لوحة المشرف', 'Supervisor board'), style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
              IconButton(icon: const Icon(Icons.notifications_rounded, color: Colors.white),
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()))),
              IconButton(icon: const Icon(Icons.workspace_premium_rounded, color: Colors.white),
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MyProfileScreen()))),
              IconButton(icon: const Icon(Icons.logout_rounded, color: Colors.white),
                  onPressed: () => context.read<AuthProvider>().logout()),
            ]),
            Row(children: [
              Container(
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
                child: CircleAvatar(radius: 26, backgroundColor: Colors.white,
                    child: Text(p.name.isNotEmpty ? p.name.trim().characters.first : '?', style: const TextStyle(color: _teal, fontSize: 22, fontWeight: FontWeight.w900))),
              ),
              const SizedBox(width: 13),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                const SizedBox(height: 3),
                Text(tr('مشرف تنفيذي · متابعة الأعمال', 'Executive supervisor · operations'), style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
              ])),
            ]),
            // ===== what exactly this person supervises =====
            if (d != null && d.teams.isNotEmpty) ...[
              const SizedBox(height: 12),
              for (final t in d.teams) Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.white.withValues(alpha: 0.18))),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    const Icon(Icons.groups_rounded, color: Colors.white, size: 15),
                    const SizedBox(width: 6),
                    Expanded(child: Text('${(t as Map)['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13))),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                        child: Text('${t['members'] ?? 0} ${tr('عضو', 'members')}', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800))),
                  ]),
                  const SizedBox(height: 7),
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    if (t['service'] != null) _ctx(Icons.design_services_rounded, '${t['service']}'),
                    if (t['facility'] != null) _ctx(Icons.apartment_rounded, '${t['facility']}'),
                    if (t['client'] != null) _ctx(Icons.badge_rounded, '${t['client']}'),
                    if (t['project'] != null) _ctx(Icons.account_tree_rounded, '${t['project']}'),
                  ]),
                ]),
              ),
            ],
            const SizedBox(height: 8),
            // ===== period filter for the achievement figures =====
            SizedBox(height: 34, child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final pr in const [('today', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'), ('month', 'الشهر', 'Month'), ('all', 'الكل', 'All')])
                Padding(padding: const EdgeInsets.only(left: 6),
                  child: GestureDetector(
                    onTap: () { setState(() => _period = pr.$1); _load(); },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                      decoration: BoxDecoration(
                        color: _period == pr.$1 ? Colors.white : Colors.white.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(20)),
                      child: Text(tr(pr.$2, pr.$3), style: TextStyle(color: _period == pr.$1 ? _teal : Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900)),
                    ),
                  )),
            ])),
            const SizedBox(height: 12),
            // live statistics strip
            Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
              ),
              child: Row(children: [
                _hs(Icons.inbox_rounded, '${s['open'] ?? 0}', tr('مفتوحة', 'Open')),
                _hd(),
                _hs(Icons.person_off_rounded, '${s['unassigned'] ?? 0}', tr('غير مُسندة', 'Unassigned')),
                _hd(),
                _hs(Icons.warning_amber_rounded, '${s['overdue'] ?? 0}', tr('متأخرة', 'Overdue')),
                _hd(),
                _hs(Icons.check_circle_rounded, '${s['done'] ?? 0}', tr('منجزة', 'Done')),
              ]),
            ),
          ])),
        ),
      );

  Widget _hs(IconData ic, String v, String l) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 17),
        const SizedBox(height: 3),
        Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 32, color: Colors.white.withValues(alpha: 0.18));

  /// a small "what I supervise" chip (service / facility / client / project)
  Widget _ctx(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, color: Colors.white, size: 12), const SizedBox(width: 5),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w800)),
        ]),
      );

  Widget _opt(IconData ic, String ar, String en, Color c, VoidCallback onTap) => Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14), onTap: onTap,
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(width: 36, height: 36, alignment: Alignment.center,
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                  child: Icon(ic, color: c, size: 19)),
              const SizedBox(height: 6),
              Text(tr(ar, en), textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 10, color: _navy)),
            ]),
          ),
        ),
      );

  Widget _sectionTitle(IconData ic, String t, int n) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 18, 14, 8),
        child: Row(children: [
          Icon(ic, size: 17, color: _navy), const SizedBox(width: 7),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
          const SizedBox(width: 8),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _teal.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
              child: Text('$n', style: const TextStyle(color: _teal, fontWeight: FontWeight.w900, fontSize: 11.5))),
        ]),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Container(
          width: double.infinity, padding: const EdgeInsets.all(18), alignment: Alignment.center,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
          child: Text(t, style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ),
      );

  Widget _assignCard(Map w, List employees) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(width: 5, height: 44, decoration: BoxDecoration(color: const Color(0xFFF7A23B), borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${w['title']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
                const SizedBox(height: 3),
                Text('${w['service_type'] ?? ''} · ${w['facility'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
              ])),
              const SizedBox(width: 8),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _teal, padding: const EdgeInsets.symmetric(horizontal: 12), minimumSize: const Size(0, 40)),
                onPressed: () => _assign(w['id'] as int, employees),
                icon: const Icon(Icons.person_add_rounded, size: 17),
                label: Text(tr('إسناد', 'Assign'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
              ),
            ]),
          ),
        ),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.35))),
        child: Text(t, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w900)),
      );

  // ===== a crew member: live load + achievements, tap for actions ===========
  Widget _crewCard(Map m) {
    final rate = ((m['on_time_rate'] as num?) ?? 0).toDouble();
    final overdue = ((m['overdue'] as num?) ?? 0).toInt();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _crewSheet(m),
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.all(11),
            child: Column(children: [
              Row(children: [
                CircleAvatar(radius: 20, backgroundColor: overdue > 0 ? const Color(0xFFE11D48) : _navy,
                    child: Text('${m['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
                const SizedBox(width: 11),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${m['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
                  Text('${m['job'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                ])),
                Wrap(spacing: 5, children: [
                  _pill('${tr('مفتوحة', 'open')} ${m['open'] ?? 0}', const Color(0xFF2F6DF6)),
                  if (overdue > 0) _pill('${tr('متأخرة', 'late')} $overdue', const Color(0xFFE11D48)),
                ]),
              ]),
              const SizedBox(height: 9),
              Row(children: [
                Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(value: rate / 100.0, minHeight: 6, backgroundColor: Colors.grey.shade200,
                        valueColor: AlwaysStoppedAnimation(rate >= 90 ? const Color(0xFF16A34A) : (rate >= 70 ? const Color(0xFFF59E0B) : const Color(0xFFE11D48)))))),
                const SizedBox(width: 8),
                Text('${rate.toStringAsFixed(0)}% ${tr('التزام', 'on-time')}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: _navy)),
                const SizedBox(width: 10),
                Text('${m['done'] ?? 0} ${tr('منجزة', 'done')} · ${m['hours'] ?? 0}${tr('س', 'h')}', style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
              ]),
            ]),
          ),
        ),
      ),
    );
  }

  void _crewSheet(Map m) => showModalBottomSheet(context: context, backgroundColor: Colors.transparent,
      builder: (_) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: SafeArea(top: false, child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
            decoration: const BoxDecoration(gradient: LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Column(children: [
              Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
              Row(children: [
                CircleAvatar(backgroundColor: Colors.white24, child: Text('${m['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${m['name']}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                  Text('${m['job'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                ])),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                _hs(Icons.inbox_rounded, '${m['open'] ?? 0}', tr('مفتوحة', 'Open')),
                _hd(),
                _hs(Icons.check_circle_rounded, '${m['done'] ?? 0}', tr('منجزة', 'Done')),
                _hd(),
                _hs(Icons.warning_amber_rounded, '${m['overdue'] ?? 0}', tr('متأخرة', 'Overdue')),
                _hd(),
                _hs(Icons.schedule_rounded, '${m['hours'] ?? 0}', tr('ساعات', 'Hours')),
              ]),
            ])),
          ListTile(leading: const Icon(Icons.assignment_rounded, color: _navy),
              title: Text(tr('عرض مهام هذا العضو', 'View their tasks')),
              onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const WorkOrdersScreen())); }),
          if (m['user_id'] != null)
            ListTile(leading: const Icon(Icons.forum_rounded, color: Color(0xFF0E7490)),
                title: Text(tr('مراسلة', 'Message')),
                onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(
                    builder: (_) => ChatScreen(peerUid: (m['user_id'] as num).toInt(), peerName: '${m['name']}'))); }),
          ListTile(leading: const Icon(Icons.fingerprint_rounded, color: Color(0xFF7C3AED)),
              title: Text(tr('سجل الحضور', 'Attendance record')),
              onTap: () { Navigator.pop(context); Navigator.push(context, MaterialPageRoute(builder: (_) => const AttendanceScreen())); }),
          const SizedBox(height: 8),
        ])),
      ));

  // ===== a quality observation the supervisor can hand to a crew member =====
  Widget _qualityCard(Map q, List employees) {
    const sevColors = {'low': Color(0xFF94A3B8), 'medium': Color(0xFF3B82F6), 'high': Color(0xFFF59E0B), 'critical': Color(0xFFE11D48)};
    final c = sevColors['${q['severity']}'] ?? const Color(0xFF3B82F6);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: Container(
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
          padding: const EdgeInsets.all(11),
          child: Row(children: [
            Container(width: 5, height: 46, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${q['title'] ?? q['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
              const SizedBox(height: 3),
              Text([q['facility'], q['location'], q['severity_label']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              if (q['assignee'] != null) Padding(padding: const EdgeInsets.only(top: 3),
                  child: Text('${tr('مُسندة إلى', 'assigned to')}: ${q['assignee']}', style: const TextStyle(fontSize: 10.5, color: Color(0xFF16A34A), fontWeight: FontWeight.w800))),
            ])),
            const SizedBox(width: 6),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: _teal, side: const BorderSide(color: _teal), padding: const EdgeInsets.symmetric(horizontal: 10), minimumSize: const Size(0, 38)),
              onPressed: () => _distribute(q, employees),
              icon: const Icon(Icons.person_add_alt_rounded, size: 16),
              label: Text(tr('توزيع', 'Assign'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5)),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _distribute(Map q, List employees) async {
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Text(tr('توزيع الملاحظة على', 'Distribute note to'), style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
              ])),
            Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(10), children: [
              for (final e in employees) Card(
                margin: const EdgeInsets.symmetric(vertical: 4),
                child: ListTile(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  leading: CircleAvatar(backgroundColor: _navy, child: Text('${e['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
                  title: Text('${e['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text('${e['job_title'] ?? '—'}'),
                  onTap: () => Navigator.pop(context, e['id'] as int),
                ),
              ),
            ])),
          ]),
        ),
      ),
    );
    if (chosen == null) return;
    try {
      await context.read<AuthProvider>().api.observationAssign((q['id'] as num).toInt(), chosen);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✔ وُزّعت الملاحظة', '✔ Note distributed')), backgroundColor: const Color(0xFF16A34A)));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

class _SupData {
  _SupData(this.stats, this.assignable, this.team, this.employees, this.scope);
  final Map<String, dynamic> stats;
  final List assignable;
  final List team;
  final List employees;
  /// /me/supervisor — supervised teams, per-member achievements, quality queue.
  final Map<String, dynamic> scope;

  List get teams => (scope['teams'] as List?) ?? const [];
  List get crew => (scope['team'] as List?) ?? const [];
  List get quality => (scope['quality'] as List?) ?? const [];
  Map get aggregate => (scope['aggregate'] as Map?) ?? const {};
}
