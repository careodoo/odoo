import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;
import 'pms_section.dart' show PmsPhotoView;

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
    ['', 'الكل', 'All'], ['starred', '⭐ المميّزة', '⭐ Starred'], ['open', 'مفتوحة', 'Open'],
    ['overdue', 'متأخرة', 'Overdue'], ['today', 'اليوم', 'Today'],
    ['mine', 'مهامي', 'Mine'], ['done', 'منجزة', 'Done'],
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

  /// Searchable department picker sheet (professional, filters by name).
  Future<int?> _pickDepartment(BuildContext ctx, List<Map> depts, int? current) {
    String q = '';
    return showModalBottomSheet<int>(
      context: ctx, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => StatefulBuilder(builder: (c, ss) {
        final ql = q.trim().toLowerCase();
        final list = ql.isEmpty ? depts
            : depts.where((d) => '${d['name']}'.toLowerCase().contains(ql)).toList();
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom),
          child: DraggableScrollableSheet(
            expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
            builder: (_, sc) => Column(children: [
              Container(width: 40, height: 4, margin: const EdgeInsets.symmetric(vertical: 11),
                  decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4))),
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8), child: Row(children: [
                const Icon(Icons.apartment_rounded, color: Pms.violet),
                const SizedBox(width: 8),
                Text(tr('اختر القسم', 'Pick department'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              ])),
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: TextField(autofocus: true, onChanged: (v) => ss(() => q = v),
                  decoration: InputDecoration(hintText: tr('ابحث عن قسم…', 'Search department…'),
                      prefixIcon: const Icon(Icons.search_rounded, size: 20),
                      isDense: true, filled: true, fillColor: Pms.bg,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)))),
              Expanded(child: ListView.builder(controller: sc, itemCount: list.length,
                itemBuilder: (_, i) {
                  final d = list[i];
                  final sel = d['id'] == current;
                  return ListTile(
                    leading: CircleAvatar(backgroundColor: Pms.violet.withValues(alpha: 0.12),
                        child: const Icon(Icons.apartment_rounded, color: Pms.violet, size: 20)),
                    title: Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                    trailing: sel ? const Icon(Icons.check_circle_rounded, color: Pms.violet) : null,
                    onTap: () => Navigator.pop(c, d['id'] as int),
                  );
                })),
            ]),
          ),
        );
      }),
    );
  }

  Future<void> _createTask() async {
    final name = TextEditingController();
    final desc = TextEditingController();
    bool urgent = false;
    bool committed = false;
    DateTime? deadline;
    int? deptId;
    String? photoB64;
    List<Map> departments = const [];
    // Pull the form's choices (departments) up front; failure is non-fatal.
    try {
      final meta = await context.read<AuthProvider>().api.pmsTaskMeta(widget.projectId!);
      departments = ((meta['departments'] as List?) ?? const []).cast<Map>();
    } catch (_) {}
    if (!mounted) return;

    Future<void> pickPhoto(void Function(void Function()) setSheet, ImageSource src) async {
      try {
        final x = await ImagePicker().pickImage(source: src, maxWidth: 1600, imageQuality: 70);
        if (x == null) return;
        final bytes = await x.readAsBytes();
        setSheet(() => photoB64 = base64Encode(bytes));
      } catch (_) {}
    }

    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      backgroundColor: Colors.white,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) => Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.add_task_rounded, color: Pms.violet),
              const SizedBox(width: 8),
              Text(tr('مهمة جديدة', 'New task'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Pms.ink)),
            ]),
            const SizedBox(height: 14),
            TextField(
              controller: name, autofocus: true,
              decoration: InputDecoration(
                  labelText: tr('عنوان المهمة', 'Task title'),
                  prefixIcon: const Icon(Icons.title_rounded),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: desc, maxLines: 3,
              decoration: InputDecoration(
                  labelText: tr('كل تفاصيل المهمة', 'All task details'),
                  alignLabelWithHint: true,
                  prefixIcon: const Icon(Icons.notes_rounded),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
            ),
            const SizedBox(height: 12),
            // department — searchable professional picker
            if (departments.isNotEmpty)
              InkWell(
                onTap: () async {
                  final picked = await _pickDepartment(ctx, departments, deptId);
                  if (picked != null) setSheet(() => deptId = picked);
                },
                child: InputDecorator(
                  decoration: InputDecoration(
                      labelText: tr('القسم', 'Department'),
                      prefixIcon: const Icon(Icons.apartment_rounded),
                      suffixIcon: const Icon(Icons.search_rounded),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                  child: Text(
                    deptId == null
                        ? tr('اختر القسم (بحث)', 'Pick department (search)')
                        : '${departments.firstWhere((d) => d['id'] == deptId, orElse: () => {'name': ''})['name']}',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: deptId == null ? Pms.slate : Pms.ink, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            // deadline
            InkWell(
              onTap: () async {
                final d = await showDatePicker(context: ctx,
                    initialDate: deadline ?? DateTime.now(),
                    firstDate: DateTime.now().subtract(const Duration(days: 1)),
                    lastDate: DateTime(2100));
                if (d != null) setSheet(() => deadline = d);
              },
              child: InputDecorator(
                decoration: InputDecoration(
                    labelText: tr('الموعد النهائي', 'Deadline'),
                    prefixIcon: const Icon(Icons.event_rounded),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                child: Text(deadline == null
                    ? tr('اختياري — اضغط للتحديد', 'Optional — tap to set')
                    : deadline!.toIso8601String().substring(0, 10),
                    style: TextStyle(fontWeight: FontWeight.w700,
                        color: deadline == null ? Pms.slate : Pms.ink)),
              ),
            ),
            const SizedBox(height: 6),
            // commitment
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: committed, onChanged: (v) => setSheet(() => committed = v),
              title: Text(tr('ملتزم بوقت التنفيذ', 'Committed to an execution time'),
                  style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700)),
              subtitle: Text(tr('هل لهذه المهمة التزام بموعد محدّد؟', 'Does this task carry a firm deadline?'),
                  style: const TextStyle(fontSize: 11)),
              activeThumbColor: Pms.green,
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: urgent, onChanged: (v) => setSheet(() => urgent = v),
              title: Text(tr('عاجلة', 'Urgent'), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700)),
              activeThumbColor: Pms.red,
            ),
            const SizedBox(height: 6),
            // photo
            Text(tr('صورة (اختياري)', 'Photo (optional)'),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Pms.slate)),
            const SizedBox(height: 8),
            Row(children: [
              if (photoB64 != null) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.memory(base64Decode(photoB64!), width: 64, height: 64, fit: BoxFit.cover),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: () => setSheet(() => photoB64 = null),
                  icon: const Icon(Icons.close_rounded, color: Pms.red)),
                const Spacer(),
              ],
              if (photoB64 == null) ...[
                Expanded(child: OutlinedButton.icon(
                  onPressed: () => pickPhoto(setSheet, ImageSource.camera),
                  icon: const Icon(Icons.photo_camera_rounded, size: 18),
                  label: Text(tr('كاميرا', 'Camera')),
                )),
                const SizedBox(width: 8),
                Expanded(child: OutlinedButton.icon(
                  onPressed: () => pickPhoto(setSheet, ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_rounded, size: 18),
                  label: Text(tr('المعرض', 'Gallery')),
                )),
              ],
            ]),
            const SizedBox(height: 18),
            SizedBox(width: double.infinity, height: 48, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.violet,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: () => Navigator.pop(ctx, true),
              icon: const Icon(Icons.check_rounded),
              label: Text(tr('إنشاء المهمة', 'Create task'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          ]),
        ),
      )),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    try {
      await context.read<AuthProvider>().api.pmsTaskCreate(widget.projectId!, {
        'name': name.text.trim(),
        if (desc.text.trim().isNotEmpty) 'description': desc.text.trim(),
        if (urgent) 'priority': '1',
        if (deptId != null) 'department_id': deptId,
        if (deadline != null) 'date_deadline': deadline!.toIso8601String().substring(0, 10),
        'time_committed': committed,
        if (photoB64 != null) 'image': photoB64,
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
                final stats = (snap.data!['stats'] as Map?) ?? const {};
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 20),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, i) => SizedBox(height: i == 0 ? 0 : 8),
                  itemBuilder: (_, i) => i == 0
                      ? Column(children: [
                          if (stats.isNotEmpty) _statsBand(stats),
                          if (rows.isNotEmpty) Padding(padding: const EdgeInsets.fromLTRB(2, 12, 2, 4),
                              child: Row(children: [
                                Text(tr('عرض ${rows.length} من $total', 'Showing ${rows.length} of $total'),
                                    style: const TextStyle(color: Pms.slate, fontSize: 11.5, fontWeight: FontWeight.w700)),
                              ]))
                          else Padding(padding: const EdgeInsets.only(top: 70),
                              child: Center(child: Text(tr('لا مهام', 'No tasks'),
                                  style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700)))),
                        ])
                      : _card(rows[i - 1] as Map),
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  /// Header KPI band for the task list.
  Widget _statsBand(Map s) {
    Widget cell(String v, String label, Color c, IconData ic) => Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
            border: Border.all(color: c.withValues(alpha: 0.18)),
            boxShadow: [BoxShadow(color: c.withValues(alpha: 0.06), blurRadius: 6, offset: const Offset(0, 2))]),
        child: Column(children: [
          Icon(ic, size: 15, color: c),
          const SizedBox(height: 3),
          Text('${s[label == 'المجموع' ? 'total' : label] ?? 0}',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)),
        ]),
      ),
    );
    return Row(children: [
      cell('${s['total']}', 'المجموع', Pms.ink, Icons.list_alt_rounded),
      cell('${s['open']}', 'open', const Color(0xFF2563EB), Icons.pending_actions_rounded),
      cell('${s['done']}', 'done', Pms.green, Icons.check_circle_rounded),
      cell('${s['overdue']}', 'overdue', Pms.red, Icons.local_fire_department_rounded),
      cell('${s['urgent']}', 'urgent', Pms.amber, Icons.priority_high_rounded),
    ]);
  }

  /// Deadline colour by proximity: red overdue, orange ≤2d, amber ≤7d, else slate.
  (Color, String) _deadlineStyle(Map t) {
    if (t['overdue'] == true) return (Pms.red, tr('متأخرة', 'overdue'));
    final s = '${t['deadline']}';
    if (s.length < 10) return (Pms.slate, '');
    final dd = DateTime.tryParse(s.substring(0, 10));
    if (dd == null) return (Pms.slate, '');
    final days = dd.difference(DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day)).inDays;
    if (days <= 0) return (const Color(0xFFDC2626), tr('اليوم', 'today'));
    if (days <= 2) return (const Color(0xFFEA580C), tr('خلال $days يوم', 'in ${days}d'));
    if (days <= 7) return (Pms.amber, tr('خلال $days يوم', 'in ${days}d'));
    return (Pms.slate, '');
  }

  Widget _card(Map t) {
    final overdue = t['overdue'] == true;
    final done = t['done'] == true;
    final urgent = t['urgent'] == true || t['priority'] == '1';
    final forwarded = (t['forward_state'] ?? 'none') != 'none' && t['forward_state'] != null;
    final (dlColor, dlNote) = _deadlineStyle(t);
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
            border: Border.all(color: overdue ? Pms.red.withValues(alpha: 0.5)
                : urgent ? Pms.amber.withValues(alpha: 0.5) : Colors.black12),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // top row: urgent badge + forwarded icon + name + stage
            Row(children: [
              if (urgent) Container(
                margin: const EdgeInsets.only(left: 6),
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(color: Pms.amber, borderRadius: BorderRadius.circular(6)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.priority_high_rounded, size: 11, color: Colors.white),
                  Text(tr('عاجل', 'Urgent'), style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900)),
                ]),
              ),
              if (forwarded) const Padding(padding: EdgeInsets.only(left: 5),
                  child: Icon(Icons.alt_route_rounded, size: 16, color: Color(0xFF7C3AED))),
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
            const SizedBox(height: 8),
            Row(children: [
              if (t['deadline'] != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(color: dlColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(7)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.event_rounded, size: 12, color: dlColor),
                    const SizedBox(width: 3),
                    Text('${t['deadline']}'.substring(0, 10),
                        style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: dlColor)),
                    if (dlNote.isNotEmpty) Text('  •  $dlNote',
                        style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: dlColor)),
                  ]),
                ),
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
              // assignee avatars (real photos, overlapping)
              for (final a in ((t['assignees'] as List?) ?? []).take(3))
                Padding(padding: const EdgeInsets.only(left: 2), child: _avatar(a as Map, 11)),
            ]),
          ]),
        ),
      ),
    );
  }

}

