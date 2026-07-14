import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client-facing cleaning suite: overview + quality audits (accept/dispute),
/// schedule compliance, cleaning rounds and consumables ledger (scoped to the
/// client's facilities). Mirrors the portal's cleaning section.
class ClientCleaningScreen extends StatefulWidget {
  const ClientCleaningScreen({super.key});
  @override
  State<ClientCleaningScreen> createState() => _ClientCleaningScreenState();
}

class _ClientCleaningScreenState extends State<ClientCleaningScreen> {
  Map<String, dynamic>? _summary;
  String _kind = 'audits';
  Future<List<dynamic>>? _list;

  static const _kinds = [
    ['audits', '✅ التدقيق', 'Audits'],
    ['schedules', '🕒 الجداول', 'Schedules'],
    ['rounds', '🚶 الجولات', 'Rounds'],
    ['consumables', '🧴 المواد', 'Supplies'],
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _loadKind('audits');
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientCleanSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _loadKind(String k) => setState(() {
        _kind = k;
        _list = context.read<AuthProvider>().api.clientClean(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    final sc = (s?['avg_score'] ?? 0);
    return Scaffold(
      appBar: AppBar(title: Text(tr('النظافة', 'Cleaning'))),
      body: Column(children: [
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('📊', '$sc%', tr('متوسط الجودة', 'Avg score'), _scoreColor(sc)),
              _stat('✅', '${s['audits'] ?? 0}', tr('تدقيقات', 'Audits'), const Color(0xFF0891B2)),
              _stat('🔔', '${s['audits_pending_ack'] ?? 0}', tr('بانتظار إقرارك', 'Pending ack'), const Color(0xFFF59E0B)),
              _stat('🕒', '${s['schedules_due'] ?? 0}', tr('تنظيف مستحقّ', 'Due'), const Color(0xFFE11D48)),
              _stat('🧴', '${s['consumables'] ?? 0}', tr('مواد', 'Supplies'), const Color(0xFF6366F1)),
              _stat('⚠️', '${s['low_stock'] ?? 0}', tr('مخزون منخفض', 'Low stock'), const Color(0xFFE11D48)),
            ]),
          ),
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
            for (final k in _kinds)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: ChoiceChip(
                  label: Text(gLang == 'en' ? k[2] : k[1]),
                  selected: _kind == k[0],
                  onSelected: (_) => _loadKind(k[0]),
                ),
              ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records')));
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
              );
            },
          ),
        ),
      ]),
    );
  }

  Color _scoreColor(dynamic v) {
    final s = (v is num) ? v : 0;
    return s >= 90 ? const Color(0xFF16A34A) : s >= 75 ? const Color(0xFF0891B2) : s >= 60 ? const Color(0xFFF59E0B) : const Color(0xFFE11D48);
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 132,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  static const _ackC = {'accepted': Color(0xFF16A34A), 'disputed': Color(0xFFE11D48), 'pending': Color(0xFFF59E0B)};

  Widget _row(Map r) {
    if (_kind == 'audits') {
      final sc = _scoreColor(r['score']);
      final ack = '${r['ack'] ?? 'pending'}';
      return ListTile(
        title: Text('${r['name']} · ${r['score']}%', style: TextStyle(fontWeight: FontWeight.w700, color: sc)),
        subtitle: Text([r['facility'], r['location'], r['rating']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
            maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill('${r['ack_label']}', _ackC[ack] ?? Colors.grey),
        onTap: () => _openAudit(r),
      );
    }
    if (_kind == 'schedules') {
      final due = r['is_due'] == true;
      return ListTile(
        leading: const Text('🕒', style: TextStyle(fontSize: 20)),
        title: Text('${r['location'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${r['facility'] ?? ''} · ${r['frequency'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill(due ? tr('مستحقّ', 'Due') : tr('منتظم', 'OK'), due ? const Color(0xFFE11D48) : const Color(0xFF16A34A)),
      );
    }
    if (_kind == 'rounds') {
      return ListTile(
        leading: const Text('🚶', style: TextStyle(fontSize: 20)),
        title: Text('${r['worker'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${r['location'] ?? ''} · ${r['scan_in'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: Text('${r['duration_min'] ?? 0} ${tr('د', 'm')}', style: const TextStyle(fontWeight: FontWeight.w700)),
      );
    }
    // consumables
    final low = r['low_stock'] == true;
    return ListTile(
      leading: const Text('🧴', style: TextStyle(fontSize: 20)),
      title: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text('${r['facility'] ?? ''} · ${r['category'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
        Text('${r['on_hand'] ?? 0} ${r['unit'] ?? ''}', style: TextStyle(fontWeight: FontWeight.w800, color: low ? const Color(0xFFE11D48) : null)),
        if (low) _pill(tr('منخفض', 'Low'), const Color(0xFFE11D48)),
      ]),
    );
  }

  Future<void> _openAudit(Map a) async {
    final items = (a['items'] as List?) ?? [];
    final commentCtrl = TextEditingController(text: '${a['ack_comment'] ?? ''}');
    final act = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.75,
        maxChildSize: 0.95,
        builder: (_, ctrl) => Padding(
          padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom),
          child: ListView(controller: ctrl, children: [
            Text('${a['name']} · ${a['score']}%', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: _scoreColor(a['score']))),
            Text([a['facility'], a['location'], a['auditor']].where((x) => x != null && '$x'.isNotEmpty).join(' · '), style: const TextStyle(color: Colors.grey)),
            const Divider(height: 20),
            Text(tr('بنود الفحص', 'Checklist items'), style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            for (final i in items)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Text(i['result'] == 'pass' ? '✅' : i['result'] == 'fail' ? '❌' : '➖'),
                title: Text('${i['name']}'),
                subtitle: (i['note'] != null) ? Text('${i['note']}') : null,
              ),
            const Divider(height: 20),
            Text(tr('إقرارك على التدقيق', 'Acknowledge this audit'), style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            TextField(controller: commentCtrl, decoration: InputDecoration(hintText: tr('تعليق (اختياري)', 'Comment (optional)'), border: const OutlineInputBorder()), maxLines: 2),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white),
                onPressed: () => Navigator.pop(ctx, 'accept'), icon: const Icon(Icons.check), label: Text(tr('قبول', 'Accept')))),
              const SizedBox(width: 10),
              Expanded(child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE11D48), foregroundColor: Colors.white),
                onPressed: () => Navigator.pop(ctx, 'dispute'), icon: const Icon(Icons.report_problem), label: Text(tr('اعتراض', 'Dispute')))),
            ]),
            const SizedBox(height: 16),
          ]),
        ),
      ),
    );
    if (act == null || !mounted) return;
    try {
      await context.read<AuthProvider>().api.clientCleanAuditAck(a['id'] as int, act, comment: commentCtrl.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(act == 'accept' ? tr('تم قبول التدقيق', 'Audit accepted') : tr('تم تسجيل اعتراضك', 'Dispute recorded'))));
        _loadKind('audits');
        _loadSummary();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
