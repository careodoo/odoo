import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;

/// Task list for a filter / project / stage.
class PmsTasksScreen extends StatefulWidget {
  const PmsTasksScreen({super.key, required this.filter, required this.title, this.projectId, this.stageId});
  final String filter, title;
  final int? projectId, stageId;

  @override
  State<PmsTasksScreen> createState() => _PmsTasksScreenState();
}

class _PmsTasksScreenState extends State<PmsTasksScreen> {
  late Future<Map<String, dynamic>> _f;
  final _search = TextEditingController();
  Timer? _deb;
  String _q = '';
  late String _filter = widget.filter;

  static const _filters = [
    ['', 'الكل', 'All'], ['open', 'مفتوحة', 'Open'], ['overdue', 'متأخرة', 'Overdue'],
    ['today', 'اليوم', 'Today'], ['mine', 'مهامي', 'Mine'], ['done', 'منجزة', 'Done'],
  ];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _deb?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.pmsTasks(
      projectId: widget.projectId, stageId: widget.stageId, filter: _filter, q: _q));

  Future<void> _createTask() async {
    final name = TextEditingController();
    final desc = TextEditingController();
    bool urgent = false;
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) => Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('مهمة جديدة', 'New task'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink)),
          const SizedBox(height: 12),
          TextField(
            controller: name, autofocus: true,
            decoration: InputDecoration(
                labelText: tr('عنوان المهمة', 'Task title'), border: const OutlineInputBorder()),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: desc, maxLines: 3,
            decoration: InputDecoration(
                labelText: tr('الوصف (اختياري)', 'Description (optional)'),
                border: const OutlineInputBorder()),
          ),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: urgent, onChanged: (v) => setSheet(() => urgent = v),
            title: Text(tr('عاجلة', 'Urgent'), style: const TextStyle(fontSize: 13.5)),
            activeThumbColor: Pms.violet,
          ),
          const SizedBox(height: 4),
          SizedBox(width: double.infinity, child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: Pms.violet),
            onPressed: () => Navigator.pop(ctx, true),
            icon: const Icon(Icons.check_rounded),
            label: Text(tr('إنشاء', 'Create')),
          )),
        ]),
      )),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    try {
      await context.read<AuthProvider>().api.pmsTaskCreate(widget.projectId!, {
        'name': name.text.trim(),
        if (desc.text.trim().isNotEmpty) 'description': desc.text.trim(),
        if (urgent) 'priority': '1',
      });
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('أُنشئت المهمة', 'Task created')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  void _onSearch(String v) {
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 400), () {
      if (!mounted) return;
      _q = v.trim();
      _reload();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(gLang == 'en' ? 'Tasks' : widget.title, overflow: TextOverflow.ellipsis),
      ),
      // Creating a task needs a home project; only offer it when scoped to one.
      floatingActionButton: widget.projectId == null
          ? null
          : FloatingActionButton.extended(
              backgroundColor: Pms.violet, foregroundColor: Colors.white,
              icon: const Icon(Icons.add_task_rounded),
              label: Text(tr('مهمة جديدة', 'New task'),
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              onPressed: _createTask,
            ),
      body: Column(children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
          child: Column(children: [
            TextField(
              controller: _search,
              onChanged: _onSearch,
              decoration: InputDecoration(
                hintText: tr('ابحث عن مهمة…', 'Search tasks…'),
                prefixIcon: const Icon(Icons.search_rounded, size: 20),
                filled: true, fillColor: Pms.bg, isDense: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(height: 32, child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final f in _filters) ...[
                GestureDetector(
                  onTap: () { setState(() => _filter = f[0]); _reload(); },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: _filter == f[0] ? Pms.violet : Pms.bg,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: _filter == f[0] ? Colors.transparent : Colors.black12),
                    ),
                    child: Text(gLang == 'en' ? f[2] : f[1],
                        style: TextStyle(color: _filter == f[0] ? Colors.white : Pms.slate,
                            fontWeight: FontWeight.w800, fontSize: 12)),
                  ),
                ),
                const SizedBox(width: 7),
              ],
            ])),
          ]),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => _reload(),
            child: FutureBuilder<Map<String, dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (snap.hasError) {
                  return ListView(children: [Padding(padding: const EdgeInsets.all(40),
                      child: Center(child: Text('${snap.error}', textAlign: TextAlign.center,
                          style: const TextStyle(color: Pms.slate))))]);
                }
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final rows = (snap.data!['rows'] as List?) ?? [];
                final total = snap.data!['count'] ?? 0;
                if (rows.isEmpty) {
                  return ListView(children: [Padding(padding: const EdgeInsets.only(top: 90),
                      child: Center(child: Text(tr('لا مهام', 'No tasks'),
                          style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700))))]);
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) => i == 0
                      ? Padding(padding: const EdgeInsets.only(bottom: 2),
                          child: Text(tr('عرض ${rows.length} من $total', 'Showing ${rows.length} of $total'),
                              style: const TextStyle(color: Pms.slate, fontSize: 11.5, fontWeight: FontWeight.w700)))
                      : _card(rows[i - 1] as Map),
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  Widget _card(Map t) {
    final overdue = t['overdue'] == true;
    final done = t['done'] == true;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => PmsTaskDetail(taskId: t['id'] as int)));
          _reload();
        },
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: overdue ? Pms.red.withValues(alpha: 0.5) : Colors.black12),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              if (t['priority'] == '1') const Padding(padding: EdgeInsets.only(left: 4),
                  child: Icon(Icons.star_rounded, color: Pms.amber, size: 16)),
              Expanded(child: Text('${t['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, height: 1.25,
                      color: done ? Pms.slate : Pms.ink,
                      decoration: done ? TextDecoration.lineThrough : null))),
              if (t['stage'] != null) Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: (done ? Pms.green : Pms.violet).withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(20)),
                child: Text('${(t['stage'] as Map)['name']}',
                    style: TextStyle(color: done ? Pms.green : Pms.violet, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
            ]),
            if (t['project'] != null) Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text('${(t['project'] as Map)['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Pms.slate, fontSize: 11)),
            ),
            const SizedBox(height: 7),
            Row(children: [
              if (t['deadline'] != null) ...[
                Icon(Icons.event_rounded, size: 13, color: overdue ? Pms.red : Pms.slate),
                const SizedBox(width: 4),
                Text('${t['deadline']}'.substring(0, 10),
                    style: TextStyle(fontSize: 11, fontWeight: overdue ? FontWeight.w800 : FontWeight.w600,
                        color: overdue ? Pms.red : Pms.slate)),
                if (overdue) Padding(padding: const EdgeInsets.only(right: 5),
                    child: Text(tr(' • متأخرة', ' • overdue'),
                        style: const TextStyle(fontSize: 10.5, color: Pms.red, fontWeight: FontWeight.w800))),
              ],
              const Spacer(),
              if ((t['subtasks'] as int? ?? 0) > 0) Padding(
                padding: const EdgeInsets.only(left: 8),
                child: Row(children: [
                  const Icon(Icons.account_tree_rounded, size: 12, color: Pms.slate),
                  const SizedBox(width: 3),
                  Text('${t['subtasks']}', style: const TextStyle(fontSize: 11, color: Pms.slate)),
                ]),
              ),
              for (final a in ((t['assignees'] as List?) ?? []).take(3))
                Padding(
                  padding: const EdgeInsets.only(left: 3),
                  child: CircleAvatar(radius: 10, backgroundColor: Pms.violet.withValues(alpha: 0.15),
                      child: Text('${(a as Map)['name']}'.characters.first,
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w900, color: Pms.deep))),
                ),
            ]),
          ]),
        ),
      ),
    );
  }
}