/// Round assignee/user avatar (real photo with an initial fallback).
Widget _avatar(Map a, double r) => CircleAvatar(
      radius: r, backgroundColor: Pms.violet.withValues(alpha: 0.15),
      backgroundImage: a['avatar'] != null ? NetworkImage('${a['avatar']}') : null,
      child: a['avatar'] == null
          ? Text('${a['name'] ?? '?'}'.characters.first,
              style: TextStyle(fontSize: r * 0.85, fontWeight: FontWeight.w900, color: Pms.deep))
          : null,
    );

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
            // professional gradient hero — colour reflects the task's state
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: d['done'] == true
                      ? [Pms.green, const Color(0xFF0F7A3D)]
                      : overdue
                          ? [Pms.red, const Color(0xFF9B1C31)]
                          : [Pms.violet, Pms.deep],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: Pms.violet.withValues(alpha: 0.28), blurRadius: 14, offset: const Offset(0, 6))],
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(child: Text('${d['name']}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Colors.white, height: 1.3))),
                  IconButton(
                    tooltip: tr('أولوية', 'Priority'),
                    icon: Icon(d['priority'] == '1' ? Icons.star_rounded : Icons.star_border_rounded,
                        color: d['priority'] == '1' ? Pms.amber : Colors.white),
                    onPressed: d['can_write'] == true && !_busy
                        ? () => _setPriority(d['priority'] != '1') : null,
                  ),
                ]),
                if (d['project'] != null) Text('${(d['project'] as Map)['name']}',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12, fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                Wrap(spacing: 7, runSpacing: 7, children: [
                  if (d['urgent'] == true || d['priority'] == '1') _hPill('🔥 ${tr('عاجل', 'Urgent')}'),
                  if (d['stage'] != null) _hPill('${(d['stage'] as Map)['name']}'),
                  if (d['done'] == true) _hPill('✓ ${tr('منجزة', 'Done')}'),
                  if (overdue) _hPill('⏰ ${tr('متأخرة', 'Overdue')}'),
                  if ((d['forward_state'] ?? 'none') != 'none') _hPill('↪ ${tr('محالة', 'Forwarded')}'),
                  if (d['time_committed'] == true) _hPill('🎯 ${tr('ملتزم بوقت', 'Committed')}'),
                  for (final t in ((d['tags'] as List?) ?? [])) _hPill('$t'),
                ]),
                if (d['deadline'] != null) Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(12)),
                    child: Row(children: [
                      const Icon(Icons.event_rounded, size: 16, color: Colors.white),
                      const SizedBox(width: 8),
                      Text(tr('الموعد النهائي', 'Deadline'),
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
                      const Spacer(),
                      Text('${d['deadline']}'.split(' ').first,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
                    ]),
                  ),
                ),
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
                if (d['time_committed'] != null)
                  _kv(d['time_committed'] == true ? Icons.verified_rounded : Icons.schedule_outlined,
                      tr('الالتزام بوقت التنفيذ', 'Time commitment'),
                      d['time_committed'] == true ? tr('ملتزم', 'Committed') : tr('غير ملتزم', 'Not committed'),
                      color: d['time_committed'] == true ? Pms.green : Pms.slate),
                if (d['category'] != null) _kv(Icons.category_rounded, tr('التصنيف', 'Category'), '${(d['category'] as Map)['name']}'),
                if (d['parent'] != null) _kv(Icons.subdirectory_arrow_right_rounded, tr('مهمة أصل', 'Parent'), '${(d['parent'] as Map)['name']}'),
                if ((d['allocated_hours'] as num? ?? 0) > 0 || (d['effective_hours'] as num? ?? 0) > 0)
                  _kv(Icons.schedule_rounded, tr('الساعات', 'Hours'),
                      tr('${d['allocated_hours']} مخصّصة · ${d['effective_hours']} منفَّذة',
                         '${d['allocated_hours']} allocated · ${d['effective_hours']} spent')),
                if ((d['assignees'] as List?)?.isNotEmpty == true) Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Icon(Icons.people_rounded, size: 16, color: Pms.slate),
                    const SizedBox(width: 9),
                    SizedBox(width: 96, child: Text(tr('المسؤولون', 'Assignees'),
                        style: const TextStyle(color: Pms.slate, fontSize: 12))),
                    Expanded(child: Wrap(spacing: 8, runSpacing: 6, children: [
                      for (final a in (d['assignees'] as List))
                        Row(mainAxisSize: MainAxisSize.min, children: [
                          _avatar(a as Map, 12),
                          const SizedBox(width: 5),
                          Text('${a['name']}', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Pms.ink)),
                        ]),
                    ])),
                  ]),
                ),
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
            // photos
            if (((d['photos'] as List?) ?? const []).isNotEmpty) ...[
              const SizedBox(height: 12),
              _section(tr('الصور', 'Photos')),
              SizedBox(
                height: 96,
                child: ListView(scrollDirection: Axis.horizontal, children: [
                  for (final p in (d['photos'] as List))
                    Padding(
                      padding: const EdgeInsets.only(left: 8),
                      child: GestureDetector(
                        onTap: () => Navigator.push(context, MaterialPageRoute(
                            builder: (_) => PmsPhotoView(url: '$p', title: tr('صورة المهمة', 'Task photo')))),
                        child: Hero(
                          tag: 'taskphoto-$p',
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.network('$p', width: 96, height: 96, fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => Container(
                                    width: 96, height: 96, color: Colors.black12,
                                    child: const Icon(Icons.broken_image_rounded, color: Pms.slate))),
                          ),
                        ),
                      ),
                    ),
                ]),
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
              _section(tr('مراحل المهمة', 'Task stage')),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final s in stages) _stageButton(d, s as Map),
              ]),
            ],
            // ---- forwarding / routing ----
            const SizedBox(height: 12),
            _forwardBlock(d),
            // ---- close / close-request ----
            _closeBlock(d),
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
                  if (_strip('${m['body']}').trim().isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(_strip('${m['body']}'), style: const TextStyle(fontSize: 12, height: 1.4)),
                  ],
                  // images attached to this comment, shown inline & tappable
                  if (((m['images'] as List?) ?? const []).isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      for (final im in (m['images'] as List))
                        GestureDetector(
                          onTap: () => Navigator.push(context, MaterialPageRoute(
                              builder: (_) => PmsPhotoView(url: '$im', title: tr('صورة', 'Photo')))),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: Image.network('$im', width: 84, height: 84, fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => Container(
                                    width: 84, height: 84, color: Colors.black12,
                                    child: const Icon(Icons.broken_image_rounded, color: Pms.slate))),
                          ),
                        ),
                    ]),
                  ],
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


  /// A white-on-gradient pill for the hero header.
  Widget _hPill(String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
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

  /// The close / close-request panel. A plain assignee on a deadline task can
  /// only «request to close»; the creator/manager approves — or it auto-closes
  /// after 48h. Everyone else with write access closes directly.
  Widget _closeBlock(Map d) {
    if (d['done'] == true) return const SizedBox.shrink();
    if (d['can_write'] != true) return const SizedBox.shrink();
    final cs = '${d['close_state'] ?? 'none'}';
    final needsReq = d['needs_close_request'] == true;
    final canClose = d['can_close_directly'] == true;
    final isApprover = d['is_close_approver'] == true;

    // A close request is pending.
    if (cs == 'requested') {
      return Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(color: const Color(0xFFFFF8EC), borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFFFE1AC))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.hourglass_top_rounded, size: 18, color: Color(0xFFA86400)),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('طلب إغلاق بانتظار الاعتماد', 'Close request pending'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Color(0xFFA86400)))),
          ]),
          if (d['close_requested_by'] != null) Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${tr('طلبه', 'Requested by')}: ${d['close_requested_by']}'
                '${d['close_requested_on'] != null ? '  •  ${d['close_requested_on']}' : ''}',
                style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
          ),
          if (isApprover) ...[
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: Pms.red, side: const BorderSide(color: Pms.red),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
                onPressed: _busy ? null : () => _closeAction('reject'),
                icon: const Icon(Icons.close_rounded, size: 17),
                label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
              const SizedBox(width: 8),
              Expanded(child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Pms.green,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
                onPressed: _busy ? null : () => _closeAction('approve'),
                icon: const Icon(Icons.check_rounded, size: 18),
                label: Text(tr('اعتماد الإغلاق', 'Approve'), style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
            ]),
          ] else
            Padding(padding: const EdgeInsets.only(top: 6),
                child: Text(tr('سيُعتمد من منشئ التاسك، أو يُغلق تلقائيًا خلال 48 ساعة.',
                    'Awaiting the creator, or auto-closes within 48h.'),
                    style: const TextStyle(fontSize: 11.5, color: Pms.slate))),
        ]),
      );
    }

    // No pending request → offer the right close affordance.
    final restricted = needsReq && !canClose;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SizedBox(width: double.infinity, height: 48, child: restricted
          ? FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE08A00),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : () => _closeAction('request'),
              icon: const Icon(Icons.assignment_turned_in_rounded),
              label: Text(tr('طلب إغلاق التاسك', 'Request to close'),
                  style: const TextStyle(fontWeight: FontWeight.w900)))
          : FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.green,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : () => _closeAction('close'),
              icon: const Icon(Icons.check_circle_rounded),
              label: Text(tr('إغلاق التاسك', 'Close task'),
                  style: const TextStyle(fontWeight: FontWeight.w900)))),
    );
  }

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
    String q = '';
    bool changeDeadline = false;
    final curDeadline = '${d['deadline'] ?? ''}';
    DateTime? newDeadline = curDeadline.length >= 10 ? DateTime.tryParse(curDeadline.substring(0, 10)) : null;
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) {
        final ql = q.trim().toLowerCase();
        final list = ql.isEmpty ? users : users.where((u) {
          final hay = '${(u as Map)['search'] ?? '${u['name']}'}'.toLowerCase();
          return ql.split(',').map((g) => g.trim()).where((g) => g.isNotEmpty)
              .any((g) => g.split(RegExp(r'\s+')).every((w) => hay.contains(w)));
        }).toList();
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: DraggableScrollableSheet(
            expand: false, initialChildSize: 0.85, maxChildSize: 0.95, minChildSize: 0.5,
            builder: (_, sc) => Column(children: [
              Container(width: 40, height: 4, margin: const EdgeInsets.symmetric(vertical: 11),
                  decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4))),
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8), child: Row(children: [
                const Icon(Icons.alt_route_rounded, color: Color(0xFF7C3AED)),
                const SizedBox(width: 8),
                Text(tr('إحالة المهمة إلى', 'Forward task to'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              ])),
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: TextField(
                  onChanged: (v) => setSheet(() => q = v),
                  decoration: InputDecoration(
                    hintText: tr('ابحث بالاسم أو الوظيفة أو القسم…', 'Search name/job/dept…'),
                    prefixIcon: const Icon(Icons.search_rounded, size: 20),
                    isDense: true, filled: true, fillColor: Pms.bg,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
                )),
              Expanded(child: ListView.builder(
                controller: sc, itemCount: list.length,
                itemBuilder: (_, i) {
                  final u = list[i] as Map;
                  final sel = picked == u['id'];
                  return ListTile(
                    leading: _avatar(u, 18),
                    title: Text('${u['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                    subtitle: (u['job'] != null || u['department'] != null)
                        ? Text([u['job'], u['department']].where((x) => x != null).join(' · '),
                            style: const TextStyle(fontSize: 11.5))
                        : null,
                    trailing: sel ? const Icon(Icons.check_circle_rounded, color: Color(0xFF7C3AED)) : null,
                    selected: sel, selectedTileColor: const Color(0xFF7C3AED).withValues(alpha: 0.06),
                    onTap: () => setSheet(() => picked = u['id'] as int),
                  );
                },
              )),
              // deadline option + reason + submit
              Padding(padding: const EdgeInsets.fromLTRB(16, 6, 16, 14), child: Column(children: [
                Container(
                  decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(12)),
                  child: Column(children: [
                    SwitchListTile(
                      dense: true, contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                      value: changeDeadline, onChanged: (v) => setSheet(() => changeDeadline = v),
                      title: Text(tr('تغيير موعد الاستحقاق', 'Change the deadline'),
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
                      subtitle: Text(changeDeadline
                          ? '${newDeadline?.toIso8601String().substring(0, 10) ?? ''}'
                          : tr('إبقاء الموعد الحالي: ${curDeadline.isEmpty ? 'بدون' : curDeadline.substring(0, curDeadline.length.clamp(0, 10))}',
                              'Keep current'),
                          style: const TextStyle(fontSize: 11)),
                    ),
                    if (changeDeadline) Padding(padding: const EdgeInsets.only(bottom: 8),
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          final dd = await showDatePicker(context: ctx, initialDate: newDeadline ?? DateTime.now(),
                              firstDate: DateTime(2020), lastDate: DateTime(2100));
                          if (dd != null) setSheet(() => newDeadline = dd);
                        },
                        icon: const Icon(Icons.event_rounded, size: 17),
                        label: Text(newDeadline?.toIso8601String().substring(0, 10) ?? tr('اختر تاريخًا', 'Pick a date')),
                      )),
                  ]),
                ),
                const SizedBox(height: 8),
                TextField(controller: reason,
                    decoration: InputDecoration(hintText: tr('سبب الإحالة (اختياري)', 'Reason (optional)'),
                        isDense: true, border: const OutlineInputBorder())),
                const SizedBox(height: 10),
                SizedBox(width: double.infinity, height: 46, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF7C3AED),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: picked == null ? null : () => Navigator.pop(ctx, true),
                  icon: const Icon(Icons.send_rounded, size: 18),
                  label: Text(tr('إحالة المهمة', 'Forward task'), style: const TextStyle(fontWeight: FontWeight.w900)),
                )),
              ])),
            ]),
          ),
        );
      }),
    );
    if (ok != true || picked == null) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsTaskForward(widget.taskId, picked!,
          reason: reason.text.trim(),
          deadline: changeDeadline ? newDeadline?.toIso8601String().substring(0, 10) : null);
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

  // Colour a stage by what it means, so the buttons read as states.
  Color _stageColor(String name) {
    final n = name.toLowerCase();
    if (RegExp(r'done|complete|closed|finish|منجز|مكتمل|مغلق|منته|انجاز|إنجاز').hasMatch(n)) return Pms.green;
    if (RegExp(r'progress|doing|قيد|جاري|تنفيذ|بدأ').hasMatch(n)) return const Color(0xFF2563EB);
    if (RegExp(r'delay|hold|wait|pending|late|متأخر|مؤجل|معلق|انتظار|تأجيل').hasMatch(n)) return const Color(0xFFEA580C);
    if (RegExp(r'new|todo|backlog|جديد|قائمة|لم').hasMatch(n)) return Pms.slate;
    if (RegExp(r'cancel|reject|ملغ|مرفوض').hasMatch(n)) return Pms.red;
    return Pms.violet;
  }

  bool _isDoneStage(String name) =>
      RegExp(r'done|complete|closed|finish|منجز|مكتمل|مغلق|منته|انجاز|إنجاز').hasMatch(name.toLowerCase());

  Widget _stageButton(Map d, Map s) {
    final current = (d['stage'] as Map?)?['id'] == s['id'];
    final c = _stageColor('${s['name']}');
    final isDone = _isDoneStage('${s['name']}');
    return Material(
      color: current ? c : Colors.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: _busy || current ? null : () => isDone ? _doneWithNote(s['id'] as int) : _move(s['id'] as int),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: current ? c : c.withValues(alpha: 0.35), width: 1.4),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(isDone ? Icons.check_circle_rounded : (current ? Icons.radio_button_checked_rounded : Icons.circle_outlined),
                size: 14, color: current ? Colors.white : c),
            const SizedBox(width: 6),
            Text('${s['name']}', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12,
                color: current ? Colors.white : c)),
          ]),
        ),
      ),
    );
  }

  Future<void> _doneWithNote(int stageId) async {
    final c = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Row(children: [
        const Icon(Icons.check_circle_rounded, color: Pms.green),
        const SizedBox(width: 8),
        Text(tr('إغلاق المهمة', 'Close task'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      ]),
      content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr('اكتب ما تم إنجازه — سيُسجّل في المتابعة:', 'What was done — logged in the activity:'),
            style: const TextStyle(fontSize: 12.5, color: Pms.slate)),
        const SizedBox(height: 10),
        TextField(controller: c, maxLines: 4, autofocus: true,
            decoration: InputDecoration(hintText: tr('تم تنفيذ…', 'Completed…'),
                filled: true, fillColor: Pms.bg,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none))),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(backgroundColor: Pms.green, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, true),
          icon: const Icon(Icons.check_rounded, size: 18),
          label: Text(tr('إغلاق', 'Close'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      // move to the done stage, then close (with the note → chatter)
      await api.pmsTaskStage(widget.taskId, stageId);
      await api.pmsTaskClose(widget.taskId, note: c.text.trim());
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم إغلاق المهمة', '✅ Task closed')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
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

  Future<void> _closeAction(String kind) async {
    // kind: 'close' | 'request' | 'approve' | 'reject'
    String? note;
    if (kind == 'request' || kind == 'reject' || kind == 'close') {
      final c = TextEditingController();
      final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(
            kind == 'request' ? tr('طلب إغلاق التاسك', 'Request to close')
                : kind == 'reject' ? tr('رفض الإغلاق', 'Reject close')
                : tr('إغلاق المهمة', 'Close task'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: TextField(controller: c, maxLines: 3, autofocus: true,
            decoration: InputDecoration(
                hintText: kind == 'reject'
                    ? tr('سبب الرفض…', 'Reason…')
                    : kind == 'close'
                        ? tr('ما تم إنجازه (يُسجّل في المتابعة)…', 'What was done (logged)…')
                        : tr('ملاحظة (اختياري)…', 'Note (optional)…'),
                filled: true, fillColor: Pms.bg,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none))),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
          ElevatedButton(
              style: ElevatedButton.styleFrom(
                  backgroundColor: kind == 'reject' ? Pms.red : kind == 'close' ? Pms.green : Pms.violet,
                  foregroundColor: Colors.white),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('تأكيد', 'Confirm'))),
        ],
      ));
      if (ok != true || !mounted) return;
      note = c.text.trim();
    }
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      String msg;
      switch (kind) {
        case 'close':
          await api.pmsTaskClose(widget.taskId, note: note);
          msg = tr('تم إغلاق التاسك', 'Task closed');
          break;
        case 'request':
          await api.pmsTaskRequestClose(widget.taskId, note: note);
          msg = tr('تم إرسال طلب الإغلاق للاعتماد', 'Close request sent');
          break;
        case 'approve':
          await api.pmsTaskApproveClose(widget.taskId);
          msg = tr('تم اعتماد إغلاق التاسك', 'Close approved');
          break;
        default:
          await api.pmsTaskRejectClose(widget.taskId, reason: note);
          msg = tr('تم رفض طلب الإغلاق', 'Close rejected');
      }
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ $msg'), backgroundColor: Pms.green));
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
