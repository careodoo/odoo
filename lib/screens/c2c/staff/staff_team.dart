import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/auth.dart';
import '../../../core/i18n.dart';
import 'staff_shell.dart';

/// Team roster for leaders/supervisors/ops — each member with role, live
/// availability and current open-job load, so managers see capacity at a glance.
class StaffTeamScreen extends StatefulWidget {
  const StaffTeamScreen({super.key, required this.me});
  final Map<String, dynamic> me;
  @override
  State<StaffTeamScreen> createState() => _StaffTeamScreenState();
}

class _StaffTeamScreenState extends State<StaffTeamScreen> {
  Future<List<dynamic>>? _team;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _team = context.read<AuthProvider>().api.c2cStaffTeam());

  @override
  Widget build(BuildContext context) {
    return SafeArea(child: Column(children: [
      Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: const BoxDecoration(gradient: LinearGradient(colors: [Crew.teal, Crew.deep], begin: Alignment.topRight, end: Alignment.bottomLeft)),
        child: Row(children: [
          const Icon(Icons.groups_rounded, color: Colors.white),
          const SizedBox(width: 8),
          Text(tr('فريقي', 'My team'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
        ]),
      ),
      Expanded(child: RefreshIndicator(
        color: Crew.teal,
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _team,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: Crew.teal));
            final team = snap.data!;
            if (team.isEmpty) {
              return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90), child: Column(children: [
                const Icon(Icons.group_off_outlined, size: 60, color: Crew.slate),
                const SizedBox(height: 10),
                Text(tr('لا يوجد أعضاء في فريقك', 'No team members yet'), style: const TextStyle(color: Crew.slate, fontWeight: FontWeight.w700)),
              ]))]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
              itemCount: team.length,
              itemBuilder: (_, i) => _memberCard(team[i] as Map),
            );
          },
        ),
      )),
    ]));
  }

  Widget _memberCard(Map m) {
    final avail = m['available'] == true;
    final load = m['load'] ?? 0;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 5),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
      child: Row(children: [
        Stack(children: [
          CircleAvatar(radius: 24, backgroundColor: Crew.teal.withValues(alpha: 0.12), backgroundImage: m['image'] != null ? NetworkImage('${m['image']}') : null, child: m['image'] == null ? Text('${m['name']}'.characters.first, style: const TextStyle(color: Crew.teal, fontWeight: FontWeight.w900, fontSize: 18)) : null),
          Positioned(right: 0, bottom: 0, child: Container(width: 13, height: 13, decoration: BoxDecoration(color: avail ? Crew.green : const Color(0xFF9CA3AF), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 2)))),
        ]),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5, color: Crew.ink)),
          const SizedBox(height: 2),
          Row(children: [
            Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2), decoration: BoxDecoration(color: Crew.teal.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20)), child: Text('${m['role_label']}', style: const TextStyle(color: Crew.teal, fontSize: 10.5, fontWeight: FontWeight.w800))),
            const SizedBox(width: 6),
            if ((m['rating'] ?? 0) > 0) Text('⭐ ${m['rating']}', style: const TextStyle(fontSize: 11, color: Crew.slate, fontWeight: FontWeight.w700)),
          ]),
        ])),
        Column(children: [
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6), decoration: BoxDecoration(color: (load > 0 ? Crew.amber : Crew.green).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)), child: Text('$load', style: TextStyle(color: load > 0 ? Crew.amber : Crew.green, fontWeight: FontWeight.w900, fontSize: 16))),
          const SizedBox(height: 2),
          Text(tr('مهام', 'jobs'), style: const TextStyle(fontSize: 9.5, color: Crew.slate)),
        ]),
        if (m['phone'] != null)
          IconButton(icon: const Icon(Icons.phone, color: Crew.teal, size: 20), onPressed: () => _dial('${m['phone']}')),
      ]),
    );
  }

  /// Place a real call to the crew member.
  Future<void> _dial(String phone) async {
    final u = Uri(scheme: 'tel', path: phone.replaceAll(RegExp(r'[\s-]'), ''));
    try {
      await launchUrl(u, mode: LaunchMode.externalApplication);
    } catch (_) {}
  }
}
