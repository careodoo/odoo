import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'employee_profile_screen.dart';
import 'add_worker_screen.dart';
import 'client_team_roster.dart';

const Map<String, Color> kStatusColor = {
  'on_task': Color(0xFF16A34A),
  'available': Color(0xFF2F6DF6),
  'recent': Color(0xFFF59E0B),
  'off': Color(0xFF94A3B8),
};
String statusLabel(String s) => {
      'on_task': tr('ينفّذ مهمة', 'On task'),
      'available': tr('متاح', 'Available'),
      'recent': tr('نشاط حديث', 'Recent'),
      'off': tr('خارج الوردية', 'Off'),
    }[s] ??
    s;

/// The client's workforce, organised the way it is actually run: a block per
/// service, the teams inside it, the people inside those. Every level carries
/// its own numbers, so a manager can stop at whichever level they care about.
class ClientTeamScreen extends StatefulWidget {
  const ClientTeamScreen({super.key});
  @override
  State<ClientTeamScreen> createState() => _ClientTeamScreenState();
}

class _ClientTeamScreenState extends State<ClientTeamScreen> {
  Future<Map<String, dynamic>>? _future;
  static const _navy = Color(0xFF0E3A5F);

  static const _svcColor = {
    'security': Color(0xFFE5484D),
    'cleaning': Color(0xFF0EA5E9),
    'agriculture': Color(0xFF16A34A),
    'facade': Color(0xFF7C3AED),
    'maintenance': Color(0xFFF59E0B),
  };
  static const _svcIcon = {
    'security': Icons.shield_rounded,
    'cleaning': Icons.cleaning_services_rounded,
    'agriculture': Icons.park_rounded,
    'facade': Icons.location_city_rounded,
    'maintenance': Icons.build_rounded,
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientTeams();

  Color _color(String? t) => _svcColor[t] ?? const Color(0xFF64748B);
  IconData _icon(String? t) => _svcIcon[t] ?? Icons.groups_rounded;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final p = context.watch<AuthProvider>().profile;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الفريق', 'Team')),
        actions: [
          IconButton(
            tooltip: tr('كل العاملين', 'All workers'),
            icon: const Icon(Icons.list_alt_rounded),
            onPressed: () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => const ClientTeamRosterScreen())),
          ),
        ],
      ),
      // Adding a worker belongs with the team, not on the portal's front page.
      floatingActionButton: (p?.canAddWorkers ?? false)
          ? FloatingActionButton.extended(
              backgroundColor: const Color(0xFF16A34A),
              foregroundColor: Colors.white,
              icon: const Icon(Icons.person_add_alt_1_rounded),
              label: Text(tr('إضافة عامل', 'Add worker'),
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              onPressed: () async {
                await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddWorkerScreen()));
                if (mounted) setState(_load);
              },
            )
          : null,
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [
                const SizedBox(height: 120),
                Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline))),
              ]);
            }
            final d = snap.data ?? const {};
            final groups = (d['groups'] as List?) ?? const [];
            final totals = (d['totals'] as Map?) ?? const {};
            if (groups.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 140),
                Center(child: Text(tr('لا فِرَق بعد.', 'No teams yet.'), style: TextStyle(color: cs.outline))),
              ]);
            }
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 90), children: [
              _totals(totals),
              const SizedBox(height: 14),
              for (final g in groups) _serviceBlock(g as Map),
            ]);
          },
        ),
      ),
    );
  }

  Widget _totals(Map t) {
    final rate = (t['present_rate'] ?? 0) is num ? (t['present_rate'] as num).toDouble() : 0.0;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF17547F), _navy],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: _navy.withValues(alpha: 0.25), blurRadius: 12, offset: const Offset(0, 5))],
      ),
      child: Column(children: [
        Row(children: [
          _t('${t['members'] ?? 0}', tr('عامل', 'Workers')),
          _sep(),
          _t('${t['teams'] ?? 0}', tr('فريق', 'Teams')),
          _sep(),
          _t('${t['services'] ?? 0}', tr('خدمة', 'Services')),
          _sep(),
          _t('${t['present_now'] ?? 0}', tr('بالموقع الآن', 'On site')),
        ]),
        const SizedBox(height: 11),
        Row(children: [
          Expanded(child: ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: LinearProgressIndicator(
              value: (rate / 100).clamp(0.0, 1.0), minHeight: 7,
              backgroundColor: Colors.white.withValues(alpha: 0.18),
              valueColor: const AlwaysStoppedAnimation(Color(0xFF4ADE80)),
            ),
          )),
          const SizedBox(width: 9),
          Text(tr('حضور ${rate.round()}%', '${rate.round()}% present'),
              style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w900)),
        ]),
        const SizedBox(height: 9),
        Row(children: [
          _chip(Icons.schedule_rounded,
              tr('${t['hours_month'] ?? 0} ساعة هذا الشهر', '${t['hours_month'] ?? 0}h this month')),
          const SizedBox(width: 7),
          _chip(Icons.build_rounded,
              tr('${t['open_workorders'] ?? 0} أمر مفتوح', '${t['open_workorders'] ?? 0} open')),
          if (((t['overdue'] ?? 0) as int) > 0) ...[
            const SizedBox(width: 7),
            _chip(Icons.warning_amber_rounded, '${t['overdue']}', danger: true),
          ],
        ]),
      ]),
    );
  }

  Widget _t(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 9, fontWeight: FontWeight.w700)),
      ]));

  Widget _sep() => Container(width: 1, height: 26, color: Colors.white.withValues(alpha: 0.15));

  Widget _chip(IconData ic, String t, {bool danger = false}) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
            color: (danger ? const Color(0xFFE5484D) : Colors.white).withValues(alpha: danger ? 0.85 : 0.13),
            borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 11, color: Colors.white),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)),
        ]),
      );

  /// One service = one block. Collapsed it reads as a summary; opened it lists
  /// the teams that make up the number.
  Widget _serviceBlock(Map g) {
    final c = _color(g['service_type'] as String?);
    final teams = (g['teams'] as List?) ?? const [];
    final rate = (g['present_rate'] ?? 0) is num ? (g['present_rate'] as num).toDouble() : 0.0;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: c.withValues(alpha: 0.25)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: teams.length <= 2,
          tilePadding: const EdgeInsets.symmetric(horizontal: 13, vertical: 4),
          childrenPadding: const EdgeInsets.fromLTRB(11, 0, 11, 11),
          leading: Container(
            width: 42, height: 42, alignment: Alignment.center,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.25)!]),
              borderRadius: BorderRadius.circular(13),
            ),
            child: Icon(_icon(g['service_type'] as String?), color: Colors.white, size: 21),
          ),
          title: Text('${g['service']}',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c)),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text(
                tr('${teams.length} فريق · ${g['members']} عامل · ${g['present_now']} بالموقع',
                   '${teams.length} teams · ${g['members']} workers · ${g['present_now']} on site'),
                style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
          ),
          trailing: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text('${rate.round()}%',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: c)),
            Text(tr('حضور', 'present'),
                style: TextStyle(fontSize: 8, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
          ]),
          children: [
            Row(children: [
              _mini(tr('ساعات الشهر', 'Hours (mo.)'), '${g['hours_month']}', Icons.schedule_rounded, c),
              const SizedBox(width: 7),
              _mini(tr('أوامر مفتوحة', 'Open'), '${g['open_workorders']}', Icons.build_rounded, const Color(0xFFF7A23B)),
              const SizedBox(width: 7),
              _mini(tr('متأخرة', 'Overdue'), '${g['overdue']}', Icons.warning_amber_rounded, const Color(0xFFE5484D)),
            ]),
            const SizedBox(height: 10),
            for (final t in teams) _teamCard(t as Map, c),
          ],
        ),
      ),
    );
  }

  Widget _mini(String l, String v, IconData ic, Color c) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 5),
          decoration: BoxDecoration(
              color: c.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10),
              border: Border.all(color: c.withValues(alpha: 0.18))),
          child: Column(children: [
            Icon(ic, size: 12, color: c),
            const SizedBox(height: 2),
            Text(v, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: c)),
            Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
          ]),
        ),
      );

  Widget _teamCard(Map t, Color c) {
    final members = (t['member_list'] as List?) ?? const [];
    final rate = (t['present_rate'] ?? 0) is num ? (t['present_rate'] as num).toDouble() : 0.0;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.withValues(alpha: 0.14)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 11),
          childrenPadding: const EdgeInsets.fromLTRB(9, 0, 9, 9),
          title: Text('${t['name']}',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Wrap(spacing: 6, runSpacing: 3, children: [
              if (t['supervisor'] != null) _tag(Icons.badge_outlined, '${t['supervisor']}', c),
              if (t['facility'] != null) _tag(Icons.apartment_rounded, '${t['facility']}', c),
              _tag(Icons.group_rounded, tr('${t['members']} عضو', '${t['members']} members'), c),
              if (((t['reserves'] ?? 0) as int) > 0)
                _tag(Icons.backup_outlined, tr('${t['reserves']} احتياطي', '${t['reserves']} reserve'), c),
            ]),
          ),
          trailing: SizedBox(
            width: 38,
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('${t['present_now']}/${t['members']}',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900,
                      color: rate >= 80
                          ? const Color(0xFF16A34A)
                          : (rate > 0 ? const Color(0xFFF7A23B) : Colors.grey))),
              Text(tr('حضور', 'here'),
                  style: TextStyle(fontSize: 7.5, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
            ]),
          ),
          children: [
            Row(children: [
              _mini(tr('ساعات', 'Hours'), '${t['hours_month']}', Icons.schedule_rounded, const Color(0xFF0891B2)),
              const SizedBox(width: 6),
              _mini(tr('ينفّذ الآن', 'On task'), '${t['on_task']}', Icons.play_circle_rounded, const Color(0xFF16A34A)),
              const SizedBox(width: 6),
              _mini(tr('مفتوحة', 'Open'), '${t['open_workorders']}', Icons.build_rounded, const Color(0xFFF7A23B)),
              const SizedBox(width: 6),
              _mini(tr('متأخرة', 'Overdue'), '${t['overdue']}', Icons.warning_amber_rounded, const Color(0xFFE5484D)),
            ]),
            const SizedBox(height: 9),
            if (members.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(tr('لا أعضاء مسجّلين في هذا الفريق.', 'No members registered on this team.'),
                    style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500)),
              )
            else
              for (final m in members) _memberRow(m as Map),
          ],
        ),
      ),
    );
  }

  Widget _tag(IconData ic, String t, Color c) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 10, color: c.withValues(alpha: 0.7)),
        const SizedBox(width: 3),
        Text(t, style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: Colors.grey.shade600)),
      ]);

  Widget _memberRow(Map m) {
    final status = '${m['status']}';
    final c = kStatusColor[status] ?? Colors.grey;
    return InkWell(
      borderRadius: BorderRadius.circular(11),
      onTap: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => EmployeeProfileScreen(employeeId: m['id'] as int, name: '${m['name']}'))),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 3),
        child: Row(children: [
          Stack(children: [
            CircleAvatar(
              radius: 17,
              backgroundColor: c.withValues(alpha: 0.15),
              backgroundImage: m['photo'] != null ? NetworkImage('${m['photo']}') : null,
              child: m['photo'] == null
                  ? Text('${m['name']}'.characters.first,
                      style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 13))
                  : null,
            ),
            Positioned(bottom: 0, left: 0, child: Container(
              width: 10, height: 10,
              decoration: BoxDecoration(
                  color: c, shape: BoxShape.circle,
                  border: Border.all(color: Theme.of(context).cardColor, width: 1.5)),
            )),
          ]),
          const SizedBox(width: 9),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${m['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
            Text(m['job'] != null ? '${m['job']} · ${statusLabel(status)}' : statusLabel(status),
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
          ])),
          if (((m['hours_month'] ?? 0) as num) > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                  color: const Color(0xFF0891B2).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6)),
              child: Text(tr('${m['hours_month']} س', '${m['hours_month']}h'),
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: Color(0xFF0891B2))),
            ),
          const SizedBox(width: 4),
          Icon(Icons.chevron_left_rounded, size: 17, color: Colors.grey.shade400),
        ]),
      ),
    );
  }
}
