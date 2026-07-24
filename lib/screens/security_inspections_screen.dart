import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «التفتيشات» — inspections by state (kanban-style tabs), each opening a
/// detail with checklist/issues, workflow actions, assign-to-person, and
/// «convert to work order» routed to any service supervisor.
class SecurityInspectionsScreen extends StatefulWidget {
  const SecurityInspectionsScreen({super.key});
  @override
  State<SecurityInspectionsScreen> createState() => _SecurityInspectionsScreenState();
}

class _SecurityInspectionsScreenState extends State<SecurityInspectionsScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String _state = '';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityInspections(state: _state);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Color _sev(String? s) => switch (s) {
        'critical' => const Color(0xFFE5484D), 'high' => const Color(0xFFF2603F),
        'medium' => const Color(0xFFF7A23B), _ => const Color(0xFF37C98A),
      };
  Color _stColor(String s) => switch (s) {
        'completed' => const Color(0xFF37C98A), 'in_progress' => const Color(0xFF4AA8FF),
        'assigned' => const Color(0xFF7C3AED), 'submitted' => const Color(0xFFF7A23B),
        'cancelled' => _muted, _ => _muted,
      };

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('التفتيشات', 'Inspections')), backgroundColor: _navy),
      body: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 4), child: Row(children: [
          _stat('${st['total'] ?? 0}', tr('الكل', 'Total'), _muted),
          _stat('${st['open'] ?? 0}', tr('مفتوحة', 'Open'), const Color(0xFF4AA8FF)),
          _stat('${st['in_progress'] ?? 0}', tr('جارية', 'Active'), const Color(0xFF7C3AED)),
          _stat('${st['completed'] ?? 0}', tr('منجزة', 'Done'), const Color(0xFF37C98A)),
        ])),
        SizedBox(height: 40, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
          for (final s in [('', tr('الكل', 'All')), ('open', tr('مفتوحة', 'Open')), ('submitted', tr('مُقدّمة', 'Submitted')), ('assigned', tr('مُسندة', 'Assigned')), ('in_progress', tr('جارية', 'In progress')), ('completed', tr('منجزة', 'Completed'))])
            Padding(padding: const EdgeInsetsDirectional.only(end: 6), child: ChoiceChip(
              label: Text(s.$2, style: const TextStyle(fontSize: 11.5)),
              selected: _state == s.$1, backgroundColor: _card, selectedColor: const Color(0xFF7C3AED),
              labelStyle: TextStyle(color: _state == s.$1 ? Colors.white : _muted, fontWeight: FontWeight.w700),
              onSelected: (_) { setState(() => _state = s.$1); _load(); })),
        ])),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? Center(child: Text(tr('لا تفتيشات.', 'No inspections.'), style: const TextStyle(color: _muted)))
                : RefreshIndicator(onRefresh: _load, child: ListView.builder(
                    padding: const EdgeInsets.all(12), itemCount: items.length,
                    itemBuilder: (_, i) => _card2(items[i])))),
      ]),
    );
  }

  Widget _stat(String v, String l, Color c) => Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.symmetric(vertical: 9),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 17)),
          Text(l, style: const TextStyle(color: _muted, fontSize: 9.5, fontWeight: FontWeight.w600)),
        ])));

  Widget _card2(Map i) {
    final sc = _sev('${i['severity_raw']}');
    final st = '${i['state']}';
    return Card(color: _card, child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
          builder: (_) => _InspSheet(id: i['id'] as int)).then((_) => _load()),
      child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 40, height: 40, alignment: Alignment.center,
              decoration: BoxDecoration(color: sc.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
              child: Icon(Icons.search_rounded, color: sc, size: 20)),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${i['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13)),
            Text('${i['type'] ?? ''} · ${i['premise'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: _muted, fontSize: 11)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _stColor(st).withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
              child: Text('${i['state_label'] ?? st}', style: TextStyle(color: _stColor(st), fontWeight: FontWeight.w800, fontSize: 9.5))),
        ]),
        if (i['description'] != null) Padding(padding: const EdgeInsets.only(top: 8),
            child: Text('${i['description']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12))),
        Padding(padding: const EdgeInsets.only(top: 6), child: Row(children: [
          if (i['assigned_to'] != null) ...[const Icon(Icons.person_rounded, size: 13, color: _muted), const SizedBox(width: 3),
            Flexible(child: Text('${i['assigned_to']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)))],
          const Spacer(),
          if (i['has_workorder'] == true) const Text('🧾', style: TextStyle(fontSize: 12)),
          if (i['timestamp'] != null) Text('${i['timestamp']}', style: const TextStyle(color: _muted, fontSize: 10)),
        ])),
      ]))));
  }
}

