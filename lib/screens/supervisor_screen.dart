import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Supervisor cockpit: live KPIs, team load, and the assignable backlog with
/// one-tap assignment to any team member.
class SupervisorScreen extends StatefulWidget {
  const SupervisorScreen({super.key});
  @override
  State<SupervisorScreen> createState() => _SupervisorScreenState();
}

class _SupervisorScreenState extends State<SupervisorScreen> {
  late Future<_Data> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<AuthProvider>().api;
    _future = Future.wait([api.stats(), api.assignable(), api.team(), api.employees()])
        .then((r) => _Data(r[0] as Map<String, dynamic>, r[1] as List, r[2] as List, r[3] as List));
  }

  Future<void> _assign(int woId) async {
    final api = context.read<AuthProvider>().api;
    final emps = (await _future).employees;
    if (!mounted) return;
    final chosen = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: const Color(0xFF152238),
      isScrollControlled: true,
      builder: (_) => ListView(
        shrinkWrap: true,
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('اختر الموظف', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800)),
          ),
          for (final e in emps)
            ListTile(
              leading: const Icon(Icons.person, color: Color(0xFF9CB2CD)),
              title: Text('${e['name']}', style: const TextStyle(color: Colors.white)),
              subtitle: e['job_title'] != null
                  ? Text('${e['job_title']}', style: const TextStyle(color: Color(0xFF9CB2CD)))
                  : null,
              onTap: () => Navigator.pop(context, e['id'] as int),
            ),
        ],
      ),
    );
    if (chosen == null) return;
    try {
      await api.assign(woId, chosen);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('✔ تم إسناد المهمة')));
        setState(_load);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(title: const Text('🧭 لوحة المشرف')),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<_Data>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [const SizedBox(height: 120), Center(child: Text('خطأ: ${snap.error}', style: const TextStyle(color: Color(0xFF9CB2CD))))]);
            }
            final d = snap.data!;
            final s = d.stats;
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(children: [
                  Expanded(child: StatCard(label: tr('مفتوحة', 'Open'), value: s['open'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.inbox)),
                  const SizedBox(width: 8),
                  Expanded(child: StatCard(label: tr('غير مُسندة', 'Unassigned'), value: s['unassigned'] ?? 0, color: const Color(0xFFF7A23B), icon: Icons.person_off)),
                  const SizedBox(width: 8),
                  Expanded(child: StatCard(label: tr('متأخرة', 'Overdue'), value: s['overdue'] ?? 0, color: const Color(0xFFE5484D), icon: Icons.warning_amber)),
                ]),
                const SizedBox(height: 20),
                Text(tr('المهام غير المُسندة / الجديدة', 'Unassigned / new tasks'), style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                if (d.assignable.isEmpty)
                  const Padding(padding: EdgeInsets.all(16), child: Text('لا مهام بانتظار الإسناد ✓', style: TextStyle(color: Color(0xFF9CB2CD)))),
                for (final w in d.assignable) _assignCard(w as Map),
                const SizedBox(height: 20),
                Text(tr('أحمال الفريق', 'Team load'), style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                for (final m in d.team) _teamCard(m as Map),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _assignCard(Map w) => Card(
        color: const Color(0xFF152238),
        child: ListTile(
          title: Text('${w['title']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
          subtitle: Text('${w['service_type']} · ${w['facility']}', style: const TextStyle(color: Color(0xFF9CB2CD))),
          trailing: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF2F6DF6)),
            onPressed: () => _assign(w['id'] as int),
            icon: const Icon(Icons.person_add, size: 18),
            label: Text(tr('إسناد', 'Assign')),
          ),
        ),
      );

  Widget _teamCard(Map m) => Card(
        color: const Color(0xFF152238),
        child: ListTile(
          leading: CircleAvatar(backgroundColor: const Color(0xFF1E3A5F), child: Text('${m['name']}'.characters.first, style: const TextStyle(color: Colors.white))),
          title: Text('${m['name']}', style: const TextStyle(color: Colors.white)),
          subtitle: Text('${m['job_title'] ?? '—'}', style: const TextStyle(color: Color(0xFF9CB2CD))),
          trailing: Wrap(spacing: 6, children: [
            _pill('مفتوحة ${m['open']}', const Color(0xFF2F6DF6)),
            if ((m['overdue'] ?? 0) > 0) _pill('متأخرة ${m['overdue']}', const Color(0xFFE5484D)),
          ]),
        ),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

class _Data {
  _Data(this.stats, this.assignable, this.team, this.employees);
  final Map<String, dynamic> stats;
  final List assignable;
  final List team;
  final List employees;
}