/// Full task detail — every field, plus stage / priority / note actions.
class PmsTaskDetail extends StatefulWidget {
  const PmsTaskDetail({super.key, required this.taskId});
  final int taskId;
  @override
  State<PmsTaskDetail> createState() => _PmsTaskDetailState();
}

class _PmsTaskDetailState extends State<PmsTaskDetail> {
  late Future<Map<String, dynamic>> _f;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.pmsTask(widget.taskId));

  String _strip(String html) => html
      .replaceAll(RegExp(r'<br\s*/?>'), '\n')
      .replaceAll(RegExp(r'<[^>]+>'), '')
      .replaceAll('&nbsp;', ' ')
      .trim();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Text(tr('تفاصيل المهمة', 'Task')),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.hasError) {
            return Center(child: Padding(padding: const EdgeInsets.all(30),
                child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))));
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final d = snap.data!;
          final overdue = d['overdue'] == true;
          final desc = _strip('${d['description'] ?? ''}');
          final stages = (d['stages'] as List?) ?? [];
          final msgs = (d['messages'] as List?) ?? [];
          final kids = (d['children'] as List?) ?? [];
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            // header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.black12)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${d['name']}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink, height: 1.3))),
                  IconButton(
                    tooltip: tr('أولوية', 'Priority'),
                    icon: Icon(d['priority'] == '1' ? Icons.star_rounded : Icons.star_border_rounded,
                        color: Pms.amber),
                    onPressed: d['can_write'] == true && !_busy
                        ? () => _setPriority(d['priority'] != '1') : null,
                  ),
                ]),
                if (d['project'] != null) Text('${(d['project'] as Map)['name']}',
                    style: const TextStyle(color: Pms.slate, fontSize: 12)),
                const SizedBox(height: 10),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  if (d['stage'] != null) _pill('${(d['stage'] as Map)['name']}', Pms.violet),
                  if (d['done'] == true) _pill(tr('منجزة', 'Done'), Pms.green),
                  if (overdue) _pill(tr('متأخرة', 'Overdue'), Pms.red),
                  for (final t in ((d['tags'] as List?) ?? [])) _pill('$t', Pms.slate),
                ]),
              ]),
            ),
            const SizedBox(height: 12),
            // fields
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.black12)),
              child: Column(children: [
                if (d['deadline'] != null)
                  _kv(Icons.event_rounded, tr('الموعد النهائي', 'Deadline'), '${d['deadline']}',
                      color: overdue ? Pms.red : null),
                if (d['date_assign'] != null) _kv(Icons.assignment_ind_rounded, tr('تاريخ الإسناد', 'Assigned on'), '${d['date_assign']}'),
                if (d['date_end'] != null) _kv(Icons.done_all_rounded, tr('تاريخ الإنجاز', 'Ended'), '${d['date_end']}'),
                if (d['partner'] != null) _kv(Icons.business_rounded, tr('العميل', 'Customer'), '${(d['partner'] as Map)['name']}'),
                if (d['department'] != null) _kv(Icons.apartment_rounded, tr('القسم', 'Department'), '${(d['department'] as Map)['name']}'),
                if (d['category'] != null) _kv(Icons.category_rounded, tr('التصنيف', 'Category'), '${(d['category'] as Map)['name']}'),
                if (d['parent'] != null) _kv(Icons.subdirectory_arrow_right_rounded, tr('مهمة أصل', 'Parent'), '${(d['parent'] as Map)['name']}'),
                if ((d['allocated_hours'] as num? ?? 0) > 0 || (d['effective_hours'] as num? ?? 0) > 0)
                  _kv(Icons.schedule_rounded, tr('الساعات', 'Hours'),
                      tr('${d['allocated_hours']} مخصّصة · ${d['effective_hours']} منفَّذة',
                         '${d['allocated_hours']} allocated · ${d['effective_hours']} spent')),
                if ((d['assignees'] as List?)?.isNotEmpty == true)
                  _kv(Icons.people_rounded, tr('المسؤولون', 'Assignees'),
                      ((d['assignees'] as List).map((a) => (a as Map)['name']).join('، '))),
              ]),
            ),
            // description
            if (desc.isNotEmpty) ...[
              const SizedBox(height: 12),
              _section(tr('الوصف', 'Description')),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.black12)),
                child: Text(desc, style: const TextStyle(fontSize: 13, height: 1.5, color: Pms.ink)),
              ),
            ],
            // subtasks
            if (kids.isNotEmpty) ...[
              const SizedBox(height: 12),
              _section(tr('المهام الفرعية (${kids.length})', 'Sub-tasks (${kids.length})')),
              for (final c in kids)
                Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.black12)),
                  child: Row(children: [
                    Icon((c as Map)['done'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
                        size: 16, color: c['done'] == true ? Pms.green : Pms.slate),
                    const SizedBox(width: 8),
                    Expanded(child: Text('${c['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600))),
                    Text('${c['stage'] ?? ''}', style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
                  ]),
                ),
            ],
            // stage actions
            if (d['can_write'] == true && stages.isNotEmpty) ...[
              const SizedBox(height: 12),
              _section(tr('نقل إلى مرحلة', 'Move to stage')),
              Wrap(spacing: 7, runSpacing: 7, children: [
                for (final s in stages)
                  ActionChip(
                    label: Text('${(s as Map)['name']}',
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12,
                            color: (d['stage'] as Map?)?['id'] == s['id'] ? Colors.white : Pms.ink)),
                    backgroundColor: (d['stage'] as Map?)?['id'] == s['id'] ? Pms.violet : Colors.white,
                    side: BorderSide(color: (d['stage'] as Map?)?['id'] == s['id'] ? Pms.violet : Colors.black12),
                    onPressed: _busy || (d['stage'] as Map?)?['id'] == s['id'] ? null : () => _move(s['id'] as int),
                  ),
              ]),
            ],
            // ---- forwarding / routing ----
            const SizedBox(height: 12),
            _forwardBlock(d),
            // chatter
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: _section(tr('المتابعة (${msgs.length})', 'Activity (${msgs.length})'))),
              TextButton.icon(
                onPressed: _busy ? null : _addNote,
                icon: const Icon(Icons.add_comment_rounded, size: 16),
                label: Text(tr('ملاحظة', 'Note')),
              ),
            ]),
            for (final m in msgs)
              Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.black12)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Text('${(m as Map)['author']}',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, color: Pms.deep)),
                    const Spacer(),
                    Text('${m['date'] ?? ''}'.split('.').first,
                        style: const TextStyle(fontSize: 10, color: Pms.slate)),
                  ]),
                  const SizedBox(height: 4),
                  Text(_strip('${m['body']}'), style: const TextStyle(fontSize: 12, height: 1.4)),
                ]),
              ),
            if (msgs.isEmpty) Padding(padding: const EdgeInsets.all(14),
                child: Center(child: Text(tr('لا متابعات', 'No activity'), style: const TextStyle(color: Pms.slate)))),
          ]);
        },
      ),
    );
  }

  Widget _section(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6, top: 2),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14)),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
      );

  Widget _kv(IconData i, String k, String v, {Color? color}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(i, size: 16, color: color ?? Pms.slate),
          const SizedBox(width: 9),
          SizedBox(width: 96, child: Text(k, style: const TextStyle(color: Pms.slate, fontSize: 12))),
          Expanded(child: Text(v, style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: color ?? Pms.ink))),
        ]),
      );

  /// The forwarding panel. When the task is forwarded TO me, I get
  /// accept/reject; otherwise (if I can write) I can forward it onward.
  Widget _forwardBlock(Map d) {
    final state = '${d['forward_state'] ?? 'none'}';
    final to = d['forward_to'] as Map?;
    final from = d['forward_from'] as Map?;
    final isRecipient = d['is_recipient'] == true;
    final pending = state == 'pending';
    if (state == 'none' && d['can_write'] != true) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: pending ? Pms.amber.withValues(alpha: 0.5) : Colors.black12),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.alt_route_rounded, size: 16, color: Pms.violet),
          const SizedBox(width: 6),
          Text(tr('الإحالة', 'Forwarding'),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 13.5)),
          const Spacer(),
          if (state != 'none')
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                  color: _fwdColor(state).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
              child: Text(_fwdLabel(state),
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: _fwdColor(state))),
            ),
        ]),
        if (to != null || from != null) ...[
          const SizedBox(height: 8),
          if (from != null) _fwdLine(Icons.person_outline_rounded, tr('أحالها', 'From'), '${from['name']}'),
          if (to != null) _fwdLine(Icons.arrow_forward_rounded, tr('إلى', 'To'), '${to['name']}'),
          if (d['forward_reason'] != null)
            _fwdLine(Icons.notes_rounded, tr('السبب', 'Reason'), '${d['forward_reason']}'),
        ],
        const SizedBox(height: 10),
        // I am the recipient of a pending forward → accept / reject.
        if (isRecipient && pending)
          Row(children: [
            Expanded(child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.green),
              onPressed: _busy ? null : _accept,
              icon: const Icon(Icons.check_rounded, size: 17),
              label: Text(tr('قبول', 'Accept')),
            )),
            const SizedBox(width: 8),
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5484D)),
              onPressed: _busy ? null : _reject,
              icon: const Icon(Icons.close_rounded, size: 17),
              label: Text(tr('رفض', 'Reject')),
            )),
          ])
        // Otherwise, if I can edit, I can forward it (onward).
        else if (d['can_write'] == true)
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: Pms.violet),
              onPressed: _busy ? null : () => _forward(d),
              icon: const Icon(Icons.alt_route_rounded, size: 17),
              label: Text(pending ? tr('إعادة الإحالة', 'Re-forward') : tr('إحالة إلى مستخدم', 'Forward to user')),
            ),
          ),
      ]),
    );
  }

  Widget _fwdLine(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 12, color: Pms.slate),
          const SizedBox(width: 6),
          Text('$k: ', style: const TextStyle(fontSize: 11.5, color: Pms.slate, fontWeight: FontWeight.w600)),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
        ]),
      );

  Color _fwdColor(String s) => {
        'pending': Pms.amber, 'accepted': Pms.green, 'rejected': const Color(0xFFE5484D),
      }[s] ?? Pms.slate;
  String _fwdLabel(String s) => {
        'pending': tr('بانتظار القبول', 'Pending'),
        'accepted': tr('مقبولة', 'Accepted'),
        'rejected': tr('مرفوضة', 'Rejected'),
      }[s] ?? s;

  Future<void> _forward(Map d) async {
    final proj = d['project'] as Map?;
    if (proj == null) return;
    List<dynamic> users;
    try {
      users = await context.read<AuthProvider>().api.pmsForwardUsers(proj['id'] as int);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      return;
    }
    if (!mounted) return;
    int? picked;
    final reason = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) => Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('إحالة المهمة إلى', 'Forward task to'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink)),
          const SizedBox(height: 10),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 280),
            child: ListView(shrinkWrap: true, children: [
              for (final u in users)
                RadioListTile<int>(
                  dense: true,
                  value: u['id'] as int, groupValue: picked,
                  onChanged: (v) => setSheet(() => picked = v),
                  title: Text('${u['name']}', style: const TextStyle(fontSize: 13)),
                ),
            ]),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: reason,
            decoration: InputDecoration(
              hintText: tr('سبب الإحالة (اختياري)', 'Reason (optional)'),
              border: const OutlineInputBorder(), isDense: true),
          ),
          const SizedBox(height: 12),
          SizedBox(width: double.infinity, child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Pms.violet),
            onPressed: picked == null ? null : () => Navigator.pop(ctx, true),
            child: Text(tr('إحالة', 'Forward')),
          )),
        ]),
      )),
    );
    if (ok != true || picked == null) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskForward(widget.taskId, picked!, reason: reason.text.trim());
      _reload();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تمت الإحالة', 'Forwarded')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _accept() async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskAccept(widget.taskId);
      _reload();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('قُبلت الإحالة', 'Accepted')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reject() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('رفض الإحالة', 'Reject forward')),
      content: TextField(controller: reason, maxLines: 2,
          decoration: InputDecoration(hintText: tr('السبب (اختياري)', 'Reason (optional)'))),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('رفض', 'Reject'))),
      ],
    ));
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskReject(widget.taskId, reason: reason.text.trim());
      _reload();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('رُفضت الإحالة', 'Rejected'))));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _move(int stageId) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskStage(widget.taskId, stageId);
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم نقل المهمة', '✅ Task moved')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setPriority(bool starred) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskPriority(widget.taskId, starred);
      if (mounted) _reload();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addNote() async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('إضافة ملاحظة', 'Add a note'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: TextField(controller: c, maxLines: 4, autofocus: true,
          decoration: InputDecoration(hintText: tr('اكتب ملاحظتك…', 'Write your note…'),
              filled: true, fillColor: Pms.bg,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none))),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: Pms.violet, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال', 'Post'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskNote(widget.taskId, c.text.trim());
      if (mounted) _reload();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