class _InspSheet extends StatefulWidget {
  const _InspSheet({required this.id});
  final int id;
  @override
  State<_InspSheet> createState() => _InspSheetState();
}

class _InspSheetState extends State<_InspSheet> {
  static const _navy = Color(0xFF0F1B2E);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _i;
  bool _busy = false;

  static const _flow = {
    'draft': [('submit', 'تقديم', 'Submit', Color(0xFFF7A23B))],
    'submitted': [('start', 'بدء', 'Start', Color(0xFF4AA8FF))],
    'assigned': [('start', 'بدء', 'Start', Color(0xFF4AA8FF))],
    'in_progress': [('complete', 'إنهاء', 'Complete', Color(0xFF37C98A))],
    'completed': [('reopen', 'إعادة فتح', 'Reopen', Color(0xFF7C3AED))],
  };

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.securityInspectionDetail(widget.id);
      if (mounted) setState(() => _i = d);
    } catch (_) {}
  }

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _run(String key) async {
    setState(() => _busy = true);
    try {
      final d = await context.read<AuthProvider>().api.securityInspectionAction(widget.id, 'action', {'key': key});
      if (mounted) setState(() { _i = d; _busy = false; });
      _snack(tr('تم', 'Done'), const Color(0xFF16A34A));
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  Future<void> _assign() async {
    final meta = await context.read<AuthProvider>().api.securityWoServices();
    final people = ((meta['assignees'] as List?) ?? const []).cast<Map>();
    if (!mounted) return;
    final chosen = await showModalBottomSheet<Map>(context: context, isScrollControlled: true, backgroundColor: _card,
      builder: (_) => ListView(children: [
        Padding(padding: const EdgeInsets.all(14), child: Text(tr('إسناد إلى', 'Assign to'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        for (final p in people) ListTile(
          title: Text('${p['l']}', style: const TextStyle(color: Colors.white)),
          subtitle: p['job'] != null ? Text('${p['job']}', style: const TextStyle(color: _muted)) : null,
          onTap: () => Navigator.pop(_, p)),
      ]));
    if (chosen == null) return;
    setState(() => _busy = true);
    try {
      final d = await context.read<AuthProvider>().api.securityInspectionAction(widget.id, 'assign', {'employee_id': chosen['v']});
      if (mounted) setState(() { _i = d; _busy = false; });
      _snack(tr('تم الإسناد', 'Assigned'), const Color(0xFF16A34A));
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  Future<void> _toWorkorder() async {
    final meta = await context.read<AuthProvider>().api.securityWoServices();
    final services = ((meta['services'] as List?) ?? const []).cast<Map>();
    if (!mounted) return;
    final svc = await showModalBottomSheet<Map>(context: context, isScrollControlled: true, backgroundColor: _card,
      builder: (_) => ListView(children: [
        Padding(padding: const EdgeInsets.all(14), child: Text(tr('تحويل إلى أمر عمل — اختر الخدمة', 'Convert to work order — pick service'),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        for (final s in services) ListTile(
          leading: const Icon(Icons.build_rounded, color: Color(0xFFF7A23B)),
          title: Text('${s['l']}', style: const TextStyle(color: Colors.white)),
          onTap: () => Navigator.pop(_, s)),
      ]));
    if (svc == null) return;
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api.securityInspectionAction(widget.id, 'to_workorder', {'service_id': svc['v']});
      await _load();
      if (mounted) { setState(() => _busy = false); _snack('${tr('أُنشئ أمر العمل', 'Work order created')}: ${r['workorder']}', const Color(0xFF16A34A)); }
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  @override
  Widget build(BuildContext context) {
    final i = _i;
    final flow = _flow['${i?['state'] ?? ''}'] ?? const [];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.8, maxChildSize: 0.96, minChildSize: 0.4,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: i == null ? const SizedBox(height: 260, child: Center(child: CircularProgressIndicator()))
            : Stack(children: [
                ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
                  Center(child: Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.search_rounded, color: Color(0xFF7C3AED), size: 24),
                    const SizedBox(width: 10),
                    Expanded(child: Text('${i['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(20)),
                        child: Text('${i['state_label'] ?? i['state']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
                  ]),
                  const SizedBox(height: 14),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    for (final f in flow)
                      FilledButton(style: FilledButton.styleFrom(backgroundColor: f.$4), onPressed: _busy ? null : () => _run(f.$1),
                          child: Text(gLang == 'en' ? f.$3 : f.$2, style: const TextStyle(fontWeight: FontWeight.w800))),
                    OutlinedButton.icon(onPressed: _busy ? null : _assign, icon: const Icon(Icons.person_add_rounded, size: 16, color: Colors.white),
                        style: OutlinedButton.styleFrom(foregroundColor: Colors.white, side: const BorderSide(color: Colors.white38)),
                        label: Text(tr('إسناد', 'Assign'), style: const TextStyle(fontWeight: FontWeight.w800))),
                    if (i['has_workorder'] != true)
                      OutlinedButton.icon(onPressed: _busy ? null : _toWorkorder, icon: const Icon(Icons.build_rounded, size: 16, color: Color(0xFFF7A23B)),
                          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFF7A23B), side: const BorderSide(color: Color(0xFFF7A23B))),
                          label: Text(tr('تحويل لأمر عمل', 'To work order'), style: const TextStyle(fontWeight: FontWeight.w800))),
                  ]),
                  const SizedBox(height: 16),
                  _info(tr('التفاصيل', 'Details'), [
                    (tr('النوع', 'Type'), i['type']),
                    (tr('الأولوية', 'Priority'), i['priority']),
                    (tr('نوع المشكلة', 'Issue type'), i['issue_type']),
                    (tr('الخطورة', 'Severity'), i['severity']),
                    (tr('الموقع', 'Premise'), i['premise']),
                    (tr('الوحدة', 'Unit'), i['unit']),
                    (tr('الحارس', 'Guard'), i['guard']),
                    (tr('مُسند إلى', 'Assigned to'), i['assigned_to']),
                    (tr('الوصف', 'Description'), i['description']),
                    (tr('ملاحظات', 'Notes'), i['notes']),
                  ]),
                  if (((i['checklist'] as List?) ?? const []).isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(tr('قائمة الفحص', 'Checklist'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
                    const SizedBox(height: 6),
                    for (final c in ((i['checklist'] as List?) ?? const []).cast<Map>())
                      Row(children: [
                        Icon(c['ok'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                            size: 16, color: c['ok'] == true ? const Color(0xFF37C98A) : _muted),
                        const SizedBox(width: 8),
                        Expanded(child: Text('${c['name']}', style: const TextStyle(color: Colors.white, fontSize: 12.5))),
                      ]),
                  ],
                  const SizedBox(height: 20),
                ]),
                if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x66000000), child: Center(child: CircularProgressIndicator()))),
              ]),
      ),
    );
  }

  Widget _info(String title, List<(String, dynamic)> rows) {
    final present = rows.where((r) => r.$2 != null && '${r.$2}'.trim().isNotEmpty).toList();
    if (present.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5)),
        const SizedBox(height: 8),
        for (final r in present) Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 110, child: Text(r.$1, style: const TextStyle(color: _muted, fontSize: 12, fontWeight: FontWeight.w700))),
          Expanded(child: Text('${r.$2}', style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
        ])),
      ]),
    );
  }
}
