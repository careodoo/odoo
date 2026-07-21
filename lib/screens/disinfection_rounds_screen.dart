import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Assign disinfection rounds to a worker and/or team, with a planned time —
/// the supervisor-facing side of care.disinfect.round.
class DisinfectionRoundsScreen extends StatefulWidget {
  const DisinfectionRoundsScreen({super.key});
  @override
  State<DisinfectionRoundsScreen> createState() => _DisinfectionRoundsScreenState();
}

class _DisinfectionRoundsScreenState extends State<DisinfectionRoundsScreen> {
  static const _accent = Color(0xFF0EA5A5);
  Future<Map<String, dynamic>>? _f;

  static const _stateColor = {
    'draft': Color(0xFF94A3B8), 'assigned': Color(0xFF0EA5A5),
    'in_progress': Color(0xFF2563EB), 'done': Color(0xFF16A34A),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.disinfectRounds();

  Future<void> _assign(Map round, List workers, List teams) async {
    int? empId, teamId;
    DateTime? planned;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) {
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(
                  color: Colors.black12, borderRadius: BorderRadius.circular(3)))),
              const SizedBox(height: 14),
              Text('${tr('إسناد جولة', 'Assign round')}: ${round['name'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 14),
              DropdownButtonFormField<int>(
                value: empId, isExpanded: true,
                decoration: InputDecoration(labelText: tr('العامل', 'Worker'),
                    border: const OutlineInputBorder()),
                items: [for (final w in workers.cast<Map>())
                    DropdownMenuItem(value: w['id'] as int, child: Text('${w['name']}'))],
                onChanged: (v) => setSheet(() => empId = v),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<int>(
                value: teamId, isExpanded: true,
                decoration: InputDecoration(labelText: tr('الفريق (اختياري)', 'Team (optional)'),
                    border: const OutlineInputBorder()),
                items: [for (final t in teams.cast<Map>())
                    DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}'))],
                onChanged: (v) => setSheet(() => teamId = v),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.schedule_rounded),
                label: Text(planned == null
                    ? tr('تحديد وقت مخطّط', 'Set planned time')
                    : '${planned!.toString().substring(0, 16)}'),
                onPressed: () async {
                  final d = await showDatePicker(context: ctx,
                      firstDate: DateTime(2020), lastDate: DateTime(2100),
                      initialDate: DateTime.now());
                  if (d == null) return;
                  final t = await showTimePicker(context: ctx, initialTime: TimeOfDay.now());
                  setSheet(() => planned = DateTime(d.year, d.month, d.day, t?.hour ?? 8, t?.minute ?? 0));
                },
              ),
              const SizedBox(height: 18),
              SizedBox(width: double.infinity, child: FilledButton(
                style: FilledButton.styleFrom(backgroundColor: _accent,
                    padding: const EdgeInsets.symmetric(vertical: 14)),
                onPressed: (empId == null && teamId == null) ? null : () async {
                  try {
                    // send UTC-naive "YYYY-MM-DD HH:MM:SS" the Odoo way
                    String? pa;
                    if (planned != null) {
                      final u = planned!.toUtc();
                      pa = '${u.toString().substring(0, 19)}';
                    }
                    await context.read<AuthProvider>().api.disinfectAssign(round['id'] as int,
                        employeeId: empId, teamId: teamId, plannedAt: pa);
                    if (ctx.mounted) Navigator.pop(ctx);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                          content: Text(tr('تم الإسناد ✅', 'Assigned ✅')),
                          backgroundColor: _accent, behavior: SnackBarBehavior.floating));
                      setState(_load);
                    }
                  } catch (e) {
                    if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
                        content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
                  }
                },
                child: Text(tr('إسناد', 'Assign'),
                    style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
            ]),
          ),
        );
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('جولات التعقيم', 'Disinfection rounds'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.black54)));
          }
          final d = snap.data ?? const {};
          final rounds = (d['rounds'] as List?) ?? const [];
          final workers = (d['workers'] as List?) ?? const [];
          final teams = (d['teams'] as List?) ?? const [];
          if (rounds.isEmpty) {
            return RefreshIndicator(
              onRefresh: () async => setState(_load),
              child: ListView(children: [
                const SizedBox(height: 160),
                Center(child: Text(tr('لا جولات تعقيم', 'No disinfection rounds'),
                    style: const TextStyle(color: Colors.black54))),
              ]),
            );
          }
          return RefreshIndicator(
            color: _accent,
            onRefresh: () async => setState(_load),
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              itemCount: rounds.length,
              itemBuilder: (_, i) => _roundCard(rounds[i] as Map, workers, teams),
            ),
          );
        },
      ),
    );
  }

  Widget _roundCard(Map r, List workers, List teams) {
    final sc = _stateColor[r['state']] ?? const Color(0xFF94A3B8);
    final canAssign = r['can_assign'] == true;
    final assignee = r['assigned_to'] ?? r['assigned_team'];
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE3E7EE))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${r['name'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: sc.withOpacity(0.14), borderRadius: BorderRadius.circular(20)),
              child: Text('${r['state_label'] ?? r['state'] ?? ''}',
                  style: TextStyle(color: sc, fontWeight: FontWeight.w900, fontSize: 11))),
        ]),
        const SizedBox(height: 6),
        Text([
          if (r['location'] != null) '📍 ${r['location']}',
          if (r['facility'] != null) '${r['facility']}',
          if (r['product'] != null) '🧴 ${r['product']}',
        ].join(' · '), style: const TextStyle(fontSize: 12, color: Colors.black54)),
        if (r['planned_at'] != null || assignee != null) ...[
          const SizedBox(height: 6),
          Text([
            if (r['planned_at'] != null) '🕒 ${r['planned_at']}',
            if (assignee != null) '👤 $assignee',
            if (r['priority_label'] != null) '⚑ ${r['priority_label']}',
          ].join(' · '), style: const TextStyle(fontSize: 11.5, color: Colors.black45)),
        ],
        if (canAssign) ...[
          const SizedBox(height: 10),
          SizedBox(width: double.infinity, child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: _accent),
            icon: const Icon(Icons.person_add_alt_rounded, size: 18),
            label: Text(assignee == null ? tr('إسناد', 'Assign') : tr('إعادة إسناد', 'Reassign')),
            onPressed: () => _assign(r, workers, teams),
          )),
        ],
      ]),
    );
  }
}
