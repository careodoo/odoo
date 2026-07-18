import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/service_ui.dart';
import 'client_workorder_create.dart';

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

  static const _c = Color(0xFF0EA5E9);
  String _q = '';
  static const _kinds = <(String, String, IconData)>[
    ('audits', 'التدقيق', Icons.fact_check_rounded),
    ('schedules', 'الجداول', Icons.event_repeat_rounded),
    ('rounds', 'الجولات', Icons.directions_walk_rounded),
    ('consumables', 'المواد', Icons.cleaning_services_rounded),
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
        _q = '';
        _list = context.read<AuthProvider>().api.clientClean(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary ?? const {};
    final sc = (s['avg_score'] ?? 0);
    final label = _kinds.firstWhere((k) => k.$1 == _kind).$2;
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _c, foregroundColor: Colors.white,
        icon: const Icon(Icons.add_task_rounded),
        label: Text(tr('مهمة نظافة', 'Cleaning task'), style: const TextStyle(fontWeight: FontWeight.w900)),
        onPressed: () async {
          // Reuse the pro work-order sheet, preset to the cleaning service so the
          // client can raise a cleaning task at any location and assign a worker.
          final created = await ClientWorkorderCreateSheet.open(context, presetServiceType: 'cleaning');
          if (created == true && mounted) { _loadSummary(); _loadKind(_kind); }
        },
      ),
      appBar: AppBar(
        title: Text(tr('النظافة', 'Cleaning')),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded),
            onPressed: () { _loadSummary(); _loadKind(_kind); })],
      ),
      body: RefreshIndicator(
        onRefresh: () async { await _loadSummary(); _loadKind(_kind); },
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          ServiceHero(
            title: tr('النظافة', 'Cleaning'),
            subtitle: tr('متوسط الجودة $sc%', 'Avg quality $sc%'),
            icon: Icons.cleaning_services_rounded,
            color: _c,
            stats: [
              (tr('الجودة', 'quality'), '$sc%',
                  _scoreColor(sc) == const Color(0xFF16A34A) ? null : _scoreColor(sc)),
              (tr('تدقيق', 'audits'), '${s['audits'] ?? 0}', null),
              (tr('بانتظار إقرارك', 'pending'), '${s['audits_pending_ack'] ?? 0}',
                  ((s['audits_pending_ack'] ?? 0) as int) > 0 ? const Color(0xFFF59E0B) : null),
              (tr('تنظيف مستحقّ', 'due'), '${s['schedules_due'] ?? 0}', null),
              (tr('مواد', 'supplies'), '${s['consumables'] ?? 0}', null),
              (tr('مخزون منخفض', 'low'), '${s['low_stock'] ?? 0}',
                  ((s['low_stock'] ?? 0) as int) > 0 ? const Color(0xFFDC2626) : null),
            ],
            onStatTap: (i) => _loadKind(const [
              'audits', 'audits', 'audits', 'schedules', 'consumables', 'consumables'][i]),
          ),
          const SizedBox(height: 12),
          ServiceTabs(kinds: _kinds, current: _kind, onSelect: _loadKind, color: _c),
          const SizedBox(height: 10),
          FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Padding(padding: EdgeInsets.symmetric(vertical: 50),
                    child: Center(child: CircularProgressIndicator()));
              }
              final all = snap.data ?? const [];
              final rows = _q.isEmpty
                  ? all
                  : all.where((r) => (r as Map).values.map((v) => '$v').join(' ').toLowerCase()
                      .contains(_q.toLowerCase())).toList();
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (all.length > 6) ...[
                  TextField(
                    onChanged: (v) => setState(() => _q = v),
                    decoration: InputDecoration(
                      hintText: tr('ابحث في $label…', 'Search $label…'),
                      prefixIcon: const Icon(Icons.search_rounded, size: 19),
                      isDense: true, filled: true,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                MoreList(
                  items: rows,
                  color: _c,
                  header: label,
                  emptyText: tr('لا سجلات في $label.', 'No $label records.'),
                  itemBuilder: (_, r, __) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Material(
                      color: Theme.of(context).cardColor,
                      borderRadius: BorderRadius.circular(12),
                      child: _row(r as Map),
                    ),
                  ),
                ),
              ]);
            },
          ),
        ]),
      ),
    );
  }

  Color _scoreColor(dynamic v) {
    final n = (v is num) ? v.toDouble() : double.tryParse('$v') ?? 0;
    if (n >= 85) return const Color(0xFF16A34A);
    if (n >= 70) return const Color(0xFFF59E0B);
    return const Color(0xFFE11D48);
  }

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
