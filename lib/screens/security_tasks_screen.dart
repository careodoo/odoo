import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «مهام الأمن» — الحارس يرى مهامه هو فقط. ترويسة إحصائيات + أرشيف شهري + فلترة
/// بالحالة + أزرار قبول/بدء/إنجاز مباشرة، وتفاصيل غنية لكل مهمة.
class SecurityTasksScreen extends StatefulWidget {
  const SecurityTasksScreen({super.key});
  @override
  State<SecurityTasksScreen> createState() => _SecurityTasksScreenState();
}

class _SecurityTasksScreenState extends State<SecurityTasksScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _month; // 'YYYY-MM'
  String _state = 'all';

  static const _monthsAr = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
  String _monthLabel(String ym) {
    final parts = ym.split('-');
    if (parts.length != 2) return ym;
    final m = int.tryParse(parts[1]) ?? 0;
    return '${(m >= 1 && m <= 12) ? _monthsAr[m] : parts[1]} ${parts[0]}';
  }

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      int? y, mo;
      if (_month != null) { final p = _month!.split('-'); y = int.parse(p[0]); mo = int.parse(p[1]); }
      final d = await context.read<AuthProvider>().api.securityMyTasks(year: y, month: mo, state: _state);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _act(int id, String action) async {
    try {
      await context.read<AuthProvider>().api.securityTaskAction(id, action);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(_actMsg(action)), backgroundColor: _green));
      }
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: _red));
    }
  }

  String _actMsg(String a) => a == 'accept' ? tr('تم قبول المهمة', 'Task accepted')
      : a == 'start' ? tr('بدأ تنفيذ المهمة', 'Task started') : tr('تم إنجاز المهمة', 'Task completed');

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final header = (_data?['header'] as Map?) ?? const {};
    final months = ((_data?['months'] as List?) ?? const []).cast();
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('مهامي', 'My tasks')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: Column(children: [
        _statsHeader(header),
        _archiveBar(months),
        _stateBar(header),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? _empty()
                : RefreshIndicator(onRefresh: _load,
                    child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                        children: [for (final t in items) _taskCard(t)]))),
      ]),
    );
  }

  Widget _statsHeader(Map h) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 6),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(children: [
        _hstat('${h['total'] ?? 0}', tr('الإجمالي', 'Total'), Colors.white),
        _div(), _hstat('${h['open'] ?? 0}', tr('مفتوحة', 'Open'), _amber),
        _div(), _hstat('${h['in_progress'] ?? 0}', tr('جارية', 'Active'), _blue),
        _div(), _hstat('${h['completed'] ?? 0}', tr('منجزة', 'Done'), _green),
      ]),
    );
  }

  Widget _div() => Container(width: 1, height: 34, color: const Color(0xFF2C4258));
  Widget _hstat(String v, String l, Color c) => Expanded(
      child: Column(children: [
        Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 20)),
        const SizedBox(height: 2),
        Text(l, style: const TextStyle(color: _muted, fontSize: 10.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _archiveBar(List months) {
    if (months.isEmpty) return const SizedBox.shrink();
    return SizedBox(height: 38, child: ListView(scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12), children: [
      _chip(tr('الكل', 'All'), _month == null, () => setState(() { _month = null; _load(); })),
      for (final m in months) _chip(_monthLabel('$m'), _month == '$m', () => setState(() { _month = '$m'; _load(); })),
    ]));
  }

  Widget _stateBar(Map h) {
    final states = [
      ('all', tr('الكل', 'All'), null),
      ('new', tr('جديدة', 'New'), h['new']),
      ('accepted', tr('مقبولة', 'Accepted'), h['accepted']),
      ('in_progress', tr('جارية', 'Active'), h['in_progress']),
      ('completed', tr('منجزة', 'Done'), h['completed']),
    ];
    return SizedBox(height: 40, child: ListView(scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12), children: [
      for (final s in states) _chip(s.$3 == null ? s.$2 : '${s.$2} ${s.$3}', _state == s.$1, () => setState(() { _state = s.$1; _load(); })),
    ]));
  }

  Widget _chip(String label, bool active, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.only(left: 8, top: 4, bottom: 4),
        child: InkWell(onTap: onTap, borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            decoration: BoxDecoration(
              color: active ? _blue : _card,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: active ? _blue : const Color(0xFF2A3B54)),
            ),
            child: Text(label, style: TextStyle(color: active ? Colors.white : _muted, fontSize: 12, fontWeight: FontWeight.w700)),
          )),
      );

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100),
        const Icon(Icons.checklist_rounded, size: 74, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا مهام في هذه الفترة.', 'No tasks in this period.'), style: const TextStyle(color: _muted))),
      ]);

  Color _prioColor(String? p) => p == '3' ? _red : p == '2' ? _amber : p == '1' ? _blue : const Color(0xFF64748B);
  Color _stateColor(String? s) => s == 'completed' ? _green : s == 'in_progress' ? _blue
      : s == 'accepted' ? _amber : s == 'refused' ? _red : const Color(0xFF64748B);

  Widget _taskCard(Map t) {
    final prio = _prioColor('${t['priority']}');
    final prog = (t['progress'] ?? 0) as int;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFF20344E))),
      child: Column(children: [
        InkWell(
          onTap: () => _openDetail(t),
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(width: 4, height: 44, margin: const EdgeInsetsDirectional.only(end: 10),
                  decoration: BoxDecoration(color: prio, borderRadius: BorderRadius.circular(3))),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${t['name'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5))),
                  _statePill(t),
                ]),
                const SizedBox(height: 4),
                Text([t['category'], t['type'], if (t['deadline'] != null) '⏰ ${t['deadline']}'].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
                if (prog > 0) ...[
                  const SizedBox(height: 8),
                  ClipRRect(borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(value: prog / 100.0, minHeight: 5,
                          backgroundColor: const Color(0xFF223349), color: _stateColor('${t['state']}'))),
                ],
              ])),
            ]),
          ),
        ),
        _actionRow(t),
      ]),
    );
  }

  Widget _statePill(Map t) {
    final c = _stateColor('${t['state']}');
    return Container(
      margin: const EdgeInsetsDirectional.only(start: 6),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
      child: Text('${t['state_label'] ?? t['state'] ?? ''}', style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
    );
  }

  Widget _actionRow(Map t) {
    final btns = <Widget>[];
    if (t['can_accept'] == true) btns.add(_actBtn(tr('قبول', 'Accept'), Icons.check_rounded, _amber, () => _act(t['id'] as int, 'accept')));
    if (t['can_start'] == true) btns.add(_actBtn(tr('بدء', 'Start'), Icons.play_arrow_rounded, _blue, () => _act(t['id'] as int, 'start')));
    if (t['can_complete'] == true) btns.add(_actBtn(tr('إنجاز', 'Complete'), Icons.done_all_rounded, _green, () => _act(t['id'] as int, 'complete')));
    if (btns.isEmpty) return const SizedBox.shrink();
    return Container(
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFF20344E)))),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      child: Row(children: [for (final b in btns) Expanded(child: b)]),
    );
  }

  Widget _actBtn(String s, IconData ic, Color c, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: TextButton.icon(
          onPressed: onTap,
          icon: Icon(ic, size: 17, color: c),
          label: Text(s, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
          style: TextButton.styleFrom(backgroundColor: c.withValues(alpha: 0.12), padding: const EdgeInsets.symmetric(vertical: 9),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
        ),
      );

  void _openDetail(Map t) async {
    showModalBottomSheet(
      context: context, backgroundColor: _card, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _TaskSheet(id: t['id'] as int, onAction: (id, a) async { Navigator.pop(context); await _act(id, a); }),
    );
  }
}

// ============ ورقة تفاصيل المهمة ============
class _TaskSheet extends StatefulWidget {
  final int id;
  final Future<void> Function(int id, String action) onAction;
  const _TaskSheet({required this.id, required this.onAction});
  @override
  State<_TaskSheet> createState() => _TaskSheetState();
}

class _TaskSheetState extends State<_TaskSheet> {
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);
  static const _amber = Color(0xFFF7A23B);
  Map<String, dynamic>? _d;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final d = await context.read<AuthProvider>().api.securityTaskDetail(widget.id); if (mounted) setState(() => _d = d); }
    catch (_) { if (mounted) setState(() => _d = {}); }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: d == null
          ? const SizedBox(height: 200, child: Center(child: CircularProgressIndicator()))
          : SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                const SizedBox(height: 10),
                Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFF34506F), borderRadius: BorderRadius.circular(3)))),
                const SizedBox(height: 14),
                Padding(padding: const EdgeInsets.symmetric(horizontal: 18),
                    child: Text('${d['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17))),
                const SizedBox(height: 10),
                _row(tr('الحالة', 'State'), d['state_label']),
                _row(tr('الأولوية', 'Priority'), d['priority_label']),
                _row(tr('التصنيف', 'Category'), d['category']),
                _row(tr('النوع', 'Type'), d['type']),
                _row(tr('الموقع', 'Premise'), d['premise']),
                _row(tr('العميل', 'Client'), d['client']),
                _row(tr('الموعد', 'Deadline'), d['deadline']),
                _row(tr('البدء', 'Started'), d['start_date']),
                _row(tr('الإنجاز', 'Completed'), d['date_completed']),
                _row(tr('نسبة الإنجاز', 'Progress'), d['progress'] != null ? '${d['progress']}%' : null),
                if ('${d['description'] ?? ''}'.replaceAll(RegExp(r'<[^>]*>'), '').trim().isNotEmpty) ...[
                  const Padding(padding: EdgeInsets.fromLTRB(18, 12, 18, 4), child: Text('الوصف', style: TextStyle(color: _muted, fontWeight: FontWeight.w700, fontSize: 12))),
                  Padding(padding: const EdgeInsets.symmetric(horizontal: 18),
                      child: Text('${d['description']}'.replaceAll(RegExp(r'<[^>]*>'), '').trim(), style: const TextStyle(color: Colors.white, fontSize: 13))),
                ],
                if (((d['checklist'] as List?) ?? const []).isNotEmpty) ...[
                  const Padding(padding: EdgeInsets.fromLTRB(18, 14, 18, 6), child: Text('قائمة المهام', style: TextStyle(color: _muted, fontWeight: FontWeight.w700, fontSize: 12))),
                  for (final c in (d['checklist'] as List).cast<Map>())
                    Padding(padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 3), child: Row(children: [
                      Icon(c['done'] == true ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
                          size: 18, color: c['done'] == true ? _green : _muted),
                      const SizedBox(width: 8),
                      Expanded(child: Text('${c['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 13))),
                    ])),
                ],
                const SizedBox(height: 16),
                Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 22), child: Row(children: [
                  if (d['can_accept'] == true) Expanded(child: _b(tr('قبول', 'Accept'), _amber, () => widget.onAction(widget.id, 'accept'))),
                  if (d['can_start'] == true) Expanded(child: _b(tr('بدء', 'Start'), _blue, () => widget.onAction(widget.id, 'start'))),
                  if (d['can_complete'] == true) ...[
                    if (d['can_accept'] == true || d['can_start'] == true) const SizedBox(width: 10),
                    Expanded(child: _b(tr('إنجاز', 'Complete'), _green, () => widget.onAction(widget.id, 'complete'))),
                  ],
                ])),
              ]),
            ),
    );
  }

  Widget _row(String l, dynamic v) {
    if (v == null || '$v'.isEmpty) return const SizedBox.shrink();
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 5), child: Row(children: [
      Text(l, style: const TextStyle(color: _muted, fontSize: 12.5)),
      const Spacer(),
      Flexible(child: Text('$v', textAlign: TextAlign.end, style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
    ]));
  }

  Widget _b(String s, Color c, VoidCallback onTap) => ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(backgroundColor: c, foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
        child: Text(s, style: const TextStyle(fontWeight: FontWeight.w800)),
      );
}
